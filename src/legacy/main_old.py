import logging
import sys
import argparse
from src.core.pipeline import run_pipeline
from src.ui.main_window import MainWindow

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        stream=sys.stdout,
        force=True
    )

def run_cli():
    import os
    DATA_DIR = "data"
    
    if not os.path.exists(DATA_DIR):
        print(f"Directory {DATA_DIR} does not exist.")
        sys.exit(1)

    image_extensions = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff')
    images = [f for f in os.listdir(DATA_DIR) if f.lower().endswith(image_extensions)]
    
    if not images:
        print(f"No images found in {DATA_DIR}")
        sys.exit(0)

    for image_name in images:
        image_path = os.path.join(DATA_DIR, image_name)
        print(f"\nProcessing: {image_path}")
        run_pipeline(image_path)

def main():
    parser = argparse.ArgumentParser(description="RC-PaddleOCR Processor")
    parser.add_argument("--gui", action="store_true", help="Run in GUI mode")
    args = parser.parse_args()

    setup_logging()

    if args.gui:
        app = MainWindow()
        app.mainloop()
    else:
        run_cli()

if __name__ == "__main__":
    main()
