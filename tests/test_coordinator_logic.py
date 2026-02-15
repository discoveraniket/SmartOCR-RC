import pytest
from unittest.mock import MagicMock, patch
from src.core.coordinator import PipelineCoordinator
from src.core.models import PipelineResult, ProcessingMetrics
from src.core.exceptions import OcrError, LlmError

@pytest.fixture
def mock_ocr():
    return MagicMock()

@pytest.fixture
def mock_llm():
    return MagicMock()

@pytest.fixture
def mock_output():
    return MagicMock()

def test_extract_data_success(mock_ocr, mock_llm, mock_output):
    # Setup mocks
    mock_ocr.run_inference.return_value = [[[[[0,0], [10,0], [10,10], [0,10]], ["TEXT", 0.99]]]]
    mock_llm.generate_response.side_effect = [
        {"answer": "cleaned text", "duration": 1.0}, # First pass
        {"answer": '{"category": "PHH", "id": "1234567890"}', "duration": 0.5} # Second pass
    ]
    
    coordinator = PipelineCoordinator(
        ocr_engine=mock_ocr, 
        det_engine=mock_ocr, 
        llm_engine=mock_llm, 
        output_manager=mock_output
    )
    
    result = coordinator.extract_data("dummy.jpg")
    
    assert isinstance(result, PipelineResult)
    assert result.data['category'] == "PHH"
    assert result.raw_text == "TEXT"
    assert result.metrics.ocr_det >= 0
    assert result.metrics.step1_duration == 1.0

def test_extract_data_ocr_failure(mock_ocr, mock_llm, mock_output):
    mock_ocr.run_inference.side_effect = OcrError("OCR Failed")
    
    coordinator = PipelineCoordinator(
        ocr_engine=mock_ocr, 
        det_engine=mock_ocr, 
        llm_engine=mock_llm, 
        output_manager=mock_output
    )
    
    # The coordinator catches AppError and returns None
    result = coordinator.extract_data("dummy.jpg")
    assert result is None

def test_extract_data_llm_failure(mock_ocr, mock_llm, mock_output):
    mock_ocr.run_inference.return_value = [[[[[0,0], [10,0], [10,10], [0,10]], ["TEXT", 0.99]]]]
    mock_llm.generate_response.side_effect = LlmError("LLM Failed")
    
    coordinator = PipelineCoordinator(
        ocr_engine=mock_ocr, 
        det_engine=mock_ocr, 
        llm_engine=mock_llm, 
        output_manager=mock_output
    )
    
    result = coordinator.extract_data("dummy.jpg")
    assert result is None
