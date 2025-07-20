#!/usr/bin/env python3
"""
Immich Auto-Uploader

Automatically uploads images and videos to a self-hosted Immich instance
and archives the uploaded files.
"""

import os
import sys
import signal
import logging
import time
from pathlib import Path

# Add src directory to path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent))

from config import Config
from file_watcher import FileWatcher
from file_processor import FileProcessor

logger = logging.getLogger(__name__)

class ImmichAutoUploader:
    """Main application class"""
    
    def __init__(self):
        self.config = None
        self.file_watcher = None
        self.file_processor = None
        self.is_running = False
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down...")
        self.stop()
    
    def start(self):
        """Start the application"""
        try:
            logger.info("Starting Immich Auto-Uploader...")
            
            # Load configuration
            self.config = Config()
            logger.info("Configuration loaded:")
            logger.info(str(self.config))
            
            # Initialize file processor
            self.file_processor = FileProcessor(self.config)
            self.file_processor.start()
            
            # Initialize file watcher
            self.file_watcher = FileWatcher(
                self.config, 
                self.file_processor.process_file
            )
            self.file_watcher.start()
            
            self.is_running = True
            logger.info("Immich Auto-Uploader started successfully")
            
            # Main loop
            self._main_loop()
            
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
        except Exception as e:
            logger.error(f"Failed to start application: {e}")
            sys.exit(1)
        finally:
            self.stop()
    
    def stop(self):
        """Stop the application"""
        if not self.is_running:
            return
        
        logger.info("Stopping Immich Auto-Uploader...")
        self.is_running = False
        
        # Stop file watcher
        if self.file_watcher:
            self.file_watcher.stop()
        
        # Stop file processor
        if self.file_processor:
            self.file_processor.stop()
        
        logger.info("Immich Auto-Uploader stopped")
    
    def _main_loop(self):
        """Main application loop"""
        stats_interval = 300  # Log stats every 5 minutes
        last_stats_time = time.time()
        
        while self.is_running:
            try:
                # Sleep for a short time
                time.sleep(1)
                
                # Periodically log statistics
                current_time = time.time()
                if current_time - last_stats_time >= stats_interval:
                    if self.file_processor:
                        stats = self.file_processor.get_stats()
                        logger.info(stats.get_summary())
                    last_stats_time = current_time
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                time.sleep(5)  # Brief pause before continuing


def check_environment():
    """Check if required environment variables are set"""
    required_vars = ['IMMICH_API_URL', 'IMMICH_API_KEY']
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print("ERROR: Missing required environment variables:")
        for var in missing_vars:
            print(f"  - {var}")
        print("\nPlease set these environment variables and try again.")
        print("Example:")
        print("  export IMMICH_API_URL='https://your-immich-server.com'")
        print("  export IMMICH_API_KEY='your-api-key-here'")
        return False
    
    return True


def main():
    """Main entry point"""
    print("Immich Auto-Uploader v1.0")
    print("=" * 40)
    
    # Check environment
    if not check_environment():
        sys.exit(1)
    
    # Create and start application
    app = ImmichAutoUploader()
    
    try:
        app.start()
    except Exception as e:
        logger.error(f"Application failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()