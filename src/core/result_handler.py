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
