import os
import logging
import shutil
import time
from pathlib import Path
from typing import Set, Dict, Any
import threading
from queue import Queue, Empty

from config import Config
from file_watcher import FileInfo
from immich_client import ImmichClient, ImmichUploadResult

logger = logging.getLogger(__name__)

class ProcessingStats:
    """Statistics for file processing"""
    
    def __init__(self):
        self.total_files = 0
        self.successful_uploads = 0
        self.failed_uploads = 0
        self.skipped_files = 0
        self.archived_files = 0
        self.start_time = time.time()
        self._lock = threading.Lock()
    
    def increment_total(self):
        with self._lock:
            self.total_files += 1
    
    def increment_success(self):
        with self._lock:
            self.successful_uploads += 1
    
    def increment_failed(self):
        with self._lock:
            self.failed_uploads += 1
    
    def increment_skipped(self):
        with self._lock:
            self.skipped_files += 1
    
    def increment_archived(self):
        with self._lock:
            self.archived_files += 1
    
    def get_summary(self) -> str:
        with self._lock:
            runtime = time.time() - self.start_time
            return (f"Processing Stats - Total: {self.total_files}, "
                   f"Success: {self.successful_uploads}, "
                   f"Failed: {self.failed_uploads}, "
                   f"Skipped: {self.skipped_files}, "
                   f"Archived: {self.archived_files}, "
                   f"Runtime: {runtime:.1f}s")


class FileProcessor:
    """Processes files by uploading to Immich and archiving"""
    
    def __init__(self, config: Config):
        self.config = config
        self.immich_client = ImmichClient(config)
        self.stats = ProcessingStats()
        
        # Track processed files to avoid duplicates
        self.processed_files: Set[str] = set()
        self.processing_queue = Queue()
        self.is_running = False
        self.worker_thread = None
        
        # Ensure archive directory exists
        self._ensure_archive_directory()
    
    def start(self):
        """Start the file processor"""
        if self.is_running:
            return
        
        logger.info("Starting file processor...")
        
        # Test connection to Immich
        if not self.immich_client.test_connection():
            raise RuntimeError("Cannot connect to Immich server")
        
        self.is_running = True
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()
        
        logger.info("File processor started")
    
    def stop(self):
        """Stop the file processor"""
        if not self.is_running:
            return
        
        logger.info("Stopping file processor...")
        self.is_running = False
        
        # Add sentinel to wake up worker thread
        self.processing_queue.put(None)
        
        if self.worker_thread:
            self.worker_thread.join(timeout=5)
        
        self.immich_client.close()
        logger.info("File processor stopped")
        
        # Log final statistics
        logger.info(self.stats.get_summary())
    
    def process_file(self, file_info: FileInfo):
        """Add a file to the processing queue"""
        if not self.is_running:
            logger.warning("File processor is not running, ignoring file")
            return
        
        # Check if we've already processed this file
        file_key = self._get_file_key(file_info)
        if file_key in self.processed_files:
            logger.debug(f"File already processed, skipping: {file_info.path}")
            self.stats.increment_skipped()
            return
        
        # Add to processing queue
        self.processing_queue.put(file_info)
        self.stats.increment_total()
        logger.debug(f"Added file to processing queue: {file_info.path}")
    
    def _worker_loop(self):
        """Main worker loop for processing files"""
        logger.info("File processor worker started")
        
        while self.is_running:
            try:
                # Get next file from queue (with timeout)
                file_info = self.processing_queue.get(timeout=1)
                
                # Check for sentinel value (None means stop)
                if file_info is None:
                    break
                
                self._process_single_file(file_info)
                
            except Empty:
                # Timeout is normal, just continue
                continue
            except Exception as e:
                logger.error(f"Error in worker loop: {e}")
        
        logger.info("File processor worker stopped")
    
    def _process_single_file(self, file_info: FileInfo):
        """Process a single file"""
        try:
            logger.info(f"Processing file: {file_info.path}")
            
            # Double-check file is still valid
            if not file_info.is_valid(self.config):
                logger.warning(f"File no longer valid, skipping: {file_info.path}")
                self.stats.increment_skipped()
                return
            
            # Mark as processed to avoid duplicates
            file_key = self._get_file_key(file_info)
            self.processed_files.add(file_key)
            
            # Upload to Immich
            upload_result = self.immich_client.upload_asset(file_info)
            
            if upload_result.success:
                logger.info(f"Upload successful: {file_info.name}")
                self.stats.increment_success()
                
                # Archive the file
                if self._archive_file(file_info):
                    self.stats.increment_archived()
                    logger.info(f"File archived: {file_info.name}")
                else:
                    logger.warning(f"Upload successful but archiving failed: {file_info.name}")
            
            else:
                logger.error(f"Upload failed: {file_info.name} - {upload_result.message}")
                self.stats.increment_failed()
        
        except Exception as e:
            logger.error(f"Error processing file {file_info.path}: {e}")
            self.stats.increment_failed()
    
    def _archive_file(self, file_info: FileInfo) -> bool:
        """Archive a file after successful upload"""
        try:
            archive_dir = Path(self.config.archive_directory)
            archive_path = archive_dir / file_info.name
            
            # Handle filename conflicts
            if archive_path.exists():
                counter = 1
                base_name = file_info.path.stem
                extension = file_info.path.suffix
                
                while archive_path.exists():
                    new_name = f"{base_name}_{counter}{extension}"
                    archive_path = archive_dir / new_name
                    counter += 1
                
                logger.info(f"Renamed archived file to avoid conflict: {archive_path.name}")
            
            # Move the file
            shutil.move(str(file_info.path), str(archive_path))
            logger.debug(f"Moved {file_info.path} to {archive_path}")
            
            return True
        
        except Exception as e:
            logger.error(f"Failed to archive file {file_info.path}: {e}")
            return False
    
    def _ensure_archive_directory(self):
        """Ensure the archive directory exists"""
        archive_dir = Path(self.config.archive_directory)
        
        try:
            archive_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Archive directory ready: {archive_dir}")
        except Exception as e:
            raise RuntimeError(f"Cannot create archive directory {archive_dir}: {e}")
    
    def _get_file_key(self, file_info: FileInfo) -> str:
        """Generate a unique key for a file to track processing"""
        return f"{file_info.path}_{file_info.size_bytes}_{file_info.modified_time}"
    
    def get_stats(self) -> ProcessingStats:
        """Get current processing statistics"""
        return self.stats
    
    def is_processing(self) -> bool:
        """Check if processor is currently running"""
        return self.is_running