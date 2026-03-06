import logging
import sys
import argparse
import os
import functools
import urllib.parse

from src.core.coordinator import PipelineCoordinator
from src.ui.dashboard import Dashboard

from src.utils.logging_utils import setup_logging

logger = logging.getLogger(__name__)

from pathlib import Path
from src.core.batch_processor import BatchProcessor

_internet_access_granted = False

def check_download_permission(url, is_gui):
    global _internet_access_granted
    if _internet_access_granted:
        return True
        
    try:
        parsed = urllib.parse.urlparse(url)
        if parsed.hostname in ['localhost', '127.0.0.1', '::1', '0.0.0.0'] or not parsed.hostname:
            return True
    except:
        pass

    msg = f"The application is trying to download data from the internet:\n{url}\n\nDo you want to allow this and any future downloads?"
    
    if is_gui:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        res = messagebox.askyesno("Internet Download Permission", msg)
        root.destroy()
        _internet_access_granted = res
        return res
    else:
        print(f"\n[WARNING] {msg}")
        while True:
            try:
                resp = input("Allow download? (y/n): ").strip().lower()
            except EOFError:
                return False
            if resp in ['y', 'yes']:
                _internet_access_granted = True
                return True
            elif resp in ['n', 'no']:
                return False

def setup_download_interceptor(is_gui):
    # Patch requests
    try:
        import requests
        _orig_session_send = requests.Session.send
        @functools.wraps(_orig_session_send)
        def hooked_session_send(self, request, **kwargs):
            if not check_download_permission(request.url, is_gui):
                raise Exception(f"User denied download of {request.url}")
            return _orig_session_send(self, request, **kwargs)
        requests.Session.send = hooked_session_send
    except ImportError:
        pass

    # Patch urllib.request.urlretrieve
    try:
        import urllib.request
        _orig_urlretrieve = urllib.request.urlretrieve
        @functools.wraps(_orig_urlretrieve)
        def hooked_urlretrieve(url, filename=None, reporthook=None, data=None):
            if not check_download_permission(url, is_gui):
                raise Exception(f"User denied download of {url}")
            return _orig_urlretrieve(url, filename, reporthook, data)
        urllib.request.urlretrieve = hooked_urlretrieve
    except ImportError:
        pass
        
    # Patch urllib.request.urlopen
    try:
        import urllib.request
        _orig_urlopen = urllib.request.urlopen
        @functools.wraps(_orig_urlopen)
        def hooked_urlopen(url, data=None, timeout=object(), *args, **kwargs):
            url_str = url if isinstance(url, str) else url.full_url
            if not check_download_permission(url_str, is_gui):
                raise Exception(f"User denied download of {url_str}")
            if timeout is object():
                return _orig_urlopen(url, data, *args, **kwargs)
            return _orig_urlopen(url, data, timeout, *args, **kwargs)
        urllib.request.urlopen = hooked_urlopen
    except ImportError:
        pass

    # Patch ollama.pull
    try:
        import ollama
        _orig_pull = ollama.pull
        @functools.wraps(_orig_pull)
        def hooked_pull(model, *args, **kwargs):
            if not check_download_permission(f"ollama model: {model}", is_gui):
                raise Exception(f"User denied download of ollama model {model}")
            return _orig_pull(model, *args, **kwargs)
        ollama.pull = hooked_pull
    except ImportError:
        pass

def run_cli():
    """Runs the processing pipeline in command-line mode."""
    data_dir = Path("data")
    output_dir = Path("output")
    
    if not data_dir.exists():
        logger.error(f"Directory {data_dir} does not exist.")
        sys.exit(1)

    logger.info(f"Scanning {data_dir} for images...")
    processor = BatchProcessor(str(data_dir), str(output_dir))
    count = processor.discover_files()
    
    if count == 0:
        logger.info(f"No images found in {data_dir}")
        sys.exit(0)

    logger.info(f"Found {count} images. Starting processing...")
    
    # Simple synchronous wrapper for CLI
    processed = 0
    def on_progress(stats, current_file, last_speeds):
        nonlocal processed
        if stats['processed'] + stats['errors'] > processed:
            processed = stats['processed'] + stats['errors']
            logger.info(f"[{processed}/{count}] Processed: {current_file}")

    def on_complete(stats):
        logger.info("\n--- Batch Processing Complete ---")
        logger.info(f"Total: {stats['total']}")
        logger.info(f"Success: {stats['processed']}")
        logger.info(f"Errors: {stats['errors']}")
        logger.info(f"Elapsed: {stats['elapsed']:.2f}s")

    # For CLI, we might want a synchronous version, but since BatchProcessor 
    # is designed for async with callbacks, we'll wait for it.
    import threading
    completion_event = threading.Event()
    
    def sync_complete(stats):
        on_complete(stats)
        completion_event.set()

    processor.start(progress_callback=on_progress, completion_callback=sync_complete)
    completion_event.wait()

def main():
    parser = argparse.ArgumentParser(description="SmartOCR-RC Processor")
    parser.add_argument("--cli", action="store_true", help="Run in command-line mode")
    args = parser.parse_args()

    # GUI is the default behavior, CLI is the flag
    is_gui = not args.cli

    setup_download_interceptor(is_gui=is_gui)
    setup_logging()

    if args.cli:
        run_cli()
    else:
        app = Dashboard()
        app.mainloop()

if __name__ == "__main__":
    main()
 # python main.py
 # python main.py --cli
