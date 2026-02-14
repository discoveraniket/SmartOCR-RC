import logging
import sys
import time
import os
import json
import config

# Direct imports of the specialized classes
from ocr_script import OcrEngine, OCRResultProcessor
from llm_processor import OllamaServiceManager, LlmInferenceEngine
from file_manager import TextFileHandler, LogFormatter, CSVFileHandler, ImageFileHandler

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        stream=sys.stdout,
        force=True
    )

class PipelineCoordinator:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Initialize specialized components
        self.ocr_engine = OcrEngine()
        self.ocr_processor = OCRResultProcessor()
        self.llm_engine = LlmInferenceEngine()
        
        # Paths from config
        self.output_dir = "output"
        self.log_dir = os.path.join(self.output_dir, "logs")
        self.csv_path = os.path.join(self.output_dir, "results.csv")

    def process_image(self, image_path: str):
        self.logger.info(f"--- Processing: {image_path} ---")
        
        base_name = os.path.splitext(os.path.basename(image_path))[0]
        audit_log_path = os.path.join(self.log_dir, f"{base_name}_output.txt")

        # 1. OCR Stage
        start_time = time.time()
        raw_ocr = self.ocr_engine.run_inference(image_path)
        lines = self.ocr_processor.process_paddle_output(raw_ocr)
        
        if not lines:
            self.logger.warning(f"No text extracted from {image_path}")
            return
        
        full_text = "".join(lines)
        TextFileHandler.write(audit_log_path, full_text)
        self.logger.info(f"OCR finished in {time.time() - start_time:.2f}s")

        # 2. LLM Cleaning Stage
        if not OllamaServiceManager.ensure_running():
            self.logger.error("Ollama service is not available.")
            return

        clean_model = config.LLM_SETTINGS.get("step1_model")
        prompt = f"{config.STANDARD_PROMPT}OCR_TEXT:{full_text}"
        
        start_time = time.time()
        clean_result = self.llm_engine.generate_response(clean_model, prompt, think=False)
        
        if not clean_result:
            return
        
        # Append cleaning result to audit log
        formatted_clean = LogFormatter.format_llm_result(clean_result)
        TextFileHandler.append(audit_log_path, formatted_clean)
        self.logger.info(f"Cleaning finished in {time.time() - start_time:.2f}s")

        # 3. Text to JSON Stage
        json_model = config.LLM_SETTINGS.get("text_to_JSON_model")
        json_prompt = f"{config.TEXT_TO_JSON_PROMPT}TEXT:{clean_result['answer']}"
        
        start_time = time.time()
        json_result = self.llm_engine.generate_response(json_model, json_prompt, format="json")
        
        if not json_result:
            return

        # Append JSON result to audit log
        formatted_json = LogFormatter.format_llm_result(json_result)
        TextFileHandler.append(audit_log_path, formatted_json)
        self.logger.info(f"JSON conversion finished in {time.time() - start_time:.2f}s")

        # 4. Finalize Data (CSV and Image Copy)
        self._finalize_output(image_path, json_result['answer'])

    def _finalize_output(self, original_image_path: str, json_string: str):
        try:
            data = json.loads(json_string)
            category = data.get('category', 'UNKNOWN')
            id_val = data.get('id', 'UNKNOWN')
            
            # Copy image to output folder
            ext = os.path.splitext(original_image_path)[1]
            new_name = f"{category}_{id_val}{ext}"
            new_path = ImageFileHandler.copy_and_rename(original_image_path, self.output_dir, new_name)
            
            # Update CSV
            data['processed_image_name'] = os.path.basename(new_path)
            CSVFileHandler.append_row(self.csv_path, data)
            
            self.logger.info(f"Successfully processed and saved to {new_path}")
        except Exception as e:
            self.logger.error(f"Finalization failed: {e}")

def main():
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

    coordinator = PipelineCoordinator()
    for image_name in images:
        image_path = os.path.join(DATA_DIR, image_name)
        coordinator.process_image(image_path)

if __name__ == "__main__":
    main()
