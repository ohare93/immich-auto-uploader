import os
import time
import pytest
from unittest.mock import patch, MagicMock, call
from pathlib import Path

import sys
sys.path.append('src')

from file_watcher import FileInfo, ImmichFileHandler, FileWatcher
from config import Config


class TestFileInfo:
    """Test FileInfo class functionality"""
    
    def test_file_info_creation(self, test_directories):
        """Test FileInfo object creation with valid file"""
        file_info = FileInfo(str(test_directories['image1']))
        
        assert file_info.path == test_directories['image1']
        assert file_info.name == 'test.jpg'
        assert file_info.extension == 'jpg'
        assert file_info.size_bytes > 0
        assert file_info.modified_time > 0
    
    def test_file_info_nonexistent_file(self, test_directories):
        """Test FileInfo with nonexistent file"""
        nonexistent = test_directories['nonexistent'] / 'missing.jpg'
        file_info = FileInfo(str(nonexistent))
        
        assert file_info.path == nonexistent
        assert file_info.name == 'missing.jpg'
        assert file_info.extension == 'jpg'
        assert file_info.size_bytes == 0
        assert file_info.modified_time == 0
    
    def test_file_info_is_valid(self, mock_env, test_directories):
        """Test FileInfo validation logic"""
        env_vars = {
            **mock_env,
            'WATCH_DIRECTORIES': str(test_directories['watch1']),
            'ARCHIVE_DIRECTORY': str(test_directories['archive']),
            'MAX_FILE_SIZE_MB': '5'  # 5MB limit
        }
        
        with patch.dict(os.environ, env_vars):
            config = Config()
            
            # Valid image file
            file_info = FileInfo(str(test_directories['image1']))
            assert file_info.is_valid(config) is True
            
            # Large file exceeding size limit
            file_info = FileInfo(str(test_directories['video1']))  # 10MB file
            assert file_info.is_valid(config) is False
            
            # Unsupported file type
            file_info = FileInfo(str(test_directories['text_file']))
            assert file_info.is_valid(config) is False
            
            # File in archive directory
            file_info = FileInfo(str(test_directories['archived_file']))
            assert file_info.is_valid(config) is False
            
            # Nonexistent file
            nonexistent = test_directories['nonexistent'] / 'missing.jpg'
            file_info = FileInfo(str(nonexistent))
            assert file_info.is_valid(config) is False
    
    def test_file_info_string_representation(self, test_directories):
        """Test FileInfo string representation"""
        file_info = FileInfo(str(test_directories['image1']))
        file_str = str(file_info)
        
        assert 'FileInfo(' in file_str
        assert 'test.jpg' in file_str
        assert 'jpg' in file_str


