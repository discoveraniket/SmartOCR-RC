import time
import logging
from pathlib import Path
from queue import Queue
from src.core.coordinator import PipelineCoordinator
from src.utils.threading import run_in_background

logger = logging.getLogger(__name__)

class BatchProcessor:
    """
    Handles the logic for batch processing multiple images.
    """
    IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff'}

    def __init__(self, input_dir: str, output_dir: str, recursive: bool = True, auto_retry: bool = True, post_action: str = "None"):
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.recursive = recursive
        self.auto_retry = auto_retry
        self.post_action = post_action
        
        self.coordinator = PipelineCoordinator(output_dir=str(output_dir))
        self.queue = Queue()
        self.total_files = 0
        self.processed_count = 0
        self.error_count = 0
        self.start_time = 0.0
        
        self.is_running = False
        self.stop_requested = False

    def discover_files(self) -> int:
        """Finds all valid image files in the input directory."""
        pattern = "**/*" if self.recursive else "*"
        files = [
            p for p in self.input_dir.glob(pattern)
            if p.suffix.lower() in self.IMAGE_EXTENSIONS and p.is_file()
        ]
        
        self.total_files = len(files)
        logger.info(f"Discovered {self.total_files} files for processing in {self.input_dir}")
        for f in files:
            self.queue.put(str(f))
        return self.total_files

    def process_next(self, progress_callback, completion_callback):
        """Processes the next item in the queue."""
        if self.queue.empty() or self.stop_requested:
            self.is_running = False
            completion_callback(self.stats)
            return

        image_path = self.queue.get()
        item_start = time.time()
        
        def on_step(metrics):
            progress_callback(self.stats, current_file=Path(image_path).name, last_speeds=metrics)

        def on_item_finished(result):
            total_duration = round(time.time() - item_start, 2)
            last_speeds = {"total": total_duration}
            
            if result and isinstance(result, dict) and "metrics" in result:
                self.processed_count += 1
                last_speeds.update(result["metrics"])
            elif result:
                self.processed_count += 1
            else:
                self.error_count += 1
            
            progress_callback(self.stats, current_file=Path(image_path).name, last_speeds=last_speeds)
            self.process_next(progress_callback, completion_callback)

        run_in_background(self.coordinator.process_image, image_path, step_callback=on_step, callback=on_item_finished)

    def start(self, progress_callback, completion_callback):
        """Starts the batch process."""
        self.is_running = True
        self.stop_requested = False
        self.start_time = time.time()
        self.discover_files()
        
        if self.total_files == 0:
            self.is_running = False
            completion_callback(self.stats)
            return

        def wrap_completion(stats):
            completion_callback(stats)
            self.perform_post_action()

        self.process_next(progress_callback, wrap_completion)

    def perform_post_action(self):
        """Executes the requested action after batch completion."""
        import os
        if self.post_action == "Shutdown":
            logger.info("Shutting down system...")
            os.system("shutdown /s /t 60")
        elif self.post_action == "Sleep":
            logger.info("Putting system to sleep...")
            os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")

    def stop(self):
        """Requests the process to stop."""
        self.stop_requested = True

    @property
    def stats(self) -> dict:
        """Calculates current session statistics."""
        elapsed = time.time() - self.start_time
        processed = self.processed_count + self.error_count
        avg_time = elapsed / self.processed_count if self.processed_count > 0 else 0
        remaining = self.total_files - processed
        
        return {
            "total": self.total_files,
            "processed": self.processed_count,
            "errors": self.error_count,
            "remaining": remaining,
            "elapsed": elapsed,
            "eta": avg_time * remaining,
            "progress": processed / self.total_files if self.total_files > 0 else 0
        }
