###############################################################################################
#                                                                                             #
#                               AUTOMA CORPORATION (c) 2023                                   #
#                                                                                             #
#      ALL RIGHTS RESERVED. UNAUTHORIZED COPYING, REPRODUCTION, HIRE, LENDING, PUBLIC         #
#      PERFORMANCE, AND BROADCASTING OF THIS SOFTWARE, VIA ANY MEDIUM, ARE PROHIBITED.        #
#                                                                                             #
#                  PROPRIETARY AND CONFIDENTIAL INFORMATION OF AUTOMA CORPORATION             #
#                                                                                             #
###############################################################################################


import os, requests, time, traceback, logging, inspect, signal
from datetime import datetime
from dateutil import parser
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter


API_BASE_URL = "https://visionapi.automa.one/facespace"


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


logger = logging.getLogger('FaceSpaceLogger')
logger.propagate = False


# Custom Exception classes
class FaceSpaceError(Exception):
    """Base class for other exceptions"""
    pass


class APIKeyError(FaceSpaceError):
    """Raised when the API key is missing or invalid"""
    pass

class DateParseError(FaceSpaceError):
    """Raised when there is a date parsing error"""
    pass


class HTTPRequestError(FaceSpaceError):
    """Raised when an HTTP request fails"""
    pass


class StopLogsSignal(Exception):
    """Raised when a stop signal is received from the API"""
    pass


class InvalidUsageError(FaceSpaceError):
    """Raised when methods are used with incorrect parameters."""
    pass


class ForLoopError(FaceSpaceError):
    """Raised when the get_realtime_logs method is not used within a for loop"""
    def __str__(self):
        example_usage = (
            "\n# Example usage\n"
            "for log in client.get_realtime_logs(refresh=0.1, limit=10):\n"
            "    print(log)  # Or process the logs as needed\n"
        )
        return (
            "ForLoopError: The get_realtime_logs method must be used within a 'for' loop as shown below:\n"
            f"{example_usage}"
        )


