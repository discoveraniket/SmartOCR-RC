import pytest
from PIL import Image
from src.utils.image_processing import ImageProcessingService

def test_calculate_text_bounds_basic():
    """Test standard bounding box calculation with padding."""
    ocr_results = [
        {"box": [[10, 10], [100, 10], [100, 50], [10, 50]]},
        {"box": [[200, 200], [300, 200], [300, 250], [200, 250]]}
    ]
    # Expected: min_x=10, min_y=10, max_x=300, max_y=250
    # With padding 20: 10-20= -10(clamp to 0), 10-20= -10(0), 300+20=320, 250+20=270
    bounds = ImageProcessingService.calculate_text_bounds(ocr_results, padding=20)
    assert bounds == (0, 0, 320, 270)

def test_calculate_text_bounds_empty():
    """Ensure it handles empty OCR results gracefully."""
    assert ImageProcessingService.calculate_text_bounds([]) is None
    assert ImageProcessingService.calculate_text_bounds(None) is None

def test_crop_to_content_safety():
    """Test that cropping respects image boundaries."""
    img = Image.new('RGB', (100, 100))
    # Bounds larger than image
    bounds = (-50, -50, 200, 200)
    cropped = ImageProcessingService.crop_to_content(img, bounds)
    assert cropped.size == (100, 100)
    
    # Valid crop
    bounds_valid = (10, 10, 50, 50)
    cropped_valid = ImageProcessingService.crop_to_content(img, bounds_valid)
    assert cropped_valid.size == (40, 40)
