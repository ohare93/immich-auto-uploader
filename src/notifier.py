import logging
import time
import threading
from typing import Optional

logger = logging.getLogger(__name__)

class Notifier:
    """Handles OS notifications for upload events using notify_py"""
    
    def __init__(self, enabled: bool = True, batch_size: int = 5, batch_timeout: int = 300):
        self.enabled = enabled
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        
        self.upload_count = 0
        self.last_notification_time = time.time()
        self._lock = threading.Lock()
        self._notification_available = False
        self._upload_session_started = False
        
        if self.enabled:
            self._test_notification_capability()
    
    def _test_notification_capability(self):
        """Test if notifications are available on this system"""
        try:
            from notifypy import Notify
            
            # Just test that we can import and create notification object
            notification = Notify()
            
            self._notification_available = True
            logger.debug("Using notify-py for cross-platform notifications")
            
        except ImportError:
            logger.warning("notify-py not available, disabling notifications")
            self.enabled = False
        except Exception as e:
            logger.warning(f"Notification test failed, disabling notifications: {e}")
            self.enabled = False
    
    def notify_upload_start(self):
        """Called when upload processing begins"""
        if not self.enabled or not self._notification_available:
            return
        
        with self._lock:
            if not self._upload_session_started:
                self._upload_session_started = True
                # Send immediate notification that uploading is starting
                threading.Thread(
                    target=self._send_start_notification_async,
                    daemon=True
                ).start()
    
    def notify_upload_success(self, filename: str):
        """Called when a file is successfully uploaded"""
        if not self.enabled or not self._notification_available:
            return
        
        with self._lock:
            self.upload_count += 1
            current_time = time.time()
            
            # Check if we should send a notification (time-based only)
            should_notify = (current_time - self.last_notification_time) >= self.batch_timeout
            
            if should_notify:
                self._send_notification()
    
    def _send_notification(self):
        """Send the actual notification (called with lock held)"""
        if self.upload_count == 0:
            return
        
        count = self.upload_count
        self.upload_count = 0
        self.last_notification_time = time.time()
        
        # Determine message
        if count == 1:
            message = "1 file uploaded to Immich"
        else:
            message = f"{count} files uploaded to Immich"
        
        # Send notification in background thread to avoid blocking
        threading.Thread(
            target=self._send_notification_async,
            args=(message,),
            daemon=True
        ).start()
    
    def _send_start_notification_async(self):
        """Send 'Uploading assets...' notification asynchronously"""
        try:
            from notifypy import Notify
            
            notification = Notify()
            notification.title = "Immich Auto-Uploader"
            notification.message = "Uploading assets..."
            notification.send()
            
            logger.debug("Sent upload start notification")
            
        except Exception as e:
            logger.debug(f"Failed to send start notification: {e}")
    
    def _send_notification_async(self, message: str):
        """Send notification asynchronously using notifypy"""
        try:
            from notifypy import Notify
            
            notification = Notify()
            notification.title = "Immich Auto-Uploader"
            notification.message = message
            notification.send()
            
            logger.debug(f"Sent notification: {message}")
            
        except Exception as e:
            logger.debug(f"Failed to send notification: {e}")
    
    def force_notification(self):
        """Force send any pending notifications"""
        if not self.enabled or not self._notification_available:
            return
        
        with self._lock:
            if self.upload_count > 0:
                self._send_notification()
    
    def get_pending_count(self) -> int:
        """Get the current pending upload count"""
        with self._lock:
            return self.upload_count