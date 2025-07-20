import os
import logging
from typing import List, Optional
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()


class Config:
    """Configuration management for Immich Auto-Uploader"""

    def __init__(self):
        self.immich_api_url = self._get_required_env("IMMICH_API_URL")
        self.immich_api_key = self._get_required_env("IMMICH_API_KEY")
        self.watch_directories = self._get_list_env(
            "WATCH_DIRECTORIES", [os.path.expanduser("~/Downloads")]
        )
        self.archive_directory = self._get_env(
            "ARCHIVE_DIRECTORY", os.path.expanduser("~/Pictures/Archived")
        )
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

        # Ensure watch directories exist
        for directory in self.watch_directories:
            expanded_dir = os.path.expanduser(directory)
            if not os.path.exists(expanded_dir):
                logging.warning(f"Watch directory does not exist: {expanded_dir}")

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
  File stability check interval: {self.file_stability_check_interval} seconds"""

