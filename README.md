
# FaceSpace Python API Client

FaceSpace is a sophisticated Python package designed for developers to seamlessly interface with the `vision.automa.one` API. It offers a comprehensive toolkit for logging, real-time data retrieval, and camera management. The package is built with asynchronous operations in mind, ensuring optimal performance in high-throughput applications.

---

## Installation

To install FaceSpace, use the following pip command:

```sh
pip install facespace
```

This package requires Python version 3.8 or higher.

---

## Configuration

Obtain your API key from `https://vision.automa.one`. For security best practices, it is strongly advised to store this key as an environment variable.

---

## Usage

### Setting Up the Client

```python
from facespace import LogsAPI, FaceSpaceError
import os

# Utilize an environment variable for your API key to enhance security.
api_key = os.getenv('FACESPACE_API_KEY')
client = LogsAPI(api_key=api_key)
```

### Fetching Logs

#### Basic Log Retrieval

```python
# Retrieve logs for a specified time range and camera.
start_time = '10:00:00 23/10/23'  # Start of the log retrieval period.
end_time = '24/10/23'             # End of the log retrieval period.
camera_id = 'TestCamera'          # Identifier for the camera.

logs = client.get_logs_range(start_time=start_time, end_time=end_time, camera_id=camera_id)
print(logs)
```

When a `start_time` is specified with only a date, the system defaults to the beginning of that day (00:00:00). In the absence of an `end_time`, logs are retrieved from the `start_time` to the last available entry. If a `camera_id` is not provided, the system will collect logs across all cameras. Should both `start_time` and `end_time` be omitted, the system will return the complete set of logs.

> **Note**: Time must be provided in UTC only (for now).

#### Advanced Log Retrieval

```python
# Fetch logs with additional configurations.
client = LogsAPI(
    api_key=api_key,
    log_to_file=True,  # This enables the logging of data to a file.
    webhook_url='https://yourwebhook.url',  # Logs will be posted to this webhook URL.
    additional_headers={'Custom-Header': 'Value'},  # Custom headers included in the webhook post.
    post_realtime=False  # Determines whether real-time logs are posted to the webhook.
)

logs = client.get_logs_range(start_time=start_time, end_time=end_time)
print(logs)
```

The `log_to_file` option, when set to `True`, logs will be saved to a file, which is useful for persistent storage and later analysis. The `webhook_url` allows for integration with external systems for processing or monitoring. If `additional_headers` are provided, they will be included in the webhook post, allowing for custom integration. Setting `post_realtime` to `False` will prevent real-time logs from being sent to the webhook.

### Real-time Logs

#### Basic Real-time Log Streaming

```python
# Stream real-time logs using a context manager.
with client:
    for log in client.get_realtime_logs(refresh=1.0):  # Refresh rate set to 1 second.
        print(log)
```

The `refresh` parameter controls the rate at which real-time logs are fetched. If not provided, a default value is used. If set too low, it may overwhelm the system with rapid data flow.

#### Limited Real-time Log Streaming

```python
# Stream a limited number of real-time logs.
for log in client.get_realtime_logs(refresh=0.5, limit=10):  # Fetch 10 logs with a half-second pause.
    print(log)
```

The `limit` parameter controls the number of real-time logs fetched. If omitted, the stream will continue indefinitely until manually stopped.

#### High-Speed Real-time Log Streaming

```python
# Stream real-time logs at a high refresh rate.
for log in client.get_realtime_logs(refresh=0.1):  # Set a very fast refresh rate.
    print(log)
```

A `refresh` rate of 0.1 seconds is extremely fast and should only be used if the system can handle such rapid data flow.

---

## Error Handling

FaceSpace provides custom exceptions for robust error management. When using the FaceSpace API client, it's important to understand the various errors that can occur and how to handle them. Here's a breakdown of potential errors and their typical causes:

### APIKeyError

This error is raised when the API key provided is either missing or invalid. It's crucial to ensure that the API key is correctly set as an environment variable or passed directly to the client. An invalid API key could be due to a typo, incorrect key, or the key not being generated or activated properly on the `vision.automa.one` portal.

### DateParseError

This occurs when the date format provided does not match the expected format (`HH:MM:SS DD/MM/YY`). If only the date is provided without the time, it should still follow the `DD/MM/YY` format. This error can be avoided by ensuring the date strings passed to the API are in the correct format.

