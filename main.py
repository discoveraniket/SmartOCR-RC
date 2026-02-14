import logging
import sys
import argparse
import os
from src.core.coordinator import PipelineCoordinator
from src.ui.dashboard import Dashboard

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        stream=sys.stdout,
        force=True
    )

def run_cli():
    DATA_DIR = "data"
    
    if not os.path.exists(DATA_DIR):
        print(f"Directory {DATA_DIR} does not exist.")
        sys.exit(1)

    image_extensions = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff')
    images = [f for f in os.listdir(DATA_DIR) if f.lower().endswith(image_extensions)]
    
    if not images:
        print(f"No images found in {DATA_DIR}")
        sys.exit(0)

    coordinator = PipelineCoordinator()
    for image_name in images:
        image_path = os.path.join(DATA_DIR, image_name)
        print(f"Processing: {image_path}")
        coordinator.process_image(image_path)

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
