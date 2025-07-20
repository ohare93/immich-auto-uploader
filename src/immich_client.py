import os
import logging
import hashlib
from typing import Optional, Dict, Any
from pathlib import Path
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config import Config
from file_watcher import FileInfo

logger = logging.getLogger(__name__)

class ImmichUploadResult:
    """Result of an Immich upload operation"""
    
    def __init__(self, success: bool, message: str, asset_id: Optional[str] = None):
        self.success = success
        self.message = message
        self.asset_id = asset_id
    
    def __str__(self) -> str:
        return f"UploadResult(success={self.success}, message='{self.message}', asset_id={self.asset_id})"


class ImmichClient:
    """Client for uploading files to Immich"""
    
    def __init__(self, config: Config):
        self.config = config
        self.session = self._create_session()
        self.device_id = "immich-auto-uploader"
    
    def _create_session(self) -> requests.Session:
        """Create a requests session with retry strategy"""
        session = requests.Session()
        
        # Setup retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Set default headers
        session.headers.update({
            'x-api-key': self.config.immich_api_key,
            'User-Agent': 'immich-auto-uploader/1.0'
        })
        
        return session
    
    def upload_asset(self, file_info: FileInfo) -> ImmichUploadResult:
        """Upload a file to Immich"""
        try:
            logger.info(f"Starting upload of {file_info.path}")
            
            # Validate file before upload
            if not file_info.is_valid(self.config):
                return ImmichUploadResult(False, "File is not valid for upload")
            
            # Generate device asset ID
            device_asset_id = self._generate_device_asset_id(file_info)
            
            # Prepare upload data
            upload_data = {
                'deviceAssetId': device_asset_id,
                'deviceId': self.device_id,
                'fileCreatedAt': self._format_timestamp(file_info.modified_time),
                'fileModifiedAt': self._format_timestamp(file_info.modified_time),
                'isFavorite': 'false'
            }
            
            # Determine content type
            content_type = self._get_content_type(file_info.extension)
            
            # Prepare files for multipart upload
            with open(file_info.path, 'rb') as f:
                files = {
                    'assetData': (file_info.name, f, content_type)
                }
                
                # Make the upload request
                url = f"{self.config.immich_api_url.rstrip('/')}/api/assets"
                
                logger.debug(f"Uploading to: {url}")
                logger.debug(f"Upload data: {upload_data}")
                
                response = self.session.post(
                    url,
                    data=upload_data,
                    files=files,
                    timeout=60
                )
            
            # Handle response
            if response.status_code == 200 or response.status_code == 201:
                try:
                    result_data = response.json()
                    asset_id = result_data.get('id')
                    logger.info(f"Successfully uploaded {file_info.name} (asset_id: {asset_id})")
                    return ImmichUploadResult(True, "Upload successful", asset_id)
                except ValueError:
                    logger.info(f"Successfully uploaded {file_info.name}")
                    return ImmichUploadResult(True, "Upload successful")
            
            elif response.status_code == 400:
                error_msg = "Bad request - check file format and API parameters"
                logger.error(f"Upload failed for {file_info.name}: {error_msg}")
                return ImmichUploadResult(False, error_msg)
            
            elif response.status_code == 401:
                error_msg = "Unauthorized - check API key"
                logger.error(f"Upload failed for {file_info.name}: {error_msg}")
                return ImmichUploadResult(False, error_msg)
            
            elif response.status_code == 409:
                # Asset already exists - this might be OK
                logger.info(f"Asset already exists in Immich: {file_info.name}")
                return ImmichUploadResult(True, "Asset already exists")
            
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                logger.error(f"Upload failed for {file_info.name}: {error_msg}")
                return ImmichUploadResult(False, error_msg)
        
        except requests.exceptions.RequestException as e:
            error_msg = f"Network error: {str(e)}"
            logger.error(f"Upload failed for {file_info.name}: {error_msg}")
            return ImmichUploadResult(False, error_msg)
        
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(f"Upload failed for {file_info.name}: {error_msg}")
            return ImmichUploadResult(False, error_msg)
    
    def _generate_device_asset_id(self, file_info: FileInfo) -> str:
        """Generate a unique device asset ID for the file"""
        # Create a unique ID based on file path, size, and modification time
        unique_string = f"{file_info.path}_{file_info.size_bytes}_{file_info.modified_time}"
        return hashlib.md5(unique_string.encode()).hexdigest()
    
    def _format_timestamp(self, timestamp: float) -> str:
        """Format timestamp for Immich API"""
        # Convert to ISO 8601 format with milliseconds
        import datetime
        dt = datetime.datetime.fromtimestamp(timestamp, tz=datetime.timezone.utc)
        return dt.isoformat().replace('+00:00', 'Z')
    
    def _get_content_type(self, extension: str) -> str:
        """Get MIME type for file extension"""
        mime_types = {
            # Images
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'png': 'image/png',
            'gif': 'image/gif',
            'bmp': 'image/bmp',
            'tiff': 'image/tiff',
            'webp': 'image/webp',
            
            # Videos
            'mp4': 'video/mp4',
            'mov': 'video/quicktime',
            'avi': 'video/x-msvideo',
            'mkv': 'video/x-matroska',
            'wmv': 'video/x-ms-wmv',
            'flv': 'video/x-flv',
            'm4v': 'video/x-m4v',
            '3gp': 'video/3gpp'
        }
        
        return mime_types.get(extension.lower(), 'application/octet-stream')
    
    def test_connection(self) -> bool:
        """Test connection to Immich server"""
        try:
            url = f"{self.config.immich_api_url.rstrip('/')}/api/server/ping"
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                logger.info("Successfully connected to Immich server")
                return True
            else:
                logger.error(f"Failed to connect to Immich server: HTTP {response.status_code}")
                return False
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to connect to Immich server: {e}")
            return False
    
    def close(self):
        """Close the session"""
        self.session.close()