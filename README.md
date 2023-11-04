# FaceSpace Python API Client

FaceSpace is a sophisticated Python package designed for developers to seamlessly interface with the `vision.automa.one` API. It offers a comprehensive toolkit for logging, real-time data retrieval, and camera management. The package is built with asynchronous operations in mind, ensuring optimal performance in high-throughput applications.

## Installation

To install FaceSpace, use the following pip command:

```sh
pip install facespace
```

This package requires Python version 3.8 or higher.

## Configuration

Obtain your API key from `https://vision.automa.one`. For security best practices, it is strongly advised to store this key as an environment variable.

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

### Error Handling

FaceSpace provides custom exceptions for robust error management:

```python
try:
    # Attempt to fetch logs or stream real-time logs.
    # ...
except FaceSpaceError as e:
    print(f'Error occurred: {e}')
    client.stop_realtime_logs()  # Properly stop the real-time log stream.
```

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

## Support

For support, issues, or feature requests, please file an issue on our [GitHub Issues page](https://github.com/Automa-Research/facesapce-python-client/issues).

## License

FaceSpace API Client is released under the MIT License. See the LICENSE file in the repository for more details.

---
