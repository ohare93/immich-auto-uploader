# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an Immich Auto-Uploader written in Python. The application monitors directories for images and videos, uploads them to a self-hosted Immich instance, and archives the uploaded files. It uses real-time file monitoring with the watchdog library and provides robust error handling and logging.

## Development Environment

**Required Tools:**
- Devbox for environment management
- Python 3.11+ (installed via devbox)
- Virtual environment (automatically created by devbox)

**Setup Commands:**
```bash
devbox shell              # Enter development environment (auto-installs dependencies)
devbox run dev            # Run the application
devbox run install        # Install/update Python dependencies
devbox run clean          # Clean build artifacts and virtual environment
```

## Architecture

**Core Modules:**
- `src/main.py` - Application entry point with signal handling and main loop
- `src/config.py` - Environment variable parsing and configuration management
- `src/file_watcher.py` - Real-time directory monitoring using watchdog library
- `src/immich_client.py` - HTTP client for Immich API uploads with retry logic
- `src/file_processor.py` - Multi-threaded file processing pipeline and archiving

**Key Design Patterns:**
- Object-oriented design with clear separation of concerns
- Thread-safe file processing with queue-based architecture
- Environment-driven configuration (no hardcoded values)
- Real-time file monitoring (no polling required)
- Comprehensive error handling and logging
- Graceful shutdown with signal handling

## Configuration

Environment variables (loaded from shell environment or `.env` file):
- `IMMICH_API_URL` and `IMMICH_API_KEY` (required) - Immich server URL and API key
- `WATCH_DIRECTORIES` (optional) - Comma-separated paths to monitor (default: ~/Downloads)
- `ARCHIVE_DIRECTORY` (optional) - Directory for processed files (default: ~/Pictures/Archived)
- `SUPPORTED_EXTENSIONS` (optional) - Comma-separated file extensions to process
- `MAX_FILE_SIZE_MB` (optional) - Maximum file size in MB (default: 1000)
- `LOG_LEVEL` (optional) - Logging level: DEBUG, INFO, WARNING, ERROR (default: INFO)

## API Integration

**Immich Upload Endpoint:**
- POST to `/api/assets`
- Multipart form data with file and metadata
- Required fields: deviceAssetId, deviceId, fileCreatedAt, fileModifiedAt
- Authentication via `x-api-key` header

## Development Notes

**Python-Specific Implementation:**
- Uses `requests` library for HTTP operations with retry logic
- `watchdog` library provides real-time file system monitoring
- Threading with `Queue` for async file processing
- `pathlib.Path` for cross-platform file system operations
- Proper signal handling for graceful shutdown

**Testing:**
- Manual testing via `devbox run dev` with sample files
- Application validates configuration and tests Immich connectivity on startup
- Comprehensive logging for debugging and monitoring

**Common Operations:**
- Add new file types: Update `SUPPORTED_EXTENSIONS` config and `_get_content_type()` in `immich_client.py`
- Modify upload logic: Edit `upload_asset()` function in `immich_client.py`
- Change monitoring behavior: Update `FileWatcher` class in `file_watcher.py`
- Adjust logging: Modify log levels in `config.py` or set `LOG_LEVEL` environment variable
- Process statistics: Use `get_stats()` method on `FileProcessor` instance

## Python Development Best Practices

**Code Style:**
- Follow PEP 8 conventions for formatting and naming
- Use type hints where helpful for clarity
- Comprehensive error handling with try/except blocks
- Logging instead of print statements for debugging

**Dependencies:**
- `requests>=2.31.0` - HTTP client with retry capabilities
- `watchdog>=3.0.0` - Cross-platform file system monitoring
- `python-dotenv>=1.0.0` - Environment variable loading from .env files

**Virtual Environment:**
- Devbox automatically creates and manages a virtual environment in `.venv/`
- Dependencies are installed locally, not globally
- Use `devbox run install` to add new dependencies

## Security and Configuration Notes

- **API Key Handling:**
  - IMMICH_API_KEY should be read directly from shell environment
  - Never print or echo out API keys
  - Avoid reading API keys from .env file to prevent accidental exposure

## Reference Links

- Immich api docs https://immich.app/docs/api/