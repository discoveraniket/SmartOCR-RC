import logging
import os
from PIL import Image
from typing import List, Tuple, Optional

logger = logging.getLogger(__name__)

class ImageProcessingService:
    """
    Modular service for image manipulation based on OCR data.
    Separates cropping logic from the UI for future use in batch processing.
    """
    
    @staticmethod
    def calculate_text_bounds(ocr_results: List[dict], padding: int = 20) -> Optional[Tuple[int, int, int, int]]:
        """
        Calculates the collective bounding box for all detected text blocks.
        Returns (left, top, right, bottom)
        """
        if not ocr_results:
            return None

        min_x = float('inf')
        min_y = float('inf')
        max_x = 0
        max_y = 0

        for item in ocr_results:
            # PaddleOCR box format: [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
            box = item.get('box', [])
            for point in box:
                x, y = point
                min_x = min(min_x, x)
                min_y = min(min_y, y)
                max_x = max(max_x, x)
                max_y = max(max_y, y)

        return (
            max(0, int(min_x) - padding),
            max(0, int(min_y) - padding),
            int(max_x) + padding,
            int(max_y) + padding
        )

    @staticmethod
    def crop_to_content(image: Image.Image, bounds: Tuple[int, int, int, int]) -> Image.Image:
        """Crops the PIL image to the specified bounds."""
        # Ensure bounds don't exceed image dimensions
        w, h = image.size
        safe_bounds = (
            max(0, bounds[0]),
            max(0, bounds[1]),
            min(w, bounds[2]),
            min(h, bounds[3])
        )
        return image.crop(safe_bounds)

    @staticmethod
    def save_image(image: Image.Image, path: str):
        """Saves the PIL image to the specified path."""
        try:
            # Ensure output directory exists
            os.makedirs(os.path.dirname(path), exist_ok=True)
            image.save(path, quality=95, subsampling=0)
            logger.info(f"Image saved successfully to {path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save image: {e}")
            return False
