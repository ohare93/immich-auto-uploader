# Immich Auto-Uploader

A Python application that automatically monitors directories for images and videos, uploads them to a self-hosted Immich instance, and archives the uploaded files.

## Features

- **Automatic monitoring**: Watches configured directories for new image and video files
- **Immich integration**: Uploads assets to your self-hosted Immich server via API
- **File archiving**: Moves uploaded files to an archive directory after successful upload
- **Configurable**: Environment-based configuration for flexibility
- **Type-safe**: Written in Python with comprehensive error handling and logging
- **Real-time**: Uses watchdog library for immediate file system monitoring
- **Thread-safe**: Multi-threaded file processing with queue-based architecture

## Prerequisites

- [Devbox](https://www.jetify.com/devbox) installed on your system
- A running Immich server with API access
- Immich API key (generated from the user settings panel)

## Setup

1. **Clone or initialize the project**:
   ```bash
   git clone <repository-url>
   cd immich-auto-uploader
   ```

2. **Enter the development environment**:
   ```bash
   devbox shell
   ```

3. **Configure the application**:
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` and set your configuration:
   ```env
   IMMICH_API_URL=http://your-immich-server:2283/api
   IMMICH_API_KEY=your_api_key_here
   WATCH_DIRECTORIES=/home/user/Downloads,/home/user/Pictures/Camera
   ARCHIVE_DIRECTORY=/home/user/Pictures/Archived
   ```

## Configuration

The application is configured via environment variables in the `.env` file:

| Variable | Description | Default |
|----------|-------------|---------|
| `IMMICH_API_URL` | Your Immich server API endpoint | Required |
| `IMMICH_API_KEY` | API key from Immich user settings | Required |
| `WATCH_DIRECTORIES` | Comma-separated list of directories to monitor | `/home/user/Downloads` |
| `ARCHIVE_DIRECTORY` | Directory to move uploaded files | `/home/user/Pictures/Archived` |
| `WATCH_RECURSIVE` | Watch subdirectories recursively (true/false) | `true` |
| `SUPPORTED_EXTENSIONS` | File extensions to process | `jpg,jpeg,png,gif,bmp,tiff,webp,mp4,mov,avi,mkv,wmv,flv,m4v,3gp` |
| `MAX_FILE_SIZE_MB` | Maximum file size to process | `1000` |
| `FILE_STABILITY_WAIT_SECONDS` | Seconds to wait for file size to stabilize | `5` |
| `FILE_STABILITY_CHECK_INTERVAL` | Seconds between file size checks | `1.0` |
| `LOG_LEVEL` | Logging level (DEBUG, INFO, WARNING, ERROR) | `INFO` |

## Usage

### Development

Run the application in development mode:
```bash
devbox run dev
```

### Testing

Run the test suite:
```bash
devbox run test
```

Run tests with coverage:
```bash
devbox run test-coverage
```

### Production

To run in production, ensure your environment variables are configured and run:
```bash
devbox run dev
```

Or activate the virtual environment and run directly:
```bash
devbox shell
source .venv/bin/activate
python src/main.py
```

## How It Works

1. **Startup**: The application loads configuration from environment variables and tests Immich connectivity
2. **Real-time Monitoring**: Uses watchdog library to monitor watch directories for file system events
3. **File Stability**: Waits for files to stabilize (stop changing size) before processing
4. **Multi-threaded Processing**: For each stable image/video file:
   - Validates file type, size, and permissions
   - Uploads to Immich via the `/api/assets` endpoint with retry logic
   - Moves the file to the archive directory on successful upload
   - Updates processing statistics
5. **Logging**: Comprehensive logging with configurable levels and detailed error handling

## Project Structure

```
├── src/
│   ├── main.py             # Application entry point with signal handling
│   ├── config.py           # Environment variable parsing and configuration
│   ├── file_watcher.py     # Real-time directory monitoring using watchdog
│   ├── immich_client.py    # HTTP client for Immich API with retry logic
│   ├── file_processor.py   # Multi-threaded file processing and archiving
│   └── requirements.txt    # Python dependencies
├── tests/                  # Comprehensive test suite (72 tests, 73% coverage)
├── devbox.json             # Devbox configuration with Python environment
├── .env.example            # Example environment configuration
└── README.md               # This file
```

## Troubleshooting

### Common Issues

1. **API Key Invalid**: Ensure your API key is correctly set and has the necessary permissions
2. **Network Errors**: Check that your Immich server is accessible from the machine running the uploader
3. **Permission Errors**: Ensure the application has read access to watch directories and write access to the archive directory
4. **File Not Uploading**: Check file size limits and supported extensions

### Debugging

Set `LOG_LEVEL=DEBUG` in your `.env` file for detailed logging information.

## Development Notes

This project uses:
- **Python 3.11+**: Modern Python with type hints and comprehensive error handling
- **Devbox**: For reproducible development environments with automatic virtual environment management
- **Watchdog**: Cross-platform file system monitoring library
- **Requests**: HTTP library with built-in retry logic for reliable API communication

For development contributions, ensure you have devbox installed and use `devbox shell` to enter the development environment with all dependencies automatically installed.