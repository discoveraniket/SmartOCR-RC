import os
import time
import logging
from queue import Queue
from src.core.coordinator import PipelineCoordinator
from src.utils.threading import run_in_background

logger = logging.getLogger(__name__)

class BatchProcessor:
    """
    Handles the logic for batch processing multiple images.
    Separates the execution logic from the UI.
    """
    def __init__(self, input_dir, output_dir, recursive=True, auto_retry=True, post_action="None"):
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.recursive = recursive
        self.auto_retry = auto_retry
        self.post_action = post_action
        
        self.coordinator = PipelineCoordinator()
        self.queue = Queue()
        self.total_files = 0
        self.processed_count = 0
        self.error_count = 0
        self.start_time = 0
        
        self.is_running = False
        self.stop_requested = False

    def discover_files(self):
        """Finds all valid image files in the input directory."""
        image_extensions = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff')
        files = []
        
        if self.recursive:
            for root, _, filenames in os.walk(self.input_dir):
                for f in filenames:
                    if f.lower().endswith(image_extensions):
                        files.append(os.path.join(root, f))
        else:
            files = [os.path.join(self.input_dir, f) for f in os.listdir(self.input_dir) 
                     if f.lower().endswith(image_extensions)]
        
        self.total_files = len(files)
        for f in files:
            self.queue.put(f)
        return self.total_files

    def process_next(self, progress_callback, completion_callback):
        """Processes the next item in the queue recursively."""
        if self.queue.empty() or self.stop_requested:
            self.is_running = False
            completion_callback(self.get_stats())
            return

        image_path = self.queue.get()
        item_start = time.time()
        
        def on_step(metrics):
            # Pass intermediate metrics to UI
            progress_callback(self.get_stats(), current_file=os.path.basename(image_path), last_speeds=metrics)

        def on_item_finished(result):
            item_end = time.time()
            total_duration = round(item_end - item_start, 2)
            
            last_speeds = {"total": total_duration}
            
            if result and isinstance(result, dict) and "metrics" in result:
                self.processed_count += 1
                last_speeds.update(result["metrics"])
            elif result:
                self.processed_count += 1
            else:
                self.error_count += 1
            
            # Send final update for this item to UI
            progress_callback(self.get_stats(), current_file=os.path.basename(image_path), last_speeds=last_speeds)
            
            # Process next item
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
            completion_callback(self.get_stats())
            return

        def wrap_completion(stats):
            completion_callback(stats)
            self.perform_post_action()

        self.process_next(progress_callback, wrap_completion)

    def perform_post_action(self):
        """Executes the requested action after batch completion."""
        if self.post_action == "Shutdown":
            logger.info("Shutting down system...")
            os.system("shutdown /s /t 60") # 60 sec delay
        elif self.post_action == "Sleep":
            logger.info("Putting system to sleep...")
            os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")

    def stop(self):
        """Requests the process to stop."""
        self.stop_requested = True

    def get_stats(self):
        """Calculates current session statistics."""
        elapsed = time.time() - self.start_time
        avg_time = elapsed / self.processed_count if self.processed_count > 0 else 0
        remaining = self.total_files - (self.processed_count + self.error_count)
        eta = avg_time * remaining
        
        return {
            "total": self.total_files,
            "processed": self.processed_count,
            "errors": self.error_count,
            "remaining": remaining,
            "elapsed": elapsed,
            "eta": eta,
            "progress": (self.processed_count + self.error_count) / self.total_files if self.total_files > 0 else 0
        }
