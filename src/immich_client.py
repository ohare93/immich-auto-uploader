import os
import logging
import hashlib
from typing import Optional, Dict, Any, Tuple
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
            
            # For video files, perform integrity check if enabled
            if self.config.verify_video_integrity and self._is_video_file(file_info.extension):
                is_valid, error_msg = self._validate_video_file(file_info.path)
                if not is_valid:
                    logger.error(f"Video integrity check failed for {file_info.name}: {error_msg}")
                    return ImmichUploadResult(False, f"Video integrity check failed: {error_msg}")
            
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
    
    def _is_video_file(self, extension: str) -> bool:
        """Check if file extension indicates a video file"""
        video_extensions = ['mp4', 'mov', 'avi', 'mkv', 'wmv', 'flv', 'm4v', '3gp']
        return extension.lower() in video_extensions
    
    def _validate_video_file(self, file_path: Path) -> Tuple[bool, str]:
        """Validate video file integrity by checking headers and structure"""
        try:
            # Check minimum file size (videos should be at least a few KB)
            file_size = file_path.stat().st_size
            if file_size < 1024:  # Less than 1KB
                return False, "File too small to be a valid video"
            
            # Check file headers for common video formats
            with open(file_path, 'rb') as f:
                header = f.read(12)
                
                if len(header) < 12:
                    return False, "File too small to read header"
                
                # Check for common video file signatures
                if self._check_mp4_header(header):
                    # Additional MP4 validation
                    return self._validate_mp4_file(f, file_size)
                elif self._check_avi_header(header):
                    return True, "Valid AVI file"
                elif self._check_mkv_header(header):
                    return True, "Valid MKV file"
                elif header[4:12] == b'ftypqt  ':  # MOV
                    return True, "Valid MOV file"
                else:
                    # For other formats, just check if we can read the entire file
                    try:
                        f.seek(0)
                        chunk_size = 1024 * 1024  # 1MB chunks
                        while f.read(chunk_size):
                            pass
                        return True, "File readable"
                    except Exception:
                        return False, "Cannot read entire file"
                        
        except FileNotFoundError:
            return False, "File not found"
        except PermissionError:
            return False, "Permission denied"
        except Exception as e:
            return False, f"Validation error: {str(e)}"
    
    def _check_mp4_header(self, header: bytes) -> bool:
        """Check if file has MP4 header"""
        # MP4 files have 'ftyp' at bytes 4-7
        return len(header) >= 8 and header[4:8] == b'ftyp'
    
    def _check_avi_header(self, header: bytes) -> bool:
        """Check if file has AVI header"""
        # AVI files start with 'RIFF' and have 'AVI ' at bytes 8-12
        return len(header) >= 12 and header[:4] == b'RIFF' and header[8:12] == b'AVI '
    
    def _check_mkv_header(self, header: bytes) -> bool:
        """Check if file has MKV/WebM header"""
        # MKV files start with EBML header (0x1A45DFA3)
        return len(header) >= 4 and header[:4] == b'\x1a\x45\xdf\xa3'
    
    def _validate_mp4_file(self, f, file_size: int) -> Tuple[bool, str]:
        """Perform additional validation for MP4 files"""
        try:
            # Check if file has proper MP4 structure
            # MP4 files should have 'moov' atom (movie header)
            f.seek(0)
            
            # For small files, read everything
            if file_size < 1024 * 1024:
                data = f.read()
                if b'moov' not in data:
                    return False, "Missing moov atom - file may be incomplete"
            else:
                # For large files, check beginning and end
                data = f.read(1024 * 1024)  # Read first 1MB
                
                if b'moov' not in data:
                    # Check end of file for moov atom (some MP4s have it at the end)
                    f.seek(-min(file_size, 1024 * 1024), os.SEEK_END)
                    data = f.read()
                    if b'moov' not in data:
                        return False, "Missing moov atom - file may be incomplete"
            
            return True, "Valid MP4 file"
            
        except Exception as e:
            return False, f"MP4 validation error: {str(e)}"
    
    def close(self):
        """Close the session"""
        self.session.close()