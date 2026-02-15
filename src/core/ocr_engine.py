import logging
from pathlib import Path
from typing import List, Any, Dict, Optional, Union
from paddleocr import PaddleOCR
from src.utils import config

logger = logging.getLogger(__name__)

class OCRResultProcessor:
    """Handles the parsing, reordering, and cleaning of raw OCR results."""
    
    @staticmethod
    def process_paddle_output(result: Any) -> List[Dict[str, Any]]:
        """Extracts text with spatial metadata (coordinates and confidence)."""
        if not result or not isinstance(result, list) or not result[0]:
            return []
            
        extracted_data = []
        for line in result[0]:
            if len(line) > 1:
                box = line[0]  # [[x1, y1], [x2, y1], [x2, y2], [x1, y2]]
                text, conf = line[1]
                extracted_data.append({
                    "text": text, 
                    "confidence": conf,
                    "x": box[0][0], 
                    "y": box[0][1],
                    "box": box
                })

        # Sort primarily by Y (with 15px line grouping to handle slight tilts) 
        # and secondarily by X (left-to-right)
        extracted_data.sort(key=lambda r: (r['y'] // 15, r['x']))
        return extracted_data

class OcrEngine:
    """Wrapper for the underlying OCR library (PaddleOCR)."""
    
    def __init__(self, **overrides):
        """Initialize PaddleOCR with settings from config, allowing overrides."""
        try:
            settings = config.OCR_SETTINGS.copy()
            settings.update(overrides)
            # Filter settings to only include what PaddleOCR expects if needed
            self.client = PaddleOCR(**settings)
        except Exception as e:
            logger.error(f"Failed to initialize PaddleOCR engine: {e}")
            raise

    def run_inference(self, image: Union[str, Path, Any]) -> Any:
        """Executes the raw OCR process on an image file or numpy array."""
        # Convert Path to str as PaddleOCR might expect string
        img_input = str(image) if isinstance(image, Path) else image
        return self.client.ocr(img_input, cls=True)

class OcrProcessor:
    """Facade for OCR operations."""
    
    def __init__(self):
        self.engine = OcrEngine()
        self.processor = OCRResultProcessor()

    def extract_text(self, image_path: Union[str, Path]) -> List[Dict[str, Any]]:
        """
        Performs OCR on the given image and returns a list of processed results.
        """
        if not self._validate_image(image_path):
            return []

        try:
            logger.info(f"Running OCR on {image_path}...")
            raw_result = self.engine.run_inference(image_path)
            return self.processor.process_paddle_output(raw_result)
        except Exception as e:
            logger.error(f"OCR execution failed for {image_path}: {e}")
            return []

    def _validate_image(self, image_path: Union[str, Path]) -> bool:
        """Checks if the image path is valid and accessible."""
        path = Path(image_path)
        if not path.exists():
            logger.error(f"Image not found: {path}")
            return False
        if not path.is_file():
            logger.error(f"Path is not a file: {path}")
            return False
        return True
