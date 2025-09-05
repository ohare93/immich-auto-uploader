import os
import pytest
from unittest.mock import patch, MagicMock, Mock
import requests

import sys
sys.path.append('src')

from immich_client import ImmichClient, ImmichUploadResult
from file_watcher import FileInfo
from config import Config


class TestImmichUploadResult:
    """Test ImmichUploadResult functionality"""
    
    def test_success_result(self):
        """Test successful upload result"""
        result = ImmichUploadResult(success=True, asset_id='test-123', message='Upload successful')
        
        assert result.success is True
        assert result.asset_id == 'test-123'
        assert result.message == 'Upload successful'
    
    def test_failure_result(self):
        """Test failed upload result"""
        result = ImmichUploadResult(success=False, message='Connection failed')
        
        assert result.success is False
        assert result.asset_id is None
        assert result.message == 'Connection failed'


class TestImmichClient:
    """Test ImmichClient functionality"""
    
    @pytest.fixture
    def mock_config(self, mock_env, test_directories):
        """Create a mock config for testing"""
        env_vars = {
            **mock_env,
            'WATCH_DIRECTORIES': str(test_directories['watch1']),
            'ARCHIVE_DIRECTORY': str(test_directories['archive']),
            'VERIFY_VIDEO_INTEGRITY': 'false'  # Default to false for most tests
        }
        
        with patch.dict(os.environ, env_vars):
            return Config()
    
    def test_client_initialization(self, mock_config):
        """Test ImmichClient initialization"""
        client = ImmichClient(mock_config)
        
        assert client.config == mock_config
        assert client.session is not None
        assert client.session.headers['x-api-key'] == mock_config.immich_api_key
    
    def test_get_content_type(self, mock_config):
        """Test MIME type detection"""
        client = ImmichClient(mock_config)
        
        # Test image types
        assert client._get_content_type('jpg') == 'image/jpeg'
        assert client._get_content_type('jpeg') == 'image/jpeg'
        assert client._get_content_type('png') == 'image/png'
        assert client._get_content_type('gif') == 'image/gif'
        assert client._get_content_type('bmp') == 'image/bmp'
        assert client._get_content_type('tiff') == 'image/tiff'
        assert client._get_content_type('webp') == 'image/webp'
        
        # Test video types
        assert client._get_content_type('mp4') == 'video/mp4'
        assert client._get_content_type('mov') == 'video/quicktime'
        assert client._get_content_type('avi') == 'video/x-msvideo'
        assert client._get_content_type('mkv') == 'video/x-matroska'
        assert client._get_content_type('wmv') == 'video/x-ms-wmv'
        assert client._get_content_type('flv') == 'video/x-flv'
        assert client._get_content_type('m4v') == 'video/x-m4v'
        assert client._get_content_type('3gp') == 'video/3gpp'
        
        # Test case insensitive
        assert client._get_content_type('JPG') == 'image/jpeg'
        assert client._get_content_type('MP4') == 'video/mp4'
        
        # Test unknown type
        assert client._get_content_type('unknown') == 'application/octet-stream'
        assert client._get_content_type('') == 'application/octet-stream'
    
    @patch('requests.Session.get')
    def test_connection_success(self, mock_get, mock_config):
        """Test successful connection test"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        client = ImmichClient(mock_config)
        result = client.test_connection()
        
        assert result is True
        mock_get.assert_called_once_with(f"{mock_config.immich_api_url}/api/server/ping", timeout=10)
    
    @patch('requests.Session.get')
    def test_connection_failure_http_error(self, mock_get, mock_config):
        """Test connection failure with HTTP error"""
        mock_get.side_effect = requests.RequestException("Connection failed")
        
        client = ImmichClient(mock_config)
        result = client.test_connection()
        
        assert result is False
    
    @patch('requests.Session.get')
    def test_connection_failure_status_code(self, mock_get, mock_config):
        """Test connection failure with bad status code"""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response
        
        client = ImmichClient(mock_config)
        result = client.test_connection()
        
        assert result is False
    
    def test_generate_device_asset_id(self, mock_config, test_directories):
        """Test device asset ID generation"""
        client = ImmichClient(mock_config)
        file_info = FileInfo(str(test_directories['image1']))
        
        device_asset_id = client._generate_device_asset_id(file_info)
        
        # Should be a hex string (MD5 hash)
        assert isinstance(device_asset_id, str)
        assert len(device_asset_id) == 32  # MD5 hex length
        
        # Should be deterministic - same input gives same output
        device_asset_id2 = client._generate_device_asset_id(file_info)
        assert device_asset_id == device_asset_id2
    
    @patch('requests.Session.post')
    def test_upload_asset_success(self, mock_post, mock_config, test_directories):
        """Test successful asset upload"""
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {'id': 'test-asset-123'}
        mock_post.return_value = mock_response
        
        client = ImmichClient(mock_config)
        file_info = FileInfo(str(test_directories['image1']))
        
        result = client.upload_asset(file_info)
        
        assert result.success is True
        assert result.asset_id == 'test-asset-123'
        assert 'upload successful' in result.message.lower()
        
        # Verify request was made correctly
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == f"{mock_config.immich_api_url}/api/assets"
    
    @patch('requests.Session.post')
    def test_upload_asset_http_error(self, mock_post, mock_config, test_directories):
        """Test upload with HTTP error"""
        mock_post.side_effect = requests.RequestException("Network error")
        
        client = ImmichClient(mock_config)
        file_info = FileInfo(str(test_directories['image1']))
        
        result = client.upload_asset(file_info)
        
        assert result.success is False
        assert result.asset_id is None
        assert 'network error' in result.message.lower()
    
    @patch('requests.Session.post')
    def test_upload_asset_bad_status(self, mock_post, mock_config, test_directories):
        """Test upload with bad HTTP status"""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = 'Bad request'
        mock_post.return_value = mock_response
        
        client = ImmichClient(mock_config)
        file_info = FileInfo(str(test_directories['image1']))
        
        result = client.upload_asset(file_info)
        
        assert result.success is False
        assert result.asset_id is None
        assert 'bad request' in result.message.lower()
    
    @patch('requests.Session.post')
    def test_upload_asset_json_error(self, mock_post, mock_config, test_directories):
        """Test upload with JSON parsing error"""
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_response.text = 'Invalid response'
        mock_post.return_value = mock_response
        
        client = ImmichClient(mock_config)
        file_info = FileInfo(str(test_directories['image1']))
        
        result = client.upload_asset(file_info)
        
        # With status 201, it should succeed even with JSON parsing error
        assert result.success is True
        assert result.asset_id is None  # No asset ID due to JSON parsing failure
        assert 'upload successful' in result.message.lower()
    
    @patch('requests.Session.post')
    def test_upload_with_network_error(self, mock_post, mock_config, test_directories):
        """Test upload with network error"""
        mock_post.side_effect = requests.RequestException("Network error")
        
        client = ImmichClient(mock_config)
        file_info = FileInfo(str(test_directories['image1']))
        
        result = client.upload_asset(file_info)
        
        # Should fail with network error
        assert result.success is False
        assert result.asset_id is None
        assert 'network error' in result.message.lower()
    
    def test_client_close(self, mock_config):
        """Test client cleanup"""
        client = ImmichClient(mock_config)
        
        # Mock session to verify close is called
        client.session = MagicMock()
        
        client.close()
        
        client.session.close.assert_called_once()
    
    def test_upload_nonexistent_file(self, mock_config, test_directories):
        """Test uploading a nonexistent file"""
        client = ImmichClient(mock_config)
        nonexistent_file = test_directories['nonexistent'] / 'missing.jpg'
        file_info = FileInfo(str(nonexistent_file))
        
        result = client.upload_asset(file_info)
        
        assert result.success is False
        assert result.asset_id is None
        assert 'file is not valid for upload' in result.message.lower()
    
    @patch('requests.Session.post')
    def test_upload_large_file_timeout(self, mock_post, mock_config, test_directories):
        """Test upload timeout handling for large files"""
        mock_post.side_effect = requests.Timeout("Request timed out")
        
        client = ImmichClient(mock_config)
        file_info = FileInfo(str(test_directories['video1']))  # Large file
        
        result = client.upload_asset(file_info)
        
        assert result.success is False
        assert result.asset_id is None
        assert 'timeout' in result.message.lower() or 'timed out' in result.message.lower()
    
    def test_device_id_consistency(self, mock_config, test_directories):
        """Test that device ID is consistent across uploads"""
        client1 = ImmichClient(mock_config)
        client2 = ImmichClient(mock_config)
        
        # Device ID should be the same for all clients
        assert client1.device_id == client2.device_id
        assert client1.device_id == "immich-auto-uploader"
    
    def test_is_video_file(self, mock_config):
        """Test video file detection by extension"""
        client = ImmichClient(mock_config)
        
        # Video extensions
        for ext in ['mp4', 'mov', 'avi', 'mkv', 'wmv', 'flv', 'm4v', '3gp']:
            assert client._is_video_file(ext) is True
            assert client._is_video_file(ext.upper()) is True
        
        # Non-video extensions
        for ext in ['jpg', 'png', 'gif', 'txt', 'pdf']:
            assert client._is_video_file(ext) is False
    
    def test_validate_video_file_with_valid_mp4(self, mock_config, test_directories):
        """Test video validation with a valid MP4 file"""
        client = ImmichClient(mock_config)
        
        # Create a minimal valid MP4 file
        mp4_file = test_directories['watch1'] / 'test_video.mp4'
        # MP4 header: ftyp box with 'mp42' brand
        mp4_header = b'\x00\x00\x00\x20ftypisom\x00\x00\x02\x00isomiso2mp41'
        # Add a simple moov atom
        moov_atom = b'\x00\x00\x00\x08moov'
        mp4_file.write_bytes(mp4_header + moov_atom + b'\x00' * 1000)
        
        is_valid, msg = client._validate_video_file(mp4_file)
        assert is_valid is True
        assert 'Valid MP4' in msg
    
    def test_validate_video_file_with_incomplete_mp4(self, mock_config, test_directories):
        """Test video validation with incomplete MP4 (missing moov atom)"""
        client = ImmichClient(mock_config)
        
        # Create an MP4 without moov atom (incomplete download)
        mp4_file = test_directories['watch1'] / 'incomplete_video.mp4'
        # MP4 header without moov
        mp4_header = b'\x00\x00\x00\x20ftypisom\x00\x00\x02\x00isomiso2mp41'
        mp4_file.write_bytes(mp4_header + b'\x00' * 1000)
        
        is_valid, msg = client._validate_video_file(mp4_file)
        assert is_valid is False
        assert 'Missing moov atom' in msg
    
    def test_validate_video_file_too_small(self, mock_config, test_directories):
        """Test video validation with file too small"""
        client = ImmichClient(mock_config)
        
        # Create a very small file
        small_file = test_directories['watch1'] / 'tiny_video.mp4'
        small_file.write_bytes(b'tiny')
        
        is_valid, msg = client._validate_video_file(small_file)
        assert is_valid is False
        assert 'too small' in msg
    
    @patch('requests.Session.post')
    def test_upload_with_video_integrity_check_enabled(self, mock_post, mock_config, test_directories):
        """Test upload with video integrity checking enabled"""
        mock_config.verify_video_integrity = True
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {'id': 'test-asset-123'}
        mock_post.return_value = mock_response
        
        client = ImmichClient(mock_config)
        
        # Create a valid MP4 for testing
        mp4_file = test_directories['watch1'] / 'good_video.mp4'
        mp4_header = b'\x00\x00\x00\x20ftypisom\x00\x00\x02\x00isomiso2mp41'
        moov_atom = b'\x00\x00\x00\x08moov'
        mp4_file.write_bytes(mp4_header + moov_atom + b'\x00' * 10000)
        
        file_info = FileInfo(str(mp4_file))
        result = client.upload_asset(file_info)
        
        assert result.success is True
        assert mock_post.called
    
    @patch('requests.Session.post')
    def test_upload_with_video_integrity_check_fails(self, mock_post, mock_config, test_directories):
        """Test upload fails when video integrity check fails"""
        mock_config.verify_video_integrity = True
        
        client = ImmichClient(mock_config)
        
        # Create an incomplete MP4
        mp4_file = test_directories['watch1'] / 'bad_video.mp4'
        mp4_header = b'\x00\x00\x00\x20ftypisom\x00\x00\x02\x00isomiso2mp41'
        mp4_file.write_bytes(mp4_header + b'\x00' * 100)  # No moov atom
        
        file_info = FileInfo(str(mp4_file))
        result = client.upload_asset(file_info)
        
        assert result.success is False
        assert 'integrity check failed' in result.message
        assert not mock_post.called  # Should not attempt upload
    
    def test_unique_device_asset_ids(self, mock_config, test_directories):
        """Test that device asset IDs are unique for different files"""
        client = ImmichClient(mock_config)
        file_info1 = FileInfo(str(test_directories['image1']))
        file_info2 = FileInfo(str(test_directories['image2']))
        
        asset_id1 = client._generate_device_asset_id(file_info1)
        asset_id2 = client._generate_device_asset_id(file_info2)
        
        # Device asset IDs should be different for different files
        assert asset_id1 != asset_id2