import logging
import csv
import shutil
from pathlib import Path
from typing import Dict, Any, List, Union

logger = logging.getLogger(__name__)

class DirectoryUtility:
    """Handles directory-level operations."""
    @staticmethod
    def ensure_dir_for_file(file_path: Union[str, Path]) -> None:
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)

class LogFormatter:
    """Handles formatting of data for audit logs."""
    @staticmethod
    def format_ocr_spatial_data(ocr_results: List[Dict[str, Any]]) -> str:
        """Formats OCR results with coordinates and confidence for auditing."""
        header = "="*30 + "\nDETAILED OCR SPATIAL DATA\n" + "="*30
        cols = f"{'TEXT':<40} | {'CONF':<6} | {'X,Y COORDS':<15}\n" + "-"*70
        
        lines = [header, cols]
        for item in ocr_results:
            pos = f"{int(item['x'])},{int(item['y'])}"
            lines.append(f"{item['text']:<40} | {item['confidence']:.3f} | {pos}")
        return "\n".join(lines) + "\n"

    @staticmethod
    def format_llm_result(result: Dict[str, Any]) -> str:
        header = "\n" + "="*30 + "\nLLM DATA CLEANING RESULT\n" + "="*30
        content = []
        if result.get('thinking'):
            content.append(f"REASONING:{result['thinking']}")
        
        content.append(f"FINAL ANSWER:{result['answer']}\n")
        return header + "\n" + "\n".join(content)

class TextFileHandler:
    """Handles basic text file I/O."""
    @staticmethod
    def write(path: Union[str, Path], content: str) -> None:
        try:
            path = Path(path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            logger.info(f"File saved successfully to {path}")
        except IOError as e:
            logger.error(f"Failed to save file {path}: {e}")

    @staticmethod
    def append(path: Union[str, Path], content: str) -> None:
        try:
            path = Path(path)
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as f:
                f.write(content)
            logger.info(f"Content appended to {path}")
        except IOError as e:
            logger.error(f"Failed to append to file {path}: {e}")

class CSVFileHandler:
    """Handles CSV specific I/O."""
    @staticmethod
    def append_row(path: Union[str, Path], data: Dict[str, Any]) -> None:
        try:
            path = Path(path)
            path.parent.mkdir(parents=True, exist_ok=True)
            file_exists = path.is_file()
            fieldnames = list(data.keys())
            
            with path.open('a', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                if not file_exists:
                    writer.writeheader()
                writer.writerow(data)
            logger.info(f"Data saved to CSV: {path}")
        except (IOError, csv.Error) as e:
            logger.error(f"Failed to save data to CSV {path}: {e}")

class ImageFileHandler:
    """Handles image file operations."""
    @staticmethod
    def copy_and_rename(src_path: Union[str, Path], dst_dir: Union[str, Path], new_name: str) -> str:
        try:
            dst_dir = Path(dst_dir)
            dst_dir.mkdir(parents=True, exist_ok=True)
            dst_path = dst_dir / new_name
            shutil.copy2(src_path, dst_path)
            logger.info(f"Image copied from {src_path} to {dst_path}")
            return str(dst_path)
        except (IOError, shutil.Error) as e:
            logger.error(f"Failed to copy image {src_path}: {e}")
            return str(src_path)

# --- Public API Facade (Backward Compatibility) ---

def save_to_file(text: str, output_path: str):
    """Saves the text to a file (overwrites)."""
    TextFileHandler.write(output_path, text)

def append_llm_result(output_path: str, result: dict):
    """Appends formatted LLM results to the file."""
    formatted_content = LogFormatter.format_llm_result(result)
    TextFileHandler.append(output_path, formatted_content)

def save_to_csv(data: dict, csv_path: str):
    """Saves/Appends a dictionary of data to a CSV file."""
    CSVFileHandler.append_row(csv_path, data)

def copy_and_rename_image(old_path: str, destination_dir: str, new_name: str) -> str:
    """Copies the image to a new directory with a new name."""
    return ImageFileHandler.copy_and_rename(old_path, destination_dir, new_name)
