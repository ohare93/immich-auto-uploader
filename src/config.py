import os
import logging
from pathlib import Path
from typing import List, Optional
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()


class Config:
    """Configuration management for Immich Auto-Uploader"""

    def __init__(self):
        self.immich_api_url = self._get_required_env("IMMICH_API_URL")
        self.immich_api_key = self._get_required_env("IMMICH_API_KEY")
        self.watch_directories = self._get_required_list_env("WATCH_DIRECTORIES")
        self.archive_directory = self._get_required_env("ARCHIVE_DIRECTORY")
        self.supported_extensions = self._get_list_env(
            "SUPPORTED_EXTENSIONS",
            [
                "jpg",
                "jpeg",
                "png",
                "gif",
                "bmp",
                "tiff",
                "webp",
                "mp4",
                "mov",
                "avi",
                "mkv",
                "wmv",
                "flv",
                "m4v",
                "3gp",
            ],
        )
        self.poll_interval_seconds = int(self._get_env("POLL_INTERVAL_SECONDS", "10"))
        self.log_level = self._get_env("LOG_LEVEL", "INFO").upper()
        self.max_file_size_mb = int(self._get_env("MAX_FILE_SIZE_MB", "1000"))
        self.file_stability_wait_seconds = int(self._get_env("FILE_STABILITY_WAIT_SECONDS", "5"))
        self.file_stability_check_interval = float(self._get_env("FILE_STABILITY_CHECK_INTERVAL", "1.0"))
        self.file_stability_wait_seconds_video = int(self._get_env("FILE_STABILITY_WAIT_SECONDS_VIDEO", "30"))
        self.min_stability_wait_size_mb = int(self._get_env("MIN_STABILITY_WAIT_SIZE_MB", "100"))
        self.verify_video_integrity = self._get_env("VERIFY_VIDEO_INTEGRITY", "true").lower() in ("true", "1", "yes", "on")
        self.watch_recursive = self._get_env("WATCH_RECURSIVE", "true").lower() in ("true", "1", "yes", "on")
        
        # Notification settings
        self.enable_notifications = self._get_env("ENABLE_NOTIFICATIONS", "true").lower() in ("true", "1", "yes", "on")
        self.notification_batch_size = int(self._get_env("NOTIFICATION_BATCH_SIZE", "999999"))  # Effectively disable count-based batching
        self.notification_batch_timeout = int(self._get_env("NOTIFICATION_BATCH_TIMEOUT", "30"))

        self._validate_config()
        self._setup_logging()

    def _get_required_env(self, key: str) -> str:
        """Get a required environment variable"""
        value = os.getenv(key)
        if not value:
            raise ValueError(f"Required environment variable {key} is not set")
        return value

    def _get_env(self, key: str, default: str) -> str:
        """Get an optional environment variable with default"""
        return os.getenv(key, default)

    def _get_list_env(self, key: str, default: List[str]) -> List[str]:
        """Get a comma-separated list from environment variable"""
        value = os.getenv(key)
        if not value:
            return default
        return [item.strip() for item in value.split(",") if item.strip()]

    def _get_required_list_env(self, key: str) -> List[str]:
        """Get a required comma-separated list from environment variable"""
        value = os.getenv(key)
        if not value:
            raise ValueError(f"Required environment variable {key} is not set")
        result = [item.strip() for item in value.split(",") if item.strip()]
        if not result:
            raise ValueError(f"Environment variable {key} cannot be empty")
        return result

    def _validate_config(self):
        """Validate configuration values"""
        if not self.immich_api_url.startswith(("http://", "https://")):
            raise ValueError("IMMICH_API_URL must start with http:// or https://")

        if self.poll_interval_seconds < 1:
            raise ValueError("POLL_INTERVAL_SECONDS must be at least 1")

        if self.max_file_size_mb < 1:
            raise ValueError("MAX_FILE_SIZE_MB must be at least 1")

        if self.file_stability_wait_seconds < 1:
            raise ValueError("FILE_STABILITY_WAIT_SECONDS must be at least 1")

        if self.file_stability_check_interval < 0.1:
            raise ValueError("FILE_STABILITY_CHECK_INTERVAL must be at least 0.1")
        
        if self.file_stability_wait_seconds_video < self.file_stability_wait_seconds:
            raise ValueError("FILE_STABILITY_WAIT_SECONDS_VIDEO must be at least FILE_STABILITY_WAIT_SECONDS")
        
        if self.min_stability_wait_size_mb < 0:
            raise ValueError("MIN_STABILITY_WAIT_SIZE_MB must be non-negative")

        if self.notification_batch_size < 1:
            raise ValueError("NOTIFICATION_BATCH_SIZE must be at least 1")
        
        if self.notification_batch_timeout < 1:
            raise ValueError("NOTIFICATION_BATCH_TIMEOUT must be at least 1 second")

        # Validate watch directories exist and are accessible
        for directory in self.watch_directories:
            expanded_dir = os.path.expanduser(directory)
            if not os.path.exists(expanded_dir):
                raise ValueError(f"Watch directory does not exist: {expanded_dir}")
            if not os.path.isdir(expanded_dir):
                raise ValueError(f"Watch path is not a directory: {expanded_dir}")
            if not os.access(expanded_dir, os.R_OK):
                raise ValueError(f"Watch directory is not readable: {expanded_dir}")
        
        # Normalize and resolve archive directory path
        self.archive_directory_resolved = Path(os.path.expanduser(self.archive_directory)).resolve()

    def _setup_logging(self):
        """Setup logging configuration"""
        log_levels = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
        }

        level = log_levels.get(self.log_level, logging.INFO)
        logging.basicConfig(
            level=level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    def is_supported_file(self, filename: str) -> bool:
        """Check if a file has a supported extension"""
        extension = filename.lower().split(".")[-1] if "." in filename else ""
        return extension in self.supported_extensions

    def get_file_size_limit_bytes(self) -> int:
        """Get the file size limit in bytes"""
        return self.max_file_size_mb * 1024 * 1024
    
    def is_in_archive_directory(self, file_path: str) -> bool:
        """Check if a file path is within the archive directory"""
        try:
            file_path_resolved = Path(file_path).resolve()
            # Check if the file path is within the archive directory tree
            return self.archive_directory_resolved in file_path_resolved.parents or file_path_resolved == self.archive_directory_resolved
        except (OSError, ValueError):
            # If path resolution fails, err on the side of caution and exclude
            return True

    def __str__(self) -> str:
        """String representation of configuration (without sensitive data)"""
        return f"""Configuration:
  API URL: {self.immich_api_url}
  API Key: {self.immich_api_key[0:5]}{20 * '*'}
  Watch directories: {', '.join(self.watch_directories)}
  Archive directory: {self.archive_directory}
  Supported extensions: {', '.join(self.supported_extensions)}
  Poll interval: {self.poll_interval_seconds} seconds
  Log level: {self.log_level}
  Max file size: {self.max_file_size_mb} MB
  File stability wait: {self.file_stability_wait_seconds} seconds
  File stability check interval: {self.file_stability_check_interval} seconds
  File stability wait for videos: {self.file_stability_wait_seconds_video} seconds
  Min size for extended stability: {self.min_stability_wait_size_mb} MB
  Verify video integrity: {self.verify_video_integrity}
  Watch recursive: {self.watch_recursive}
  Notifications enabled: {self.enable_notifications}
  Notification batch size: {self.notification_batch_size}
  Notification batch timeout: {self.notification_batch_timeout} seconds"""

