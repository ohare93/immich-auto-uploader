import os
import logging
import time
from pathlib import Path
from typing import List, Callable, Set
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent, FileModifiedEvent

from config import Config

logger = logging.getLogger(__name__)

class FileInfo:
    """Information about a file to be processed"""
    
    def __init__(self, path: str):
        self.path = Path(path)
        self.name = self.path.name
        self.extension = self.path.suffix.lower().lstrip('.')
        
        try:
            stat = self.path.stat()
            self.size_bytes = stat.st_size
            self.modified_time = stat.st_mtime
        except (OSError, FileNotFoundError):
            self.size_bytes = 0
            self.modified_time = 0
    
    def is_valid(self, config: Config) -> bool:
        """Check if file is valid for processing"""
        try:
            # Check if file still exists
            if not self.path.exists():
                return False
            
            # Check if it's actually a file (not directory)
            if not self.path.is_file():
                return False
            
            # Check file size
            if self.size_bytes > config.get_file_size_limit_bytes():
                logger.warning(f"File too large: {self.path} ({self.size_bytes} bytes)")
                return False
            
            # Check if file is supported
            if not config.is_supported_file(self.name):
                return False
            
            # Check if file is in archive directory (never process archived files)
            if config.is_in_archive_directory(str(self.path)):
                logger.debug(f"File is in archive directory, skipping: {self.path}")
                return False
            
            return True
            
        except (OSError, FileNotFoundError):
            return False
    
    def __str__(self) -> str:
        return f"FileInfo(path={self.path}, size={self.size_bytes}, ext={self.extension})"


class ImmichFileHandler(FileSystemEventHandler):
    """File system event handler for Immich auto-uploader"""
    
    def __init__(self, config: Config, on_file_ready: Callable[[FileInfo], None]):
        self.config = config
        self.on_file_ready = on_file_ready
        self.processing_files: Set[str] = set()
        
    def on_created(self, event):
        if not event.is_directory:
            self._handle_file_event(event.src_path)
    
    def on_modified(self, event):
        if not event.is_directory:
            self._handle_file_event(event.src_path)
    
    def _handle_file_event(self, file_path: str):
        """Handle a file system event"""
        file_path = os.path.abspath(file_path)
        
        # Avoid processing the same file multiple times
        if file_path in self.processing_files:
            return
        
        logger.debug(f"File event detected: {file_path}")
        
        # Add to processing set to avoid duplicates
        self.processing_files.add(file_path)
        
        try:
            # Wait for file to become stable
            if self._wait_for_file_stability(file_path):
                file_info = FileInfo(file_path)
                
                if file_info.is_valid(self.config):
                    logger.info(f"New file ready for processing: {file_info}")
                    self.on_file_ready(file_info)
                else:
                    logger.debug(f"File not valid for processing: {file_path}")
            else:
                logger.warning(f"File did not stabilize within timeout: {file_path}")
        
        except Exception as e:
            logger.error(f"Error processing file event for {file_path}: {e}")
        
        finally:
            # Remove from processing set
            self.processing_files.discard(file_path)

    def _wait_for_file_stability(self, file_path: str) -> bool:
        """Wait for file to become stable (size stops changing)"""
        path = Path(file_path)
        
        if not path.exists():
            logger.debug(f"File no longer exists during stability check: {file_path}")
            return False
        
        try:
            # Get initial file size
            last_size = path.stat().st_size
            logger.debug(f"Starting stability check for {file_path} (initial size: {last_size} bytes)")
            
            stable_start_time = None
            
            while True:
                
                # Wait before checking again
                time.sleep(self.config.file_stability_check_interval)
                
                # Check if file still exists
                if not path.exists():
                    logger.debug(f"File disappeared during stability check: {file_path}")
                    return False
                
                # Get current file size
                try:
                    current_size = path.stat().st_size
                except (OSError, FileNotFoundError):
                    logger.debug(f"Could not get file size during stability check: {file_path}")
                    return False
                
                # Check if size has changed
                if current_size != last_size:
                    logger.debug(f"File size changed: {file_path} ({last_size} -> {current_size} bytes)")
                    last_size = current_size
                    stable_start_time = None  # Reset stability timer
                else:
                    # Size hasn't changed
                    if stable_start_time is None:
                        stable_start_time = time.time()
                        logger.debug(f"File size stable, starting stability timer: {file_path} ({current_size} bytes)")
                    
                    # Check if file has been stable long enough
                    stable_duration = time.time() - stable_start_time
                    if stable_duration >= self.config.file_stability_wait_seconds:
                        logger.debug(f"File is stable for {stable_duration:.1f}s: {file_path} ({current_size} bytes)")
                        return True
        
        except Exception as e:
            logger.error(f"Error during file stability check for {file_path}: {e}")
            return False


class FileWatcher:
    """Watches directories for new image and video files"""
    
    def __init__(self, config: Config, on_file_ready: Callable[[FileInfo], None]):
        self.config = config
        self.on_file_ready = on_file_ready
        self.observer = Observer()
        self.handler = ImmichFileHandler(config, on_file_ready)
        self.is_running = False
    
    def start(self):
        """Start watching directories"""
        if self.is_running:
            return
        
        logger.info("Starting file watcher...")
        
        # Schedule watching for each directory
        for directory in self.config.watch_directories:
            expanded_dir = os.path.expanduser(directory)
            if os.path.exists(expanded_dir):
                self.observer.schedule(self.handler, expanded_dir, recursive=self.config.watch_recursive)
                logger.info(f"Watching directory: {expanded_dir}")
            else:
                logger.warning(f"Watch directory does not exist: {expanded_dir}")
        
        self.observer.start()
        self.is_running = True
        logger.info("File watcher started")
        
        # Perform initial scan of existing files
        self._initial_scan()
    
    def stop(self):
        """Stop watching directories"""
        if not self.is_running:
            return
        
        logger.info("Stopping file watcher...")
        self.observer.stop()
        self.observer.join()
        self.is_running = False
        logger.info("File watcher stopped")
    
    def _initial_scan(self):
        """Perform initial scan of existing files in watch directories"""
        logger.info("Performing initial scan of existing files...")
        
        for directory in self.config.watch_directories:
            expanded_dir = os.path.expanduser(directory)
            if not os.path.exists(expanded_dir):
                continue
            
            try:
                self._scan_directory(Path(expanded_dir), recursive=self.config.watch_recursive)
            except Exception as e:
                logger.error(f"Error scanning directory {expanded_dir}: {e}")
        
        logger.info("Initial scan completed")
    
    def _scan_directory(self, directory: Path, recursive: bool = True):
        """Scan a directory for files, optionally recursively"""
        try:
            for item in directory.iterdir():
                if item.is_file():
                    file_info = FileInfo(str(item))
                    if file_info.is_valid(self.config):
                        logger.info(f"Found existing file: {file_info}")
                        self.on_file_ready(file_info)
                elif item.is_dir() and recursive:
                    self._scan_directory(item, recursive=True)
        except (PermissionError, OSError) as e:
            logger.warning(f"Cannot access {directory}: {e}")
    
    def is_watching(self) -> bool:
        """Check if file watcher is currently running"""
        return self.is_running