class TestImmichFileHandler:
    """Test ImmichFileHandler functionality"""
    
    @pytest.fixture
    def mock_config(self, mock_env, test_directories):
        """Create a mock config for testing"""
        env_vars = {
            **mock_env,
            'WATCH_DIRECTORIES': str(test_directories['watch1']),
            'ARCHIVE_DIRECTORY': str(test_directories['archive']),
            'FILE_STABILITY_WAIT_SECONDS': '1',
            'FILE_STABILITY_CHECK_INTERVAL': '0.1'
        }
        
        with patch.dict(os.environ, env_vars):
            return Config()
    
    def test_handler_creation(self, mock_config):
        """Test handler creation"""
        callback = MagicMock()
        handler = ImmichFileHandler(mock_config, callback)
        
        assert handler.config == mock_config
        assert handler.on_file_ready == callback
        assert isinstance(handler.processing_files, set)
    
    def test_file_stability_check_stable_file(self, mock_config, test_directories):
        """Test file stability detection with stable file"""
        callback = MagicMock()
        handler = ImmichFileHandler(mock_config, callback)
        
        # Test with existing stable file
        result = handler._wait_for_file_stability(str(test_directories['image1']))
        assert result is True
    
    def test_file_stability_check_missing_file(self, mock_config, test_directories):
        """Test file stability with nonexistent file"""
        callback = MagicMock()
        handler = ImmichFileHandler(mock_config, callback)
        
        nonexistent = str(test_directories['nonexistent'] / 'missing.jpg')
        result = handler._wait_for_file_stability(nonexistent)
        assert result is False
    
    def test_file_stability_check_disappearing_file(self, mock_config, test_directories):
        """Test file stability when file disappears during check"""
        callback = MagicMock()
        handler = ImmichFileHandler(mock_config, callback)
        
        # Create a file that we'll delete during the test
        temp_file = test_directories['watch1'] / 'temp_file.jpg'
        temp_file.write_bytes(b'temporary content')
        
        # Mock time.sleep to delete file during stability check
        original_sleep = time.sleep
        def mock_sleep(duration):
            if temp_file.exists():
                temp_file.unlink()  # Delete file during sleep
            original_sleep(0.01)  # Short actual sleep
        
        with patch('time.sleep', side_effect=mock_sleep):
            result = handler._wait_for_file_stability(str(temp_file))
            # Should return True since file disappeared (likely processed)
            assert result is True
    
    @patch('time.sleep')
    def test_file_stability_check_growing_file(self, mock_sleep, mock_config, test_directories):
        """Test file stability with a growing file"""
        callback = MagicMock()
        handler = ImmichFileHandler(mock_config, callback)
        
        # Create a file and simulate it growing
        temp_file = test_directories['watch1'] / 'growing_file.jpg'
        temp_file.write_bytes(b'initial content')
        
        call_count = 0
        def mock_sleep_and_grow(duration):
            nonlocal call_count
            call_count += 1
            if call_count <= 3:  # Grow file for first few calls
                with open(temp_file, 'ab') as f:
                    f.write(b'more content')
            # After 3 calls, file stops growing and should stabilize
        
        mock_sleep.side_effect = mock_sleep_and_grow
        
        result = handler._wait_for_file_stability(str(temp_file))
        assert result is True
        assert mock_sleep.call_count >= 4  # Should wait for stability
    
    def test_handle_file_event_valid_file(self, mock_config, test_directories):
        """Test handling of valid file events"""
        callback = MagicMock()
        handler = ImmichFileHandler(mock_config, callback)
        
        # Mock the stability check to return immediately
        with patch.object(handler, '_wait_for_file_stability', return_value=True):
            handler._handle_file_event(str(test_directories['image1']))
            
            # Should call the callback with valid file
            callback.assert_called_once()
            file_info = callback.call_args[0][0]
            assert isinstance(file_info, FileInfo)
            assert file_info.name == 'test.jpg'
    
    def test_handle_file_event_invalid_file(self, mock_config, test_directories):
        """Test handling of invalid file events"""
        callback = MagicMock()
        handler = ImmichFileHandler(mock_config, callback)
        
        # Mock stability check to return True but file is invalid (text file)
        with patch.object(handler, '_wait_for_file_stability', return_value=True):
            handler._handle_file_event(str(test_directories['text_file']))
            
            # Should not call callback for invalid file
            callback.assert_not_called()
    
    def test_handle_file_event_unstable_file(self, mock_config, test_directories):
        """Test handling of unstable file events"""
        callback = MagicMock()
        handler = ImmichFileHandler(mock_config, callback)
        
        # Mock stability check to return False
        with patch.object(handler, '_wait_for_file_stability', return_value=False):
            handler._handle_file_event(str(test_directories['image1']))
            
            # Should not call callback for unstable file
            callback.assert_not_called()
    
    def test_duplicate_file_processing(self, mock_config, test_directories):
        """Test that the same file is not processed multiple times during stability check"""
        callback = MagicMock()
        handler = ImmichFileHandler(mock_config, callback)
        
        file_path = str(test_directories['image1'])
        
        # Mock stability check to simulate a long-running check
        def slow_stability_check(path):
            import time
            time.sleep(0.1)  # Simulate processing time
            return True
        
        with patch.object(handler, '_wait_for_file_stability', side_effect=slow_stability_check):
            # Start first call in a thread to simulate concurrent processing
            import threading
            
            # First call should process
            thread1 = threading.Thread(target=handler._handle_file_event, args=(file_path,))
            thread1.start()
            
            # Second call while first is processing should be ignored
            handler._handle_file_event(file_path)
            
            # Wait for first thread to complete
            thread1.join()
            
            # Should only call callback once (from the first thread)
            callback.assert_called_once()


