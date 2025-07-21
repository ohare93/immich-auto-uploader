import os
import pytest
from unittest.mock import patch, MagicMock, Mock
from pathlib import Path

import sys
sys.path.append('src')

from file_processor import FileProcessor, ProcessingStats
from file_watcher import FileInfo
from config import Config


class TestProcessingStats:
    """Test ProcessingStats functionality"""
    
    def test_stats_initialization(self):
        """Test stats object initialization"""
        stats = ProcessingStats()
        
        assert stats.total_files == 0
        assert stats.successful_uploads == 0
        assert stats.failed_uploads == 0
        assert stats.skipped_files == 0
        assert stats.archived_files == 0
        assert stats.start_time > 0
    
    def test_stats_increment_methods(self):
        """Test stats increment methods"""
        stats = ProcessingStats()
        
        stats.increment_total()
        stats.increment_success()
        stats.increment_failed()
        stats.increment_skipped()
        stats.increment_archived()
        
        assert stats.total_files == 1
        assert stats.successful_uploads == 1
        assert stats.failed_uploads == 1
        assert stats.skipped_files == 1
        assert stats.archived_files == 1
    
    def test_stats_thread_safety(self):
        """Test that stats operations are thread-safe"""
        stats = ProcessingStats()
        
        # This test primarily ensures the lock exists and methods run
        # Full thread safety testing would require more complex setup
        import threading
        
        def increment_stats():
            for _ in range(10):
                stats.increment_total()
                stats.increment_success()
        
        threads = [threading.Thread(target=increment_stats) for _ in range(3)]
        
        for thread in threads:
            thread.start()
        
        for thread in threads:
            thread.join()
        
        assert stats.total_files == 30
        assert stats.successful_uploads == 30
    
    def test_stats_summary(self):
        """Test stats summary generation"""
        stats = ProcessingStats()
        stats.increment_total()
        stats.increment_success()
        stats.increment_archived()
        
        summary = stats.get_summary()
        
        assert 'Total: 1' in summary
        assert 'Success: 1' in summary
        assert 'Failed: 0' in summary
        assert 'Skipped: 0' in summary
        assert 'Archived: 1' in summary
        assert 'Runtime:' in summary


