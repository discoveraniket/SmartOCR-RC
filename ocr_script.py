import os
import logging
from typing import List, Any
from paddleocr import PaddleOCR
import config

logger = logging.getLogger(__name__)

class OCRResultProcessor:
    """Handles the parsing and cleaning of raw OCR results."""
    
    @staticmethod
    def process_paddle_output(result: Any) -> List[str]:
        """Extracts plain text strings from PaddleOCR's nested list structure."""
        extracted_text = []
        if result and isinstance(result, list) and result[0]:
            for line in result[0]:
                # line format: [[coords], [text, confidence]]
                if len(line) > 1 and len(line[1]) > 0:
                    text = line[1][0]
                    extracted_text.append(str(text))
        return extracted_text

class OcrEngine:
    """Wrapper for the underlying OCR library (PaddleOCR)."""
    
    def __init__(self):
        """Initialize PaddleOCR with settings from config."""
        try:
            self.client = PaddleOCR(**config.OCR_SETTINGS)
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
