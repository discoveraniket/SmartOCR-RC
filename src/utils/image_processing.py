import logging
from pathlib import Path
from PIL import Image
from typing import List, Tuple, Optional, Union

logger = logging.getLogger(__name__)

class ImageProcessingService:
    """
    Modular service for image manipulation based on OCR data.
    """
    
    @staticmethod
    def calculate_text_bounds(ocr_results: List[dict], padding: int = 20) -> Optional[Tuple[int, int, int, int]]:
        """
        Calculates the collective bounding box for all detected text blocks.
        Returns (left, top, right, bottom)
        """
        if not ocr_results:
            return None

        # Flatten all points from all boxes to find min/max coordinates
        all_points = [point for item in ocr_results for point in item.get('box', [])]
        if not all_points:
            return None

        min_x = min(p[0] for p in all_points)
        min_y = min(p[1] for p in all_points)
        max_x = max(p[0] for p in all_points)
        max_y = max(p[1] for p in all_points)

        return (
            max(0, int(min_x) - padding),
            max(0, int(min_y) - padding),
            int(max_x) + padding,
            int(max_y) + padding
        )

    @staticmethod
    def crop_to_content(image: Image.Image, bounds: Tuple[int, int, int, int]) -> Image.Image:
        """Crops the PIL image to the specified bounds, ensuring they stay within image dimensions."""
        w, h = image.size
        safe_bounds = (
            max(0, bounds[0]),
            max(0, bounds[1]),
            min(w, bounds[2]),
            min(h, bounds[3])
        )
        return image.crop(safe_bounds)

    @staticmethod
    def save_image(image: Image.Image, path: Union[str, Path]) -> bool:
        """Saves the PIL image to the specified path, ensuring directories exist."""
        try:
            path = Path(path)
            path.parent.mkdir(parents=True, exist_ok=True)
            image.save(path, quality=95, subsampling=0)
            logger.info(f"Image saved successfully to {path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save image at {path}: {e}")
            return False