class TestFileProcessor:
    """Test FileProcessor functionality"""
    
    @pytest.fixture
    def mock_config(self, mock_env, test_directories):
        """Create a mock config for testing"""
        env_vars = {
            **mock_env,
            'WATCH_DIRECTORIES': str(test_directories['watch1']),
            'ARCHIVE_DIRECTORY': str(test_directories['archive'])
        }
        
        with patch.dict(os.environ, env_vars):
            return Config()
    
    @pytest.fixture
    def mock_immich_client(self):
        """Create a mock Immich client"""
        mock_client = MagicMock()
        mock_client.test_connection.return_value = True
        return mock_client
    
    def test_processor_initialization(self, mock_config):
        """Test FileProcessor initialization"""
        with patch('file_processor.ImmichClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client.test_connection.return_value = True
            mock_client_class.return_value = mock_client
            
            processor = FileProcessor(mock_config)
            
            assert processor.config == mock_config
            assert isinstance(processor.stats, ProcessingStats)
            assert processor.is_running is False
            assert len(processor.processed_files) == 0
    
    def test_ensure_archive_directory_exists(self, mock_config, test_directories):
        """Test archive directory validation when it exists"""
        with patch('file_processor.ImmichClient'):
            processor = FileProcessor(mock_config)
            
            # Should not raise any exceptions
            processor._ensure_archive_directory()
    
    def test_ensure_archive_directory_creation(self, mock_config, test_directories):
        """Test archive directory creation"""
        # Use a non-existent directory within an existing parent
        new_archive = test_directories['archive_parent'] / 'new_archive'
        mock_config.archive_directory = str(new_archive)
        mock_config.archive_directory_resolved = new_archive.resolve()
        
        with patch('file_processor.ImmichClient'):
            processor = FileProcessor(mock_config)
            processor._ensure_archive_directory()
            
            assert new_archive.exists()
            assert new_archive.is_dir()
    
    def test_ensure_archive_directory_missing_parent(self, mock_config, test_directories):
        """Test archive directory creation with missing parent"""
        # Use a directory with non-existent parent
        missing_parent = test_directories['nonexistent'] / 'parent' / 'archive'
        mock_config.archive_directory = str(missing_parent)
        mock_config.archive_directory_resolved = missing_parent.resolve()
        
        # Constructor calls _ensure_archive_directory, so we expect the error during initialization
        with patch('file_processor.ImmichClient'):
            with pytest.raises(RuntimeError, match="parent directory does not exist"):
                processor = FileProcessor(mock_config)
    
    def test_ensure_archive_directory_not_writable(self, mock_config, test_directories):
        """Test archive directory with non-writable parent"""
        # Create a directory and make it non-writable
        restricted_parent = test_directories['archive_parent'] / 'restricted'
        restricted_parent.mkdir()
        restricted_parent.chmod(0o444)  # Read-only
        
        new_archive = restricted_parent / 'archive'
        mock_config.archive_directory = str(new_archive)
        mock_config.archive_directory_resolved = new_archive.resolve()
        
        try:
            # Constructor calls _ensure_archive_directory, so we expect the error during initialization  
            with patch('file_processor.ImmichClient'):
                with pytest.raises(RuntimeError, match="Cannot setup archive directory"):
                    processor = FileProcessor(mock_config)
        finally:
            # Restore permissions for cleanup
            restricted_parent.chmod(0o755)
    
    def test_ensure_archive_directory_file_exists(self, mock_config, test_directories):
        """Test archive directory when a file exists at the path"""
        # Create a file where the archive directory should be
        file_path = test_directories['archive_parent'] / 'file_not_dir'
        file_path.write_text('not a directory')
        
        mock_config.archive_directory = str(file_path)
        mock_config.archive_directory_resolved = file_path.resolve()
        
        # Constructor calls _ensure_archive_directory, so we expect the error during initialization
        with patch('file_processor.ImmichClient'):
            with pytest.raises(RuntimeError, match="exists but is not a directory"):
                processor = FileProcessor(mock_config)
    
    def test_processor_start_connection_failure(self, mock_config):
        """Test processor start with connection failure"""
        with patch('file_processor.ImmichClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client.test_connection.return_value = False
            mock_client_class.return_value = mock_client
            
            processor = FileProcessor(mock_config)
            
            with pytest.raises(RuntimeError, match="Cannot connect to Immich server"):
                processor.start()
    
    def test_processor_start_success(self, mock_config):
        """Test successful processor start"""
        with patch('file_processor.ImmichClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client.test_connection.return_value = True
            mock_client_class.return_value = mock_client
            
            processor = FileProcessor(mock_config)
            processor.start()
            
            assert processor.is_running is True
            assert processor.worker_thread is not None
            assert processor.worker_thread.daemon is True
            
            # Clean up
            processor.stop()
    
    def test_processor_stop(self, mock_config):
        """Test processor stop"""
        with patch('file_processor.ImmichClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client.test_connection.return_value = True
            mock_client_class.return_value = mock_client
            
            processor = FileProcessor(mock_config)
            processor.start()
            processor.stop()
            
            assert processor.is_running is False
            mock_client.close.assert_called_once()
    
    def test_process_file_duplicate_detection(self, mock_config, test_directories):
        """Test duplicate file processing prevention"""
        with patch('file_processor.ImmichClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client.test_connection.return_value = True
            mock_client_class.return_value = mock_client
            
            processor = FileProcessor(mock_config)
            processor.start()  # Must start processor for it to process files
            
            file_info = FileInfo(str(test_directories['image1']))
            
            # First process should work
            processor.process_file(file_info)
            assert processor.stats.total_files == 1
            
            # Wait for file to be processed by worker thread
            import time
            time.sleep(0.1)  # Give worker time to process
            
            # Second process of same file should be skipped
            processor.process_file(file_info)
            assert processor.stats.total_files == 1  # Should not increment
            assert processor.stats.skipped_files == 1
            
            processor.stop()  # Clean up
    
    def test_process_file_not_running(self, mock_config, test_directories):
        """Test processing file when processor is not running"""
        with patch('file_processor.ImmichClient'):
            processor = FileProcessor(mock_config)
            file_info = FileInfo(str(test_directories['image1']))
            
            # Should not process when not running
            processor.process_file(file_info)
            assert processor.stats.total_files == 0
    
    def test_get_file_key(self, mock_config, test_directories):
        """Test file key generation for duplicate detection"""
        with patch('file_processor.ImmichClient'):
            processor = FileProcessor(mock_config)
            file_info = FileInfo(str(test_directories['image1']))
            
            key = processor._get_file_key(file_info)
            
            # Key should contain path, size, and modified time
            assert str(file_info.path) in key
            assert str(file_info.size_bytes) in key
            assert str(file_info.modified_time) in key
            assert key.count('_') == 2  # Two separators
    
    @patch('shutil.move')
    def test_archive_file_success(self, mock_move, mock_config, test_directories):
        """Test successful file archiving"""
        with patch('file_processor.ImmichClient'):
            processor = FileProcessor(mock_config)
            file_info = FileInfo(str(test_directories['image1']))
            
            result = processor._archive_file(file_info)
            
            assert result is True
            mock_move.assert_called_once()
            
            # Check move arguments
            call_args = mock_move.call_args[0]
            assert call_args[0] == str(test_directories['image1'])
            assert 'test.jpg' in call_args[1]
    
    @patch('shutil.move')
    def test_archive_file_name_conflict(self, mock_move, mock_config, test_directories):
        """Test file archiving with name conflict resolution"""
        # Create a file that already exists in archive
        existing_file = test_directories['archive'] / 'test.jpg'
        existing_file.write_bytes(b'existing content')
        
        with patch('file_processor.ImmichClient'):
            processor = FileProcessor(mock_config)
            file_info = FileInfo(str(test_directories['image1']))
            
            result = processor._archive_file(file_info)
            
            assert result is True
            mock_move.assert_called_once()
            
            # Should have renamed to avoid conflict
            call_args = mock_move.call_args[0]
            assert 'test_1.jpg' in call_args[1]
    
    @patch('shutil.move')
    def test_archive_file_failure(self, mock_move, mock_config, test_directories):
        """Test file archiving failure"""
        mock_move.side_effect = OSError("Permission denied")
        
        with patch('file_processor.ImmichClient'):
            processor = FileProcessor(mock_config)
            file_info = FileInfo(str(test_directories['image1']))
            
            result = processor._archive_file(file_info)
            
            assert result is False
    
    def test_processor_stats_access(self, mock_config):
        """Test accessing processor statistics"""
        with patch('file_processor.ImmichClient'):
            processor = FileProcessor(mock_config)
            
            stats = processor.get_stats()
            assert isinstance(stats, ProcessingStats)
            assert stats is processor.stats
    
    def test_processor_is_processing(self, mock_config):
        """Test processing status check"""
        with patch('file_processor.ImmichClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client.test_connection.return_value = True
            mock_client_class.return_value = mock_client
            
            processor = FileProcessor(mock_config)
            
            assert processor.is_processing() is False
            
            processor.start()
            assert processor.is_processing() is True
            
            processor.stop()
            assert processor.is_processing() is False