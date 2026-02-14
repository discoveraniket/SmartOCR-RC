import logging
import time
import os
import json
from src.utils import config
from src.core.ocr_engine import OcrEngine, OCRResultProcessor
from src.core.llm_engine import OllamaServiceManager, LlmInferenceEngine
from src.utils.file_ops import TextFileHandler, LogFormatter, CSVFileHandler, ImageFileHandler

logger = logging.getLogger(__name__)

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
        ocr_results = self.ocr_processor.process_paddle_output(raw_ocr)
        
        if not ocr_results:
            self.logger.warning(f"No text extracted from {image_path}")
            return
        
        # Format for audit log (Detailed with coordinates)
        spatial_log = LogFormatter.format_ocr_spatial_data(ocr_results)
        TextFileHandler.write(audit_log_path, spatial_log)
        
        # Format for LLM (Clean text only)
        full_text = "\n".join([item['text'] for item in ocr_results])
        
        # Log the EXACT prompt and text sent to the LLM
        llm_input_audit = (
            "\n" + "="*30 + "\n"
            "EXACT INPUT SENT TO LLM (STEP 1)\n" + 
            "="*30 + "\n" +
            f"{config.STANDARD_PROMPT}\n\n"
            f"OCR_TEXT:\n{full_text}\n" +
            "="*30 + "\n"
        )
        TextFileHandler.append(audit_log_path, llm_input_audit)
        
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
        return self._finalize_output(image_path, json_result['answer'])

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
            return data
        except Exception as e:
            self.logger.error(f"Finalization failed: {e}")
            return None
