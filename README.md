# Immich Auto-Uploader

A Gren application that automatically monitors directories for images and videos, uploads them to a self-hosted Immich instance, and archives the uploaded files.

## Features

- **Automatic monitoring**: Watches configured directories for new image and video files
- **Immich integration**: Uploads assets to your self-hosted Immich server via API
- **File archiving**: Moves uploaded files to an archive directory after successful upload
- **Configurable**: Environment-based configuration for flexibility
- **Type-safe**: Written in Gren for reliability and maintainability
- **Efficient**: Polling-based monitoring with configurable intervals

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

3. **Initialize the Gren project** (first time only):
   ```bash
   devbox run init
   ```

4. **Configure the application**:
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
| `SUPPORTED_EXTENSIONS` | File extensions to process | `jpg,jpeg,png,gif,bmp,tiff,webp,mp4,mov,avi,mkv,wmv,flv,m4v,3gp` |
| `POLL_INTERVAL_SECONDS` | How often to check for new files | `10` |
| `LOG_LEVEL` | Logging verbosity (DEBUG, INFO, WARN, ERROR) | `INFO` |
| `MAX_FILE_SIZE_MB` | Maximum file size to process | `1000` |

## Usage

### Development

Run the application in development mode:
```bash
devbox run dev
```

### Building

Build the optimized application:
```bash
devbox run build
```

The compiled application will be in `dist/main.js`.

### Production

To run in production, ensure your `.env` file is configured and run:
```bash
node dist/main.js
```

## How It Works

1. **Startup**: The application loads configuration from environment variables
2. **Monitoring**: Every `POLL_INTERVAL_SECONDS`, it scans the watch directories
3. **Processing**: For each new image/video file found:
   - Validates file type and size
   - Uploads to Immich via the `/api/assets` endpoint
   - Moves the file to the archive directory on successful upload
4. **Logging**: Provides detailed logs based on the configured log level

## Project Structure

```
├── src/
│   ├── Main.gren           # Application entry point
│   ├── Config.gren         # Configuration loading and parsing
│   ├── FileWatcher.gren    # Directory monitoring and file detection
│   ├── ImmichAPI.gren      # Immich API integration
│   └── FileProcessor.gren  # File processing and archiving logic
├── devbox.json             # Devbox configuration
├── gren.json               # Gren project configuration
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
- **Gren**: A pure functional language for reliable applications
- **Devbox**: For reproducible development environments
- **Node.js**: As the runtime platform for the compiled Gren code

For development contributions, ensure you have devbox installed and use `devbox shell` to enter the development environment.