### HTTPRequestError

An HTTP request error happens when there's a problem with the network connection, the API endpoint is unreachable, or the server fails to respond. This could be due to network issues on the client side, downtime on the API server, or incorrect endpoint URLs.

### StopLogsSignal

This is a control signal rather than an error. It's raised to stop the retrieval of logs, which could be part of normal operation or a response to a specific command from the server indicating that the client should cease log retrieval.

### InvalidUsageError

This error is raised when methods are used incorrectly. For example, if the `get_realtime_logs` method is called without being in a `for` loop, or if the parameters provided to any method do not meet the required criteria (like missing mandatory fields or providing parameters in an incorrect type or format).

### General Error Handling

The `FaceSpaceError` is a base class for all custom exceptions. It's used in a broad `try...except` block to catch any of the specific errors mentioned above. When an error is caught, it's good practice to log the error message and, if necessary, perform cleanup operations such as stopping real-time log streams to prevent partial or corrupted data processing.

Here's an example of how you might handle errors in a typical use case:

```python
try:
    # Attempt to fetch logs or stream real-time logs.
    # ...
except FaceSpaceError as e:
    print(f'Error occurred: {e}')
    client.stop_realtime_logs()  # Properly stop the real-time log stream.
```

---

## Advanced Configuration

- **Webhook Integration**: Direct logs to a specified webhook URL for external processing or monitoring.
- **Custom Headers**: Send additional headers with your webhook requests for customized integration.
- **Real-time Log Posting**: Toggle the posting of real-time logs to your webhook endpoint.
- **File Logging**: Enable logging to a file for persistent storage and later review.
- **Log Level**: Adjust the verbosity of the logs for different environments, such as debugging or production.

## Comprehensive Examples

### Webhook Configuration

```python
client = LogsAPI(
    api_key=api_key,
    webhook_url='https://yourwebhook.url',  # Your webhook endpoint.
    additional_headers={'Custom-Header': 'Value'},  # Any additional headers you require.
    post_logs=True  # Enable posting logs to the webhook URL.
)
```

> **Note**: By default, `post_logs` is set to `False` to prevent the transmission of large static blocks of data to the webhook.

### File Logging and Log Level

```python
client = LogsAPI(
    api_key=api_key,
    log_to_file=True,  # Enable file logging.
    log_level=logging.DEBUG  # Set log level to DEBUG for verbose output.
)
```

---

## Example Code: Fetching Logs for an Entire Day

```python
from facespace import LogsAPI, FaceSpaceError
import os

# Initialize the client with your API key
api_key = os.getenv('YOUR_API_KEY')
client = LogsAPI(api_key=api_key)

# Define the date for which you want to fetch logs
# The time is omitted, so logs from the start to the end of the day are fetched.
date = '23/10/23'  # Format: DD/MM/YY

try:
    # Fetch logs for the entire day for a specific camera.
    camera_id = 'TestCamera'
    logs = client.get_logs_range(start_time=date, end_time=date, camera_id=camera_id)
    print(logs)

    # If camera_id is not provided, logs for all cameras will be fetched.
    all_camera_logs = client.get_logs_range(start_time=date, end_time=date)
    print(all_camera_logs)

except FaceSpaceError as e:
    print(f'An error occurred: {e}')
    # Additional error handling can be implemented here.
```

---

## Example Output Print

```python
# Example output when get_logs_range is printed for a specific camera
{
    'TestCamera': [
        'Alice @ 00:05:22 23/10/23',
        'Bob @ 11:15:47 23/10/23',
        ...
        'Eve @ 23:59:59 23/10/23'
    ]
}

# Example output when get_logs_range is printed for all cameras
{
    'Camera1': [
        'Alice @ 00:05:22 23/10/23',
        'Bob @ 11:15:47 23/10/23'
    ],
    'Camera2': [
        'Charlie @ 07:30:00 23/10/23',
        'Dana @ 18:45:30 23/10/23'
    ],
    ...
}

# Example output for real-time logs
{
    'Camera1': ['Alice', 'Bob'],
    'Camera2': ['Charlie', 'Dana']
}
```

---

## Support

For support, issues, or feature requests, please file an issue on our [GitHub Issues page](https://github.com/Automa-Research/facesapce-python-client/issues).

---

## License

FaceSpace API Client is released under the MIT License. See the LICENSE file in the repository for more details.

---
