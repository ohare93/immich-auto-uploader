# Immich Auto-Uploader

**Stop manually uploading photos and videos to your Immich server.** This tool automatically monitors whichever directories you want (Downloads, camera imports, etc.), uploads new media files to Immich as soon as they appear, then safely archives them.

Perfect for monitoring download folders for media files.

## How It Works

1. **Monitor**: Watches your specified directories for new image and video files
2. **Stabilize**: Waits for files to finish copying/downloading (no more size changes)
3. **Upload**: Sends files to your Immich server via API
4. **Archive**: Moves successfully uploaded files to your archive directory
5. **Repeat**: Continues monitoring in real-time

The uploader is smart about file handling - it won't upload partially downloaded files, duplicates, or files that are too large. All activity is logged for troubleshooting.

## Basic Configuration

Create a `.env` file with these properties:

```env
# Required: Your Immich server details
IMMICH_API_URL=http://localhost:2283/api
IMMICH_API_KEY=your_api_key_here

# Directories to monitor (comma-separated)
WATCH_DIRECTORIES=/home/user/Downloads,/home/user/Pictures/Camera

# Where to move uploaded files
ARCHIVE_DIRECTORY=/home/user/Pictures/Archived
```

**Getting your API key**: Log into Immich → User Settings → API Keys → Create new key

## Run / Install

### Method 1: Poetry

**Requirements**: [Poetry](https://python-poetry.org/) installed

```bash
# Install dependencies with Poetry
poetry install

# Configure
cp .env.example .env
# Edit .env with your settings

# Run
poetry run python src/main.py

# Or activate the shell and run directly
poetry shell
python src/main.py
```

**To run as a service**, create a systemd unit or use your system's service manager.

### Method 2: Devbox

**Requirements**: [Devbox](https://www.jetify.com/devbox) installed

```bash
# Enter dev environment (auto-installs Python + dependencies)
devbox shell

# Run
devbox run dev
```

### Method 3: NixOS / Home Manager Service

Add to your NixOS configuration:

```nix
# For system-wide service
services.immich-auto-uploader = {
  enable = true;
  user = "immich-uploader"; # Optional: custom user
  environment = {
    IMMICH_API_URL = "https://immich.example.com";
    WATCH_DIRECTORIES = "/home/user/Downloads,/home/user/Pictures/Import";
    ARCHIVE_DIRECTORY = "/home/user/Pictures/Archived";
    LOG_LEVEL = "INFO";
  };
  environmentFile = "/run/secrets/immich-uploader-env";
};

# For user service (home-manager)
services.immich-auto-uploader-user = {
  enable = true;
  sourceDirectory = "/home/user/immich-auto-uploader";
  environment = {
    IMMICH_API_URL = "https://immich.example.com";
    WATCH_DIRECTORIES = "${config.home.homeDirectory}/Downloads";
    ARCHIVE_DIRECTORY = "${config.home.homeDirectory}/Pictures/Archived";
  };
  environmentFile = "${config.home.homeDirectory}/.config/immich-auto-uploader/.env";
};
```

The environment file should contain your sensitive API key:

```env
IMMICH_API_KEY=your_secret_api_key_here
```

## Advanced Configuration

All settings can be configured via environment variables:

| Variable                        | Description                               | Default                                                          |
| ------------------------------- | ----------------------------------------- | ---------------------------------------------------------------- |
| **Required**                    |
| `IMMICH_API_URL`                | Your Immich server API endpoint           | -                                                                |
| `IMMICH_API_KEY`                | API key from Immich user settings         | -                                                                |
| `WATCH_DIRECTORIES`             | Comma-separated directories to monitor    | -                                                                |
| `ARCHIVE_DIRECTORY`             | Where to move uploaded files              | -                                                                |
| **Optional**                    |
| `WATCH_RECURSIVE`               | Monitor subdirectories (true/false)       | `true`                                                           |
| **File Handling**               |
| `SUPPORTED_EXTENSIONS`          | File types to process                     | `jpg,jpeg,png,gif,bmp,tiff,webp,mp4,mov,avi,mkv,wmv,flv,m4v,3gp` |
| `MAX_FILE_SIZE_MB`              | Maximum file size to process              | `1000`                                                           |
| `FILE_STABILITY_WAIT_SECONDS`   | Wait time for file size to stabilize      | `5`                                                              |
| `FILE_STABILITY_CHECK_INTERVAL` | Seconds between stability checks          | `1.0`                                                            |
| **System**                      |
| `LOG_LEVEL`                     | Logging detail (DEBUG/INFO/WARNING/ERROR) | `INFO`                                                           |

### Example: High-Volume Setup

```env
# For processing lots of large video files
MAX_FILE_SIZE_MB=5000
FILE_STABILITY_WAIT_SECONDS=30
SUPPORTED_EXTENSIONS=mp4,mov,avi,mkv,m4v
LOG_LEVEL=DEBUG
```

### Example: Minimal Photo Setup

```env
# Only photos, smaller files
SUPPORTED_EXTENSIONS=jpg,jpeg,png,heic
MAX_FILE_SIZE_MB=50
FILE_STABILITY_WAIT_SECONDS=2
WATCH_RECURSIVE=false
```

## Troubleshooting

### Debug Mode

Set `LOG_LEVEL=DEBUG` in your `.env` file for detailed logging:

```bash
LOG_LEVEL=DEBUG python src/main.py
```

This will show:

- Every file system event detected
- File stability checking progress
- API request/response details
- Archive operations

## Development

### Running Tests

```bash
# With Poetry
poetry run pytest
poetry run pytest --cov=src --cov-report=html

# With devbox
devbox run test
devbox run test-coverage

# With Python directly
pip install pytest pytest-cov
pytest
pytest --cov=src --cov-report=html
```

### Development Environment

The project uses devbox for reproducible development with automatic virtual environment management. Python 3.11+ with type hints and comprehensive error handling.

**Key Dependencies:**

- `requests` - HTTP client with retry logic
- `watchdog` - Cross-platform file system monitoring
- `python-dotenv` - Environment variable loading
- `notify-py` - Desktop notifications (optional)
