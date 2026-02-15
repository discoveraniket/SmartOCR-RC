import pytest
import json
import csv
from pathlib import Path
from unittest.mock import MagicMock, patch
from src.core.output_manager import OutputManager

@pytest.fixture
def temp_output_dir(tmp_path):
    """Creates a temporary output directory for testing."""
    return tmp_path / "output"

def test_save_audit_log(temp_output_dir):
    manager = OutputManager(temp_output_dir)
    result = {
        "raw_text": "raw content",
        "cleaned_text": "cleaned content",
        "json_answer": '{"key": "value"}'
    }
    log_base = "test_log"
    
    manager.save_audit_log("input.jpg", result, log_base)
    
    log_file = temp_output_dir / "logs" / "test_log.txt"
    assert log_file.exists()
    content = log_file.read_text()
    assert "SOURCE IMAGE: input.jpg" in content
    assert "raw content" in content
    assert '{"key": "value"}' in content

def test_finalize_result_copy(temp_output_dir):
    manager = OutputManager(temp_output_dir)
    
    # Create a dummy source file
    src_file = temp_output_dir.parent / "input.png"
    src_file.write_text("dummy image data")
    
    json_string = '{"category": "PHH", "id": "1234567890"}'
    
    # Mock ImageFileHandler.copy_and_rename because it uses shutil.copy2
    with patch('src.utils.file_ops.ImageFileHandler.copy_and_rename') as mock_copy:
        # Simulate successful copy by returning the destination path
        dest_name = "PHH_1234567890.png"
        dest_path = temp_output_dir / dest_name
        mock_copy.return_value = str(dest_path)
        
        # We also need to mock CSV append to avoid file locking issues in rapid tests
        with patch('src.utils.file_ops.CSVFileHandler.append_row') as mock_csv:
            data = manager.finalize_result(src_file, json_string)
            
            assert data is not None
            assert data['category'] == "PHH"
            assert data['processed_image_name'] == dest_name
            mock_copy.assert_called_once()
            mock_csv.assert_called_once()

def test_finalize_result_with_crop(temp_output_dir):
    manager = OutputManager(temp_output_dir)
    src_file = "input.jpg"
    json_string = '{"category": "AAY", "id": "9988776655"}'
    
    mock_image = MagicMock()
    
    with patch('src.utils.image_processing.ImageProcessingService.save_image') as mock_save:
        with patch('src.utils.file_ops.CSVFileHandler.append_row'):
            data = manager.finalize_result(src_file, json_string, cropped_pil=mock_image)
            
            assert data is not None
            assert data['processed_image_name'] == "AAY_9988776655.jpg"
            mock_save.assert_called_once()
