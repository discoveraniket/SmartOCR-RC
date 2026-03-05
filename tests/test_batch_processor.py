import pytest
import os
from unittest.mock import MagicMock, patch
from src.core.batch_processor import BatchProcessor

@pytest.fixture
def mock_coordinator():
    return MagicMock()

def test_discover_files(tmp_path):
    """Test discovering image files in a directory."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "img1.jpg").write_text("dummy")
    (data_dir / "img2.png").write_text("dummy")
    (data_dir / "doc.txt").write_text("dummy")
    
    sub_dir = data_dir / "subdir"
    sub_dir.mkdir()
    (sub_dir / "img3.bmp").write_text("dummy")
    
    processor = BatchProcessor(str(data_dir), "output")
    count = processor.discover_files()
    
    assert count == 3
    assert processor.queue.qsize() == 3

@patch('src.core.batch_processor.run_in_background')
def test_process_next_stops_when_empty(mock_run, mock_coordinator):
    """Test that it stops when the queue is empty."""
    completion_callback = MagicMock()
    processor = BatchProcessor("input", "output")
    processor.coordinator = mock_coordinator
    
    processor.process_next(MagicMock(), completion_callback)
    
    assert processor.is_running is False
    completion_callback.assert_called_once()
    mock_run.assert_not_called()

@patch('src.core.batch_processor.run_in_background')
def test_start_calls_discover_and_process(mock_run, tmp_path):
    """Test starting the batch process."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "img.jpg").write_text("data")
    
    processor = BatchProcessor(str(data_dir), "output")
    processor.start(MagicMock(), MagicMock())
    
    assert processor.total_files == 1
    assert processor.is_running is True
    mock_run.assert_called_once()
