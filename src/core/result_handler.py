import os
import json
import logging
import csv
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class ResultDataHandler:
    """
    Handles the data logic for the Image Viewer.
    Manages loading results from CSV/JSON and saving user edits.
    """
    def __init__(self, results_csv: str, output_dir: str):
        self.results_csv = results_csv
        self.output_dir = output_dir
        self.results: List[Dict] = []
        self.current_index = -1
        self.load_results()
        self.load_last_index()

    def load_results(self):
        """Loads processed results from the CSV file."""
        if not os.path.exists(self.results_csv):
            logger.warning(f"Results CSV not found at {self.results_csv}")
            return

        try:
            with open(self.results_csv, mode='r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                self.results = [row for row in reader if any(row.values())] # Filter empty rows
            if self.results:
                self.current_index = 0
                logger.info(f"Loaded {len(self.results)} items from CSV.")
        except Exception as e:
            logger.error(f"Failed to load results: {e}")

    def _get_state_file(self):
        return os.path.join(self.output_dir, ".viewer_state")

    def save_last_index(self):
        """Saves the current index to a hidden state file in output dir."""
        try:
            with open(self._get_state_file(), "w") as f:
                json.dump({"last_index": self.current_index}, f)
        except:
            pass

    def load_last_index(self):
        """Loads the last index if the state file exists."""
        state_file = self._get_state_file()
        if os.path.exists(state_file):
            try:
                with open(state_file, "r") as f:
                    state = json.load(f)
                    idx = state.get("last_index", 0)
                    if 0 <= idx < len(self.results):
                        self.current_index = idx
            except:
                pass

    def get_current_item(self) -> Optional[Dict]:
        if 0 <= self.current_index < len(self.results):
            return self.results[self.current_index]
        return None

    def get_image_path(self, item: Dict) -> Optional[str]:
        image_name = item.get('processed_image_name', '').strip()
        if not image_name:
            logger.warning("No image name in item")
            return None
        full_path = os.path.join(self.output_dir, image_name)
        logger.debug(f"Resolved image path: {full_path}")
        return full_path

    def next_item(self) -> bool:
        if self.current_index < len(self.results) - 1:
            self.current_index += 1
            return True
        return False

    def prev_item(self) -> bool:
        if self.current_index > 0:
            self.current_index -= 1
            return True
        return False

    def save_edit(self, index: int, updated_data: Dict):
        """Updates the local result and saves back to CSV."""
        if 0 <= index < len(self.results):
            self.results[index].update(updated_data)
            self._write_all_to_csv()
            return True
        return False

    def rename_item_files(self, index: int, new_category: str, new_id: str) -> Optional[str]:
        """Renames the image and log files on disk and returns the new filename."""
        if not (0 <= index < len(self.results)):
            return None
            
        item = self.results[index]
        old_name = item.get('processed_image_name', '').strip()
        if not old_name:
            return None
            
        ext = os.path.splitext(old_name)[1]
        new_name = f"{new_category}_{new_id}{ext}"
        
        if old_name == new_name:
            return old_name
            
        try:
            # 1. Rename Image
            old_img_path = os.path.join(self.output_dir, old_name)
            new_img_path = os.path.join(self.output_dir, new_name)
            
            if os.path.exists(old_img_path):
                # Ensure we don't overwrite an existing file unless it's the same
                if os.path.exists(new_img_path) and old_img_path != new_img_path:
                    logger.warning(f"Destination file already exists: {new_name}")
                else:
                    os.rename(old_img_path, new_img_path)
            
            # 2. Rename Log
            old_base = os.path.splitext(old_name)[0]
            new_base = f"{new_category}_{new_id}"
            old_log_path = os.path.join(self.output_dir, "logs", f"{old_base}.txt")
            new_log_path = os.path.join(self.output_dir, "logs", f"{new_base}.txt")
            
            if os.path.exists(old_log_path):
                if os.path.exists(new_log_path) and old_log_path != new_log_path:
                    pass
                else:
                    os.rename(old_log_path, new_log_path)
            
            # 3. Update internal name
            item['processed_image_name'] = new_name
            self._write_all_to_csv()
            return new_name
            
        except Exception as e:
            logger.error(f"Failed to rename files: {e}")
            return None

    def delete_item(self, index: int) -> bool:
        """Removes an item from the list and updates the CSV."""
        if 0 <= index < len(self.results):
            self.results.pop(index)
            # Adjust current_index if we deleted the last item
            if self.current_index >= len(self.results):
                self.current_index = len(self.results) - 1
            
            self._write_all_to_csv()
            return True
        return False

    def _write_all_to_csv(self):
        """Rewrites the entire CSV with updated data."""
        if not self.results:
            return
        
        try:
            fieldnames = self.results[0].keys()
            with open(self.results_csv, mode='w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(self.results)
        except Exception as e:
            logger.error(f"Failed to save CSV: {e}")
