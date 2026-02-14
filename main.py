import logging
import sys
import time
import os
import json
import config
from ocr_script import OcrProcessor
from llm_processor import LlmManager
from file_manager import save_to_file, append_llm_result, save_to_csv, copy_and_rename_image

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
    output_path = os.path.join("output", "logs", f"{base_name}_output.txt")
    csv_path = os.path.join("output", "results.csv")
    output_dir = "output"

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
    
    #----------Text to JSON----------

    model = config.LLM_SETTINGS.get("text_to_JSON_model")
    prompt = f"{config.TEXT_TO_JSON_PROMPT}\n\nTEXT:\n{result['answer']}"

    logger.info(f"Text to JSON Model: {model}")
    start_time = time.time()
    result = llm.to_json(model, prompt)
    duration = time.time() - start_time
    logger.info(f"Text to JSON finished in {duration:.2f}s")
    
    if result:
        append_llm_result(output_path, result)
        
        # Parse JSON and save to CSV
        try:
            data = json.loads(result['answer'])
            category = data.get('category', 'UNKNOWN')
            id_val = data.get('id', 'UNKNOWN')
            
            # Copy image to output folder with new name
            ext = os.path.splitext(image_path)[1]
            new_image_name = f"{category}_{id_val}{ext}"
            new_image_path = copy_and_rename_image(image_path, output_dir, new_image_name)
            
            # Update data with new image name and save to CSV
            data['processed_image_name'] = os.path.basename(new_image_path)
            save_to_csv(data, csv_path)
            
        except Exception as e:
            logger.error(f"Failed to parse JSON or save CSV: {e}")
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