class LogsAPI:
    """The main class to use for communicating with FaceSpace APIs"""
    def __init__(self, api_key=None, log_to_file=False, log_level=logging.INFO, file_log_level=logging.DEBUG, additional_headers=None, webhook_url=None, post_realtime=True, post_logs=False, gaze_detection=False):
        """
        Summary:
            Initializes the logging API client with configurable parameters.

        Description:
            This constructor sets up the logging environment, including API key configuration, session retries, signal handling, and log handlers for both console and file output based on user preferences.

        Parameters:
            - 'api_key': Optional; The API key for authentication. If not provided, it attempts to fetch from environment variables.
            - 'log_to_file': Optional; Boolean indicating whether logs should also be written to a file.
            - 'log_level': Optional; The logging level for console output.
            - 'file_log_level': Optional; The logging level for file output.
            - 'additional_headers': Optional; Additional headers to include in HTTP requests.
            - 'webhook_url': Optional; The URL to which logs will be posted.
            - 'post_realtime': Optional; Boolean indicating whether logs should be posted in real-time.
            - 'post_logs': Optional; Boolean indicating whether logs should be posted at all.

        Exceptions:
            - Raises APIKeyError if an API key is not provided or found in environment variables.
        """
        self.session = requests.Session()  # Create a session for HTTP requests
        self.file_handler = None  # Initialize file handler for logging to a file
        self.api_key = api_key or os.getenv('FACESPACE_API_KEY')  # Fetch API key from parameters or environment
        if not self.api_key:
            raise APIKeyError("API key must be set before using the client.")
        self.headers = {"x-api-key": self.api_key}  # Set the API key in the headers
        self.logs = []  # Initialize the list to store logs
        self.post_realtime = post_realtime  # Set the flag for real-time log posting
        self.post_logs = post_logs  # Set the flag for log posting
        self.running = False  # Initialize the running state of the logger
        self._within_context_manager = False  # Internal flag for context manager state
        signal.signal(signal.SIGINT, self.signal_handler)  # Set up signal handling for graceful shutdown
        self.request_count = 0  # Initialize the request count
        self.last_active_time = None  # Initialize the last active time
        self.gaze_detection = gaze_detection
        # Additional headers for HTTP requests
        self.additional_headers = additional_headers or {}
        
        # Webhook URL for posting logs
        self.webhook_url = webhook_url
        
        # Update the headers with additional headers
        self.headers.update(self.additional_headers)
        
        # Add retries to the session for robustness
        retries = Retry(total=5, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
        self.session.mount('https://', HTTPAdapter(max_retries=retries))
        
        # Set up a stream handler for console logs and add it to the logger
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        self.console_handler = console_handler
        logger.addHandler(console_handler)
        logger.setLevel(log_level)
        console_handler.setLevel(log_level)
        
        # Set up a file handler for file logs if needed
        if log_to_file:
            log_filename = datetime.now().strftime('facespace_log_%Y%m%d_%H%M%S.log')
            file_handler = logging.FileHandler(log_filename)
            file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
            self.file_handler = file_handler
            logger.addHandler(file_handler)
            file_handler.setLevel(file_log_level) 
            
        self.log_levels = {
            'heartbeat': logging.DEBUG,  # Lowest level for heartbeat messages
            'error': logging.ERROR,  # Highest level for error messages
            'log': logging.INFO,  # Middle level for general logs
        }
        
        self.set_display_log_level(log_level)  # Set the initial log level for display

                
    def __enter__(self):
        """Entry for context manager, allowing for realtime logs to run indefinitely"""
        self._within_context_manager = True
        self.start_fetching()
        return self


    def __exit__(self, exc_type, exc_value, traceback):
        """Exit for manager, automatically stopping rogue realtime_logs running indefinitely"""
        self._within_context_manager = False
        self.stop_realtime_logs()
        
        
    def set_display_log_level(self, level):
        """
        Summary:
            Sets the logging level for the console handler.

        Description:
            This method configures the logging level for console output. It accepts both string and integer inputs to define the log level. If a string is provided, it is converted to the corresponding logging level.

        Parameters:
            - 'level': Can be a string representing the log level ('debug', 'info', 'warning', 'error', 'critical') or an integer as defined in the logging module.

        Exceptions:
            - Raises ValueError if the string log level name is invalid.
            - Raises TypeError if the log level is neither an int nor a str.
        """
        # Check if the log level is specified as a string
        if isinstance(level, str):
            level_name = level.lower()  # Convert the level name to lowercase to ensure case-insensitivity
            # Set the console handler log level if the level name is valid
            if level_name in self.log_levels:
                self.console_handler.setLevel(self.log_levels[level_name])
            else:
                # Raise an error if the level name is not recognized
                raise ValueError(f"Invalid log level name: {level}")
        # Check if the log level is specified as an integer
        elif isinstance(level, int):
            self.console_handler.setLevel(level)  # Set the console handler log level directly
        else:
            # Raise an error if the log level is neither an int nor a str
            raise TypeError("Log level must be either an int or str.")


    def set_file_log_level(self, level):
        """
        Summary:
            Sets the logging level for the file handler.

        Description:
            This method configures the logging level for file output, provided that file logging is enabled. It accepts both string and integer inputs to define the log level. If a string is provided, it is checked against predefined log levels.

        Parameters:
            - 'level': Can be a string representing the log level ('debug', 'info', 'warning', 'error', 'critical') or an integer as defined in the logging module.

        Exceptions:
            - Raises ValueError if file logging is not enabled or if the string log level name is invalid.
            - Raises TypeError if the log level is neither an int nor a str.
        """
        # Check if the file handler attribute exists to ensure file logging is enabled
        if hasattr(self, 'file_handler'):
            # Check if the log level is specified as a string
            if isinstance(level, str):
                level_name = level.lower()  # Normalize the level name to lowercase
                # Set the file handler log level if the level name is valid
                if level_name in self.log_levels:
                    self.file_handler.setLevel(self.log_levels[level_name])
                else:
                    # Raise an error if the level name is not recognized
                    raise ValueError(f"Invalid log level name: {level}")
            # Check if the log level is specified as an integer
            elif isinstance(level, int):
                self.file_handler.setLevel(level)  # Set the file handler log level directly
            else:
                # Raise an error if the log level is neither an int nor a str
                raise TypeError("Log level must be either an int or str.")
        else:
            # Raise an error if file logging is not enabled
            raise ValueError("File logging is not enabled.")


    def _increment_request_count(self):
        """To track the number of requests made to the API for future logging"""
        self.request_count += 1
        logger.log(self.log_levels['heartbeat'], f"Total requests made: {self.request_count}") 
    
    
    def signal_handler(self, sig, frame):
        """To handle terminal quitting"""
        logger.info('SIGINT or CTRL-C detected. Stopping log fetching.')
        self.stop_realtime_logs()


    def _perform_request_with_retry(self, method, url, **kwargs):
        """
        Summary:
            Executes an HTTP request with automatic retries for certain status codes.

        Description:
            This private method attempts to perform an HTTP request using a session with a mounted retry strategy.
            It retries on specific HTTP status codes with exponential backoff. If a webhook URL is provided and
            post_logs is enabled, it will also send the response to the webhook URL.

        Parameters:
            - 'method': The HTTP method to be used for the request (e.g., 'GET', 'POST').
            - 'url': The URL to which the request is to be sent.
            - '**kwargs': Additional keyword arguments that are passed to the 'request' method.

        Exceptions:
            - Raises HTTPRequestError if the request exceeds the maximum number of retries.
            - Logs an error message if the webhook POST fails.
        """
        # Define a retry strategy for the session
        retry_strategy = Retry(
            total=3,  # Maximum number of retry attempts
            status_forcelist=[429, 500, 502, 503, 504],  # HTTP status codes to trigger a retry
            allowed_methods=["HEAD", "GET", "OPTIONS"],  # HTTP methods to be retried
            backoff_factor=1  # Factor by which the delay until next retry will increase
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)  # Create an adapter with the retry strategy
        self.session.mount('https://', adapter)  # Mount the adapter for HTTPS requests
        
        try:
            response = self.session.request(method, url, **kwargs)  # Perform the HTTP request
            response.raise_for_status()  # Raise an exception for HTTP error codes

            # If a webhook URL is provided and post_logs is True, post the response to the webhook
            if self.webhook_url and self.post_logs == True:
                try:
                    webhook_response = requests.post(self.webhook_url, json=response.json(), headers=self.headers)
                    webhook_response.raise_for_status()  # Raise an exception for HTTP error codes
                    logger.debug(f"Webhook POST successful: {webhook_response.json()}")  # Log success
                except requests.exceptions.RequestException as e:
                    logger.error(f"Webhook POST failed: {e}")  # Log any exception that occurs

            return response.json()  # Return the JSON response
        except requests.exceptions.RetryError as retry_err:
            logger.error(f"Retry Error: {retry_err}")  # Log the retry error
            raise HTTPRequestError(f"Retry Error: {retry_err}")  # Raise an exception if retries fail


    def _request(self, method, endpoint, **kwargs):
        """
        Summary:
            Sends an HTTP request to a specified endpoint with error handling.

        Description:
            This private method sends an HTTP request using the specified method and endpoint.
            It automatically increments the request count and handles both HTTP-specific and general
            exceptions, logging detailed error messages and traceback information.

        Parameters:
            - 'method': The HTTP method to be used for the request (e.g., 'GET', 'POST').
            - 'endpoint': The endpoint (path relative to the base URL) to which the request is to be sent.
            - '**kwargs': Additional keyword arguments that are passed to the '_perform_request_with_retry' method.

        Exceptions:
            - Raises HTTPRequestError with a detailed error message if an HTTP error occurs.
            - Raises HTTPRequestError with a detailed error message and traceback if any other exception occurs.
        """
        self._increment_request_count()  # Increment the count of requests made
        try:
            url = f"{API_BASE_URL}{endpoint}"  # Construct the full URL
            # Perform the request with retry logic and return the response
            return self._perform_request_with_retry(method, url, headers=self.headers, **kwargs)
        except requests.HTTPError as http_err:
            # Extract error message from HTTP error response or use the error string representation
            error_message = http_err.response.json().get('error', str(http_err))
            tb = traceback.format_exc()  # Get the traceback as a string
            logger.error(f"HTTP Error: {error_message}\n{tb}")  # Log the HTTP error with traceback
            raise HTTPRequestError(f"HTTP Error: {error_message}")  # Raise an HTTPRequestError with the error message
        except Exception as err:
            tb = traceback.format_exc()  # Get the traceback as a string
            logger.error(f"Request Error: {str(err)}\n{tb}")  # Log any other exception with traceback
            raise HTTPRequestError(f"Request Error: {str(err)}")  # Raise an HTTPRequestError with the error message


    def _parse_date(self, date_str):
        """
        Summary:
            Parses a date string and returns it in a standardized format.

        Description:
            This private method takes a date string which may or may not include time information.
            It returns the date and time (if present) in a standardized format. If the date string
            is in an invalid format, it logs the error and raises a DateParseError.

        Parameters:
            - 'date_str': A string representing the date (and optionally time).

        Returns:
            - A string of the parsed date and time in the format '%H:%M %d/%m/%y' if time is included,
            or just '%d/%m/%y' if only the date is provided.

        Exceptions:
            - Raises DateParseError with a detailed error message if the date string is in an invalid format.
        """
        try:
            # Check if the date_str includes time
            if len(date_str.split()) > 1:
                # If time is included, parse the full datetime
                return parser.parse(date_str).strftime('%H:%M %d/%m/%y')
            else:
                # If only the date is provided, parse without the time
                return parser.parse(date_str).strftime('%d/%m/%y')
        except ValueError:
            tb = traceback.format_exc()  # Get the traceback as a string
            error_message = f"Invalid date format: {date_str}\n{tb}"
            logger.error(error_message)  # Log the error with the traceback
            raise DateParseError(error_message)  # Raise a DateParseError with the error message


    def _response(self, endpoint, params=None):
        """Make request to API while retrying if there is a server error"""
        return self._request('GET', endpoint, params=params)


    def get_logs_range(self, start_time=None, end_time=None, camera_id=None):
        """
        Summary:
            Retrieves logs within a specified time range and/or from a specific camera.

        Description:
            This method fetches logs based on the provided start and end times, and optionally filters them by camera ID.
            It validates the input formats before making the API call and uses the internal method to parse dates.

        Parameters:
            - 'start_time': Optional; A string representing the start of the time range in 'dd/mm/yy' format.
            - 'end_time': Optional; A string representing the end of the time range in 'dd/mm/yy' format.
            - 'camera_id': Optional; A string representing the camera ID to filter the logs.

        Returns:
            - The response from the logs API endpoint with the logs that match the given criteria.

        Exceptions:
            - Raises InvalidUsageError if 'start_time', 'end_time', or 'camera_id' are not strings.
        """
        # Validate the date formats and camera_id before making the request
        if start_time and not isinstance(start_time, str):
            raise InvalidUsageError("Start time must be a string in 'dd/mm/yy' format.")
        if end_time and not isinstance(end_time, str):
            raise InvalidUsageError("End time must be a string in 'dd/mm/yy' format.")
        if camera_id and not isinstance(camera_id, str):
            raise InvalidUsageError("Camera ID must be a string.")
        
        params = {}  # Initialize the parameters dictionary
        if start_time:
            params['start_time'] = self._parse_date(start_time)  # Parse and add start time to parameters
        if end_time:
            params['end_time'] = self._parse_date(end_time)  # Parse and add end time to parameters
        if camera_id:
            params['camera_id'] = camera_id  # Add camera ID to parameters if provided
        return self._response("/logs", params=params)  # Make the API call and return the response

    ##########################################################
    #     REALTIME API SECTION BELOW, DO NOT TAMPER 💀      #
    ##########################################################
    
    def fetch_logs(self):
        """
        Summary:
            Fetches the latest logs from the recognition API endpoint.

        Description:
            This method retrieves logs from the recognition API. If the logs contain a stop signal indicating no active cameras,
            it raises a custom StopLogsSignal exception. It appends successful log responses to the internal logs list and
            posts them to a webhook URL if configured for real-time posting.

        Returns:
            - A dictionary containing the fetched log data.

        Exceptions:
            - Raises StopLogsSignal if a stop signal is detected in the log indicating no active cameras.
            - Raises HTTPRequestError if the response from the server is not successful (non-200 status code).
        """
        response = self.session.get(API_BASE_URL + "/recognition", headers=self.headers)  # Perform a GET request to fetch logs
        if response.status_code == 200:
            log = response.json()  # Parse the log from the response
            # Check for a stop signal in the log
            if isinstance(log, dict) and 'stop' in log and log['stop'].startswith('No cameras active'):
                raise StopLogsSignal("Stop signal received: " + log['stop'])  # Raise a StopLogsSignal exception
            self.logs.append(log)  # Append the log to the internal list

            # If a webhook URL is provided and real-time posting is enabled, post the log to the webhook
            if self.webhook_url and self.post_realtime == True:
                try:
                    webhook_response = requests.post(self.webhook_url, json=log, headers=self.headers)
                    webhook_response.raise_for_status()  # Check for HTTP errors and raise an exception if any
                    logger.debug(f"Webhook POST successful: {webhook_response.json()}")  # Log the successful POST
                except requests.exceptions.RequestException as e:
                    logger.error(f"Webhook POST failed: {e}")  # Log the exception if the POST fails

            return log  # Return the log
        else:
            # Log and raise an error if the response status code is not 200
            error_message = f"Error fetching logs: {response.status_code} {response.text}"
            logger.error(error_message)
            raise HTTPRequestError(error_message)


    def get_realtime_logs(self, refresh=0.5, limit=None):
        """
        Summary:
            Retrieves logs in real-time, either indefinitely or up to a specified limit.

        Description:
            This method provides a generator that yields logs in real-time with a specified refresh rate.
            It can yield logs indefinitely or stop after yielding a set number of logs based on the limit provided.
            It is designed to be used within a 'with' block for proper resource management.

        Parameters:
            - 'refresh': The time interval (in seconds) between log fetches. Must be a positive number.
            - 'limit': The maximum number of logs to yield. If None, the generator will run indefinitely.

        Returns:
            - A generator that yields logs in real-time.

        Exceptions:
            - Raises InvalidUsageError if 'refresh' is not a positive number or if 'limit' is not a positive integer.
            - Raises ForLoopError if the method is not called within a 'for' loop.
            - Raises RuntimeError if 'limit' is None and the method is not used within a 'with' block.

        Usage:
            - The method should be used as follows within a 'with' block:
                with client:
                    for log in client.get_realtime_logs(refresh=1, limit=10):
                        # process log
        """
        # Validate the refresh rate and limit before proceeding
        if not isinstance(refresh, (float, int)) or refresh <= 0:
            raise InvalidUsageError("Refresh rate must be a positive number representing seconds.")
        if limit is not None and not isinstance(limit, int):
            raise InvalidUsageError("Limit must be an integer representing the maximum number of logs to fetch.")
        if limit is not None and limit <= 0:
            raise InvalidUsageError("Limit must be a positive integer.")
        if not self._called_within_for_loop():
            raise ForLoopError("get_realtime_logs must be called within a 'for' loop.")
        if limit is None and not self._within_context_manager:
            raise RuntimeError(
                "get_realtime_logs with no limit must be used within a 'with' statement.\n\n"
                "# Example\n"
                "with client:\n"
                "   # Your 'for' loop here\n"
            )
        return self._realtime_log_generator(refresh, limit)


    def _realtime_log_generator(self, refresh, limit):
        """
        Summary:
            An internal generator method for fetching logs in real-time.

        Description:
            This private method is the core of real-time log fetching, yielding logs at a specified interval.
            It continues to fetch and yield logs until a stop signal is received, a limit is reached, or the
            'running' flag is set to False. It ensures that the fetching process is properly terminated upon exit.

        Parameters:
            - 'refresh': The time interval (in seconds) between log fetches.
            - 'limit': The maximum number of logs to yield. If None, the generator will run indefinitely.

        Yields:
            - Log data as a dictionary for each fetch.

        Usage:
            - This method should not be called directly; it is intended to be used by the 'get_realtime_logs' method.
        """
        self.start_fetching()  # Begin the log fetching process
        count = 0  # Initialize the count of fetched logs
        try:
            # Continue fetching logs as long as the 'running' flag is True and the limit has not been reached
            while self.running and (limit is None or count < limit):
                log = self.fetch_logs()  # Fetch the logs
                # Check for a stop signal in the log
                if isinstance(log, dict) and 'stop' in log and log['stop'].startswith('No cameras active'):
                    logger.info('Stop signal received, terminating log fetching.')  # Log the stop signal
                    break  # Exit the loop if a stop signal is received
                yield log  # Yield the fetched log
                if limit is not None:  # Only increment count if there is a limit
                    count += 1
                time.sleep(refresh)  # Wait for the specified refresh interval before the next fetch
        finally:
            self.stop_realtime_logs()  # Ensure the fetching process is stopped when the generator exits


    def _called_within_for_loop(self):
        """
        Summary:
            Checks if the current method invocation occurs within the context of a 'for' loop.

        Description:
            This private method inspects the call stack to determine if the current function call
            is made from within a 'for' loop. It is a utility function used to enforce correct usage
            patterns for certain generator methods.

        Returns:
            - True if the current function was called within a 'for' loop; otherwise, False.

        Usage:
            - This method is used internally to validate that certain methods are being called in the correct context.
        """
        frames = inspect.stack()  # Get the current call stack
        for frame in frames[2:]:  # Iterate over the call stack, skipping the first two frames
            if frame.code_context:  # Check if there is code context available for the frame
                for line in frame.code_context:  # Iterate over the lines of code in the context
                    # Check if the line contains a 'for' loop syntax
                    if 'for ' in line and ' in ' in line:
                        return True  # Return True if a 'for' loop is found
        return False  # Return False if no 'for' loop is found in the call stack

        return False
            
    def start_fetching(self):
        """Set to true when realtime logs start, makes it easy to stop when running"""
        self.running = True

    def stop_realtime_logs(self):
        """Very important to close connections in case of terminal failure and is automatically managed"""
        self.running = False
        self.session.close()
        logger.info('Log fetching has been stopped.')