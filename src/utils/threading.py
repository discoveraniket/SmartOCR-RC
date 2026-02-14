import threading
import queue
import logging
from typing import Callable, Any

logger = logging.getLogger(__name__)

class WorkerThread(threading.Thread):
    """A generic worker thread for background tasks."""
    def __init__(self, task: Callable, *args, callback: Callable = None, **kwargs):
        super().__init__()
        self.task = task
        self.args = args
        self.kwargs = kwargs
        self.callback = callback
        self.daemon = True

    def run(self):
        try:
            result = self.task(*self.args, **self.kwargs)
            if self.callback:
                self.callback(result)
        except Exception as e:
            logger.error(f"Error in worker thread: {e}")

def run_in_background(task: Callable, *args, callback: Callable = None, **kwargs):
    """Runs a task in a background thread."""
    thread = WorkerThread(task, *args, callback=callback, **kwargs)
    thread.start()
    return thread