class TestFileWatcher:
    """Test FileWatcher functionality"""
    
    @pytest.fixture
    def mock_config(self, mock_env, test_directories):
        """Create a mock config for testing"""
        env_vars = {
            **mock_env,
            'WATCH_DIRECTORIES': f"{test_directories['watch1']},{test_directories['watch2']}",
            'ARCHIVE_DIRECTORY': str(test_directories['archive'])
        }
        
        with patch.dict(os.environ, env_vars):
            return Config()
    
    def test_file_watcher_creation(self, mock_config):
        """Test FileWatcher creation"""
        callback = MagicMock()
        watcher = FileWatcher(mock_config, callback)
        
        assert watcher.config == mock_config
        assert watcher.on_file_ready == callback
        assert watcher.is_running is False
    
    @patch('file_watcher.Observer')
    def test_file_watcher_start(self, mock_observer_class, mock_config):
        """Test file watcher startup"""
        mock_observer = MagicMock()
        mock_observer_class.return_value = mock_observer
        
        callback = MagicMock()
        watcher = FileWatcher(mock_config, callback)
        
        watcher.start()
        
        assert watcher.is_running is True
        mock_observer.schedule.assert_called()
        mock_observer.start.assert_called_once()
    
    @patch('file_watcher.Observer')
    def test_file_watcher_stop(self, mock_observer_class, mock_config):
        """Test file watcher shutdown"""
        mock_observer = MagicMock()
        mock_observer_class.return_value = mock_observer
        
        callback = MagicMock()
        watcher = FileWatcher(mock_config, callback)
        
        watcher.start()
        watcher.stop()
        
        assert watcher.is_running is False
        mock_observer.stop.assert_called_once()
        mock_observer.join.assert_called_once()
    
    def test_file_watcher_no_valid_directories(self, mock_env, test_directories):
        """Test file watcher with no valid directories"""
        # Create config with nonexistent directory
        env_vars = {
            **mock_env,
            'WATCH_DIRECTORIES': str(test_directories['watch1']),  # This exists
            'ARCHIVE_DIRECTORY': str(test_directories['archive'])
        }
        
        with patch.dict(os.environ, env_vars):
            config = Config()
            callback = MagicMock()
            watcher = FileWatcher(config, callback)
            
            # Mock directories to appear missing at runtime
            with patch('os.path.exists', return_value=False):
                with pytest.raises(RuntimeError, match="No directories could be scheduled for watching"):
                    watcher.start()
    
    def test_file_watcher_initial_scan(self, mock_config, test_directories):
        """Test initial scan functionality"""
        callback = MagicMock()
        watcher = FileWatcher(mock_config, callback)
        
        # Mock observer to avoid actual file watching
        with patch('file_watcher.Observer'):
            watcher.start()
            
            # Should have called callback for existing valid files
            callback.assert_called()
            
            # Check that it found the valid image files
            call_args_list = [call.args[0] for call in callback.call_args_list]
            file_names = [file_info.name for file_info in call_args_list]
            
            assert 'test.jpg' in file_names
            assert 'large_photo.jpeg' in file_names
            assert 'video.mp4' in file_names
            # Should not include text file or archived file
            assert 'readme.txt' not in file_names
            assert 'already_archived.jpg' not in file_names
    
    def test_file_watcher_recursive_scanning(self, mock_env, test_directories):
        """Test recursive vs non-recursive scanning"""
        # Create subdirectory with a file
        subdir = test_directories['watch1'] / 'subdir'
        subdir.mkdir()
        sub_file = subdir / 'sub_image.jpg'
        sub_file.write_bytes(b'sub content')
        
        callback = MagicMock()
        
        # Test with recursive=True
        env_vars = {
            **mock_env,
            'WATCH_DIRECTORIES': str(test_directories['watch1']),
            'ARCHIVE_DIRECTORY': str(test_directories['archive']),
            'WATCH_RECURSIVE': 'true'
        }
        
        with patch.dict(os.environ, env_vars):
            config = Config()
            watcher = FileWatcher(config, callback)
            
            with patch('file_watcher.Observer'):
                watcher.start()
                
                # Should find file in subdirectory
                call_args_list = [call.args[0] for call in callback.call_args_list]
                file_names = [file_info.name for file_info in call_args_list]
                assert 'sub_image.jpg' in file_names
        
        callback.reset_mock()
        
        # Test with recursive=False
        env_vars['WATCH_RECURSIVE'] = 'false'
        
        with patch.dict(os.environ, env_vars):
            config = Config()
            watcher = FileWatcher(config, callback)
            
            with patch('file_watcher.Observer'):
                watcher.start()
                
                # Should not find file in subdirectory
                call_args_list = [call.args[0] for call in callback.call_args_list]
                file_names = [file_info.name for file_info in call_args_list]
                assert 'sub_image.jpg' not in file_names