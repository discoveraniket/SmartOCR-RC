import logging
import sys
import argparse
import os
from src.core.coordinator import PipelineCoordinator
from src.ui.dashboard import Dashboard

from src.utils.logging_utils import setup_logging

logger = logging.getLogger(__name__)

from pathlib import Path
from src.core.batch_processor import BatchProcessor

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
    parser = argparse.ArgumentParser(description="RC-PaddleOCR Processor")
    parser.add_argument("--gui", action="store_true", help="Run in GUI mode")
    args = parser.parse_args()

    setup_logging()

    if args.gui:
        app = Dashboard()
        app.mainloop()
    else:
        run_cli()

if __name__ == "__main__":
    main()
