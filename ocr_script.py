import os
import logging
from paddleocr import PaddleOCR
import config

logger = logging.getLogger(__name__)

class OcrProcessor:
    def __init__(self):
        """Initialize PaddleOCR with settings from config."""
        self.ocr = PaddleOCR(**config.OCR_SETTINGS)

    def extract_text(self, image_path: str) -> list:
        """
        Performs OCR on the given image and returns a list of extracted text lines.
        """
        if not os.path.exists(image_path):
            logger.error(f"Image not found: {image_path}")
            return []

        logger.info(f"Running OCR on {image_path}...")
        result = self.ocr.ocr(image_path, cls=True)
        
        extracted_text = []
        if result and result[0]:
            for line in result[0]:
                text = line[1][0]
                extracted_text.append(text)
        
        return extracted_text
