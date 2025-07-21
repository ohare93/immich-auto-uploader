import os
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

import sys
sys.path.append('src')

from config import Config


class TestConfigValidation:
    """Test Config class validation and error handling"""
    
    def test_config_with_valid_env(self, mock_env, test_directories):
        """Test config initialization with valid environment"""
        env_vars = {
            **mock_env,
            'WATCH_DIRECTORIES': str(test_directories['watch1']),
            'ARCHIVE_DIRECTORY': str(test_directories['archive'])
            # Not setting WATCH_RECURSIVE to test default behavior
        }
        
        # Mock load_dotenv to prevent .env file from interfering with test
        with patch('config.load_dotenv'), patch.dict(os.environ, env_vars, clear=True):
            config = Config()
            assert config.immich_api_url == 'https://test.immich.com'
            assert config.immich_api_key == 'test_api_key_12345'
            assert config.log_level == 'DEBUG'
            assert config.watch_recursive is True  # default "true" should parse as True
    
    def test_missing_required_env_vars(self):
        """Test that missing required environment variables raise errors"""
        with patch('config.load_dotenv'), patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="Required environment variable IMMICH_API_URL is not set"):
                Config()
    
    def test_invalid_api_url(self, mock_env):
        """Test invalid API URL format"""
        with patch('config.load_dotenv'), patch.dict(os.environ, {**mock_env, 'IMMICH_API_URL': 'invalid-url'}):
            with pytest.raises(ValueError, match="IMMICH_API_URL must start with http:// or https://"):
                Config()
    
    def test_invalid_numeric_values(self, mock_env, test_directories):
        """Test invalid numeric configuration values"""
        base_env = {
            **mock_env,
            'WATCH_DIRECTORIES': str(test_directories['watch1']),
            'ARCHIVE_DIRECTORY': str(test_directories['archive'])
        }
        
        # Test invalid file stability wait
        with patch('config.load_dotenv'), patch.dict(os.environ, {**base_env, 'FILE_STABILITY_WAIT_SECONDS': '0'}):
            with pytest.raises(ValueError, match="FILE_STABILITY_WAIT_SECONDS must be at least 1"):
                Config()
        
        # Test invalid check interval
        with patch('config.load_dotenv'), patch.dict(os.environ, {**base_env, 'FILE_STABILITY_CHECK_INTERVAL': '0.05'}):
            with pytest.raises(ValueError, match="FILE_STABILITY_CHECK_INTERVAL must be at least 0.1"):
                Config()
        
        # Test invalid max file size
        with patch('config.load_dotenv'), patch.dict(os.environ, {**base_env, 'MAX_FILE_SIZE_MB': '0'}):
            with pytest.raises(ValueError, match="MAX_FILE_SIZE_MB must be at least 1"):
                Config()
    
    def test_nonexistent_watch_directory(self, mock_env, test_directories):
        """Test that nonexistent watch directories cause failure"""
        env_vars = {
            **mock_env,
            'WATCH_DIRECTORIES': str(test_directories['nonexistent']),
            'ARCHIVE_DIRECTORY': str(test_directories['archive'])
        }
        
        with patch.dict(os.environ, env_vars):
            with pytest.raises(ValueError, match="Watch directory does not exist"):
                Config()
    
    def test_watch_directory_not_directory(self, mock_env, test_directories):
        """Test that watch directory pointing to a file causes failure"""
        env_vars = {
            **mock_env,
            'WATCH_DIRECTORIES': str(test_directories['image1']),  # Point to file, not directory
            'ARCHIVE_DIRECTORY': str(test_directories['archive'])
        }
        
        with patch.dict(os.environ, env_vars):
            with pytest.raises(ValueError, match="Watch path is not a directory"):
                Config()
    
    def test_watch_directory_permissions(self, mock_env, test_directories):
        """Test watch directory permission checking"""
        # Create a directory and remove read permissions
        restricted_dir = test_directories['watch1'] / 'restricted'
        restricted_dir.mkdir()
        restricted_dir.chmod(0o000)  # No permissions
        
        env_vars = {
            **mock_env,
            'WATCH_DIRECTORIES': str(restricted_dir),
            'ARCHIVE_DIRECTORY': str(test_directories['archive'])
        }
        
        try:
            with patch.dict(os.environ, env_vars):
                with pytest.raises(ValueError, match="Watch directory is not readable"):
                    Config()
        finally:
            # Restore permissions for cleanup
            restricted_dir.chmod(0o755)
    
    def test_multiple_watch_directories(self, mock_env, test_directories):
        """Test configuration with multiple watch directories"""
        env_vars = {
            **mock_env,
            'WATCH_DIRECTORIES': f"{test_directories['watch1']},{test_directories['watch2']}",
            'ARCHIVE_DIRECTORY': str(test_directories['archive'])
        }
        
        with patch.dict(os.environ, env_vars):
            config = Config()
            assert len(config.watch_directories) == 2
            assert str(test_directories['watch1']) in config.watch_directories
            assert str(test_directories['watch2']) in config.watch_directories
    
    def test_watch_recursive_parsing(self, mock_env, test_directories):
        """Test parsing of WATCH_RECURSIVE environment variable"""
        base_env = {
            **mock_env,
            'WATCH_DIRECTORIES': str(test_directories['watch1']),
            'ARCHIVE_DIRECTORY': str(test_directories['archive'])
        }
        
        # Test true values
        for true_value in ['true', 'True', '1', 'yes', 'YES', 'on']:
            with patch.dict(os.environ, {**base_env, 'WATCH_RECURSIVE': true_value}):
                config = Config()
                assert config.watch_recursive is True
        
        # Test false values
        for false_value in ['false', 'False', '0', 'no', 'NO', 'off']:
            with patch.dict(os.environ, {**base_env, 'WATCH_RECURSIVE': false_value}):
                config = Config()
                assert config.watch_recursive is False
    
    def test_supported_extensions_parsing(self, mock_env, test_directories):
        """Test parsing of supported extensions"""
        env_vars = {
            **mock_env,
            'WATCH_DIRECTORIES': str(test_directories['watch1']),
            'ARCHIVE_DIRECTORY': str(test_directories['archive']),
            'SUPPORTED_EXTENSIONS': 'jpg,png,mp4'
        }
        
        with patch.dict(os.environ, env_vars):
            config = Config()
            assert config.supported_extensions == ['jpg', 'png', 'mp4']
    
    def test_is_supported_file(self, mock_env, test_directories):
        """Test file extension checking"""
        env_vars = {
            **mock_env,
            'WATCH_DIRECTORIES': str(test_directories['watch1']),
            'ARCHIVE_DIRECTORY': str(test_directories['archive'])
        }
        
        with patch.dict(os.environ, env_vars):
            config = Config()
            
            # Test supported files
            assert config.is_supported_file('photo.jpg') is True
            assert config.is_supported_file('image.JPEG') is True  # Case insensitive
            assert config.is_supported_file('video.mp4') is True
            
            # Test unsupported files
            assert config.is_supported_file('document.txt') is False
            assert config.is_supported_file('archive.zip') is False
            assert config.is_supported_file('no_extension') is False
    
    def test_is_in_archive_directory(self, mock_env, test_directories):
        """Test archive directory filtering"""
        env_vars = {
            **mock_env,
            'WATCH_DIRECTORIES': str(test_directories['watch1']),
            'ARCHIVE_DIRECTORY': str(test_directories['archive'])
        }
        
        with patch.dict(os.environ, env_vars):
            config = Config()
            
            # Test files in archive directory
            assert config.is_in_archive_directory(str(test_directories['archived_file'])) is True
            assert config.is_in_archive_directory(str(test_directories['archive'] / 'subfolder' / 'file.jpg')) is True
            
            # Test files outside archive directory
            assert config.is_in_archive_directory(str(test_directories['image1'])) is False
            assert config.is_in_archive_directory(str(test_directories['video1'])) is False
    
    def test_get_file_size_limit_bytes(self, mock_env, test_directories):
        """Test file size limit calculation"""
        env_vars = {
            **mock_env,
            'WATCH_DIRECTORIES': str(test_directories['watch1']),
            'ARCHIVE_DIRECTORY': str(test_directories['archive']),
            'MAX_FILE_SIZE_MB': '100'
        }
        
        with patch.dict(os.environ, env_vars):
            config = Config()
            expected_bytes = 100 * 1024 * 1024  # 100 MB in bytes
            assert config.get_file_size_limit_bytes() == expected_bytes
    
    def test_config_string_representation(self, mock_env, test_directories):
        """Test config string representation hides sensitive data"""
        env_vars = {
            **mock_env,
            'WATCH_DIRECTORIES': str(test_directories['watch1']),
            'ARCHIVE_DIRECTORY': str(test_directories['archive'])
        }
        
        with patch.dict(os.environ, env_vars):
            config = Config()
            config_str = str(config)
            
            # Should contain non-sensitive info
            assert 'https://test.immich.com' in config_str
            assert str(test_directories['watch1']) in config_str
            assert str(test_directories['archive']) in config_str
            
            # Should mask API key
            assert 'test_' in config_str  # First 5 chars
            assert '*' in config_str      # Masked part
            assert 'test_api_key_12345' not in config_str  # Full key should not appear