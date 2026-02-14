import os
import logging
from typing import List, Any
from paddleocr import PaddleOCR
from src.utils import config
from typing import Dict, Any, List

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
                text = line[1][0]
                conf = line[1][1]
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
            self.client = PaddleOCR(**settings)
        except Exception as e:
            logger.error(f"Failed to initialize PaddleOCR engine: {e}")
            raise

    def run_inference(self, image_path: str) -> Any:
        """Executes the raw OCR process on an image file."""
        return self.client.ocr(image_path, cls=True)

class OcrProcessor:
    """Facade for OCR operations to maintain compatibility with main.py."""
    
    def __init__(self):
        self.engine = OcrEngine()
        self.processor = OCRResultProcessor()

    def extract_text(self, image_path: str) -> List[str]:
        """
        Performs OCR on the given image and returns a list of extracted text lines.
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

    def _validate_image(self, image_path: str) -> bool:
        """Checks if the image path is valid and accessible."""
        if not os.path.exists(image_path):
            logger.error(f"Image not found: {image_path}")
            return False
        if not os.path.isfile(image_path):
            logger.error(f"Path is not a file: {image_path}")
            return False
        return True
