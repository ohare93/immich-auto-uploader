import os
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing"""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


@pytest.fixture
def mock_env():
    """Mock environment variables for testing"""
    env_vars = {
        'IMMICH_API_URL': 'https://test.immich.com',
        'IMMICH_API_KEY': 'test_api_key_12345',
        'LOG_LEVEL': 'DEBUG'
    }
    
    with patch.dict(os.environ, env_vars, clear=False):
        yield env_vars


@pytest.fixture
def test_directories(temp_dir):
    """Create test directory structure"""
    directories = {
        'watch1': temp_dir / 'watch1',
        'watch2': temp_dir / 'watch2',
        'archive': temp_dir / 'archive',
        'archive_parent': temp_dir / 'archive_parent',
        'nonexistent': temp_dir / 'nonexistent'
    }
    
    # Create most directories
    for name, path in directories.items():
        if name != 'nonexistent':  # Leave this one missing
            path.mkdir(parents=True, exist_ok=True)
    
    # Create some test files
    test_files = {
        'image1': directories['watch1'] / 'test.jpg',
        'image2': directories['watch1'] / 'large_photo.jpeg',
        'video1': directories['watch2'] / 'video.mp4',
        'text_file': directories['watch1'] / 'readme.txt',
        'archived_file': directories['archive'] / 'already_archived.jpg'
    }
    
    for name, file_path in test_files.items():
        # Create files with different sizes
        if name == 'image2':
            content = b'X' * (2 * 1024 * 1024)  # 2MB file
        elif name == 'video1':
            content = b'Y' * (10 * 1024 * 1024)  # 10MB file
        else:
            content = b'test content'
        
        file_path.write_bytes(content)
    
    yield {**directories, **test_files}


@pytest.fixture
def mock_immich_response():
    """Mock successful Immich API response"""
    return {
        'id': 'test-asset-id-12345',
        'status': 'success'
    }