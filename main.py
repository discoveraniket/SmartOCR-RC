import logging
import sys
import time
import os
import config
from ocr_script import OcrProcessor
from llm_processor import LlmManager
from file_manager import save_to_file, append_llm_result

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        stream=sys.stdout,
        force=True
    )

def run_pipeline(image_path: str):
    logger = logging.getLogger(__name__)
    
    # Generate output path based on image filename
    base_name = os.path.splitext(os.path.basename(image_path))[0]
    output_path = f"{base_name}_output.txt"

    # 2. OCR Stage
    ocr = OcrProcessor()
    start_time = time.time()
    lines = ocr.extract_text(image_path)
    if not lines:
        return
    
    duration = time.time() - start_time
    logger.info(f"OCR finished in {duration:.2f}s for {image_path}")
    
    full_text = "\n".join(lines)
    save_to_file(full_text, output_path)

    # 3. Clean Raw OCR
    llm = LlmManager()
    
    if not llm.initialize_service():
        logger.error("LLM Service initialization failed.")
        return
    
    model = config.LLM_SETTINGS.get("step1_model")
    think = False  # Set this to False to hide reasoning
    prompt = f"{config.STANDARD_PROMPT}\n\nOCR_TEXT:\n{full_text}"

    logger.info(f"Raw text sent to Model: {model}")
    start_time = time.time()
    result = llm.clean_text(model, prompt, think)
    duration = time.time() - start_time
    logger.info(f"OCR Data cleaning finished in {duration:.2f}s")
    
    if result:
        append_llm_result(output_path, result)
    else:
        logger.error("LLM stage failed to produce a result.")
        return
    
    model = config.LLM_SETTINGS.get("text_to_JSON_model")
    prompt = f"{config.TEXT_TO_JSON_PROMPT}\n\nTEXT:\n{result['answer']}"

    logger.info(f"Text to JSON Model: {model}")
    start_time = time.time()
    result = llm.to_json(model, prompt)
    duration = time.time() - start_time
    logger.info(f"Text to JSON finished in {duration:.2f}s")
    
    if result:
        append_llm_result(output_path, result)
    else:
        logger.error("Text to JSON failed to produce a result.")

if __name__ == "__main__":
    setup_logging()
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
