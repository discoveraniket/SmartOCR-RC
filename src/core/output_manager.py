import logging
import json
from pathlib import Path
from PIL import Image
from typing import Dict, Any, Optional, Union
from src.utils.file_ops import TextFileHandler, CSVFileHandler, ImageFileHandler
from src.utils.image_processing import ImageProcessingService

logger = logging.getLogger(__name__)

class OutputManager:
    """Handles all persistence and output-related operations for the pipeline."""
    
    def __init__(self, output_dir: Union[str, Path]):
        self.output_dir = Path(output_dir)
        self.log_dir = self.output_dir / "logs"
        self.csv_path = self.output_dir / "results.csv"
        
        # Ensure directories exist
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def save_audit_log(self, image_path: str, result: Dict[str, Any], log_base: str):
        """Dumps the text data flow (OCR + LLM) to a text file for auditing."""
        try:
            log_path = self.log_dir / f"{log_base}.txt"
            
            content = [
                f"SOURCE IMAGE: {image_path}",
                f"FINAL NAME: {log_base}",
                "\n" + "="*50,
                "1. RAW OCR TEXT",
                "="*50,
                result.get('raw_text', ''),
                "\n" + "="*50,
                "2. LLM CLEANED TEXT",
                "="*50,
                result.get('cleaned_text', ''),
                "\n" + "="*50,
                "3. FINAL JSON OUTPUT",
                "="*50,
                result.get('json_answer', '')
            ]
            
            TextFileHandler.write(log_path, "\n".join(content))
        except Exception as e:
            logger.error(f"Failed to dump text flow: {e}")

    def finalize_result(self, original_image_path: Union[str, Path], json_string: str, cropped_pil: Optional[Image.Image] = None) -> Optional[Dict[str, Any]]:
        """Saves processed image, updates CSV, and returns final data dictionary."""
        try:
            data = json.loads(json_string)
            category = data.get('category') or 'UNKNOWN'
            id_val = data.get('id') or 'UNKNOWN'
            
            orig_path = Path(original_image_path)
            new_name = f"{category}_{id_val}{orig_path.suffix}"
            
            if cropped_pil:
                new_path = self.output_dir / new_name
                ImageProcessingService.save_image(cropped_pil, new_path)
                logger.info(f"Saved cropped image to {new_path}")
            else:
                # Returns the path as string
                new_path_str = ImageFileHandler.copy_and_rename(str(orig_path), str(self.output_dir), new_name)
                new_path = Path(new_path_str)
                logger.info(f"Copied original image to {new_path}")
            
            # Update data and persist to CSV
            data['processed_image_name'] = new_path.name
            CSVFileHandler.append_row(self.csv_path, data)
            
            logger.info(f"Successfully finalized: {data['processed_image_name']}")
            return data
        except Exception as e:
            logger.error(f"Finalization failed for {original_image_path}: {e}")
            return None
