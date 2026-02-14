import pytest
from src.core.ocr_engine import OCRResultProcessor

def test_natural_reading_order_sorting():
    """
    Test that OCR results are sorted correctly: 
    Top-to-bottom (Y axis) and Left-to-right (X axis).
    """
    # Mock data: [Text, X, Y]
    # We purposefully put them out of order in the list
    mock_raw_data = [
        [ [[100, 50], [200, 50], [200, 70], [100, 70]], ("Line 2 Left", 0.99) ],
        [ [[10, 10], [50, 10], [50, 30], [10, 30]], ("Line 1", 0.99) ],
        [ [[210, 52], [300, 52], [300, 72], [210, 72]], ("Line 2 Right", 0.99) ],
    ]
    
    # Format it like PaddleOCR's raw nested list structure
    # Paddle returns: [ [ [box, (text, conf)], [box, (text, conf)] ] ]
    raw_paddle_output = [mock_raw_data]
    
    processor = OCRResultProcessor()
    processed = processor.process_paddle_output(raw_paddle_output)
    
    # Assertions
    assert len(processed) == 3
    assert processed[0]['text'] == "Line 1"
    assert processed[1]['text'] == "Line 2 Left"
    assert processed[2]['text'] == "Line 2 Right"

def test_line_grouping_tolerance():
    """
    Test that text with slightly different Y coordinates (within 15px)
    is treated as being on the same line and sorted left-to-right.
    """
    mock_raw_data = [
        [ [[200, 15], [300, 15], [300, 35], [200, 35]], ("Word 2", 0.95) ],
        [ [[10, 10], [100, 10], [100, 30], [10, 30]], ("Word 1", 0.95) ],
    ]
    
    raw_paddle_output = [mock_raw_data]
    processor = OCRResultProcessor()
    processed = processor.process_paddle_output(raw_paddle_output)
    
    # Even though Word 2 is at Y=15 and Word 1 is at Y=10, 
    # they should be grouped together (10//15 == 15//15 == 0)
    # and then sorted by X.
    assert processed[0]['text'] == "Word 1"
    assert processed[1]['text'] == "Word 2"

def test_empty_results():
    """Ensure the processor doesn't crash on empty input."""
    processor = OCRResultProcessor()
    assert processor.process_paddle_output(None) == []
    assert processor.process_paddle_output([]) == []
    assert processor.process_paddle_output([[]]) == []

def test_data_structure_integrity():
    """Verify all required keys are present in the output."""
    mock_raw_data = [[ [[0, 0], [10, 0], [10, 10], [0, 10]], ("Test", 0.85) ]]
    processor = OCRResultProcessor()
    result = processor.process_paddle_output([mock_raw_data])[0]
    
    assert "text" in result
    assert "confidence" in result
    assert "x" in result
    assert "y" in result
    assert "box" in result
    assert result['text'] == "Test"
    assert result['confidence'] == 0.85
