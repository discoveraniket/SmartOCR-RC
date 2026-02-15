import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Any

logger = logging.getLogger(__name__)

# Single shared executor for background tasks
_executor = ThreadPoolExecutor(max_workers=4)

def run_in_background(task: Callable, *args, callback: Callable = None, **kwargs):
    """
    Runs a task in a background thread using a shared ThreadPoolExecutor.
    If a callback is provided, it is executed with the task's result.
    """
    def wrapper():
        try:
            result = task(*args, **kwargs)
            if callback:
                callback(result)
            return result
        except Exception as e:
            logger.error(f"Error in background task '{task.__name__}': {e}")
            if callback:
                callback(None)
            return None

    return _executor.submit(wrapper)
