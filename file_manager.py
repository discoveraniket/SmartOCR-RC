import logging
import csv
import os
import shutil

logger = logging.getLogger(__name__)

def save_to_file(text: str, output_path: str):
    """Saves the text to a file (overwrites)."""
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(text)
        logger.info(f"File saved successfully to {output_path}")
    except Exception as e:
        logger.error(f"Failed to save file {output_path}: {e}")

def append_llm_result(output_path: str, result: dict):
    """Appends LLM results (reasoning and answer) to the file."""
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "a", encoding="utf-8") as f:
            f.write("\n" + "="*30 + "\n")
            f.write("LLM DATA CLEANING RESULT\n")
            f.write("="*30 + "\n")
            if result.get('thinking'):
                f.write(f"REASONING:{result['thinking']}\n")
            f.write(f"FINAL ANSWER:{result['answer']}\n")
        logger.info(f"LLM results appended to {output_path}")
    except Exception as e:
        logger.error(f"Failed to append LLM results to {output_path}: {e}")

def save_to_csv(data: dict, csv_path: str):
    """Saves/Appends a dictionary of data to a CSV file."""
    try:
        os.makedirs(os.path.dirname(csv_path), exist_ok=True)
        file_exists = os.path.isfile(csv_path)
        fieldnames = list(data.keys())
        with open(csv_path, 'a', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            writer.writerow(data)
        logger.info(f"Data saved to CSV: {csv_path}")
    except Exception as e:
        logger.error(f"Failed to save data to CSV {csv_path}: {e}")

def copy_and_rename_image(old_path: str, destination_dir: str, new_name: str):
    """Copies the image to a new directory with a new name."""
    try:
        os.makedirs(destination_dir, exist_ok=True)
        new_path = os.path.join(destination_dir, new_name)
        
        shutil.copy2(old_path, new_path)
        logger.info(f"Image copied from {old_path} to {new_path}")
        return new_path
    except Exception as e:
        logger.error(f"Failed to copy image {old_path}: {e}")
        return old_path
