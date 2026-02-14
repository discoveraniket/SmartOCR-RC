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
        result = self.extract_data(image_path)
        if result:
            return self._finalize_output(image_path, result['json_answer'])
        return None

    def extract_data(self, image_path: str, model_overrides: dict = None):
        """Runs OCR and LLM stages but does NOT save to CSV or copy files."""
        self.logger.info(f"--- Extracting Data: {image_path} ---")
        metrics = {}
        
        overrides = model_overrides or {}
        
        base_name = os.path.splitext(os.path.basename(image_path))[0]
        audit_log_path = os.path.join(self.log_dir, f"{base_name}_extraction.txt")

        # 1. OCR Stage
        # ... (OCR logic)
        start_time = time.time()
        raw_ocr = self.ocr_engine.run_inference(image_path)
        ocr_results = self.ocr_processor.process_paddle_output(raw_ocr)
        metrics['ocr'] = round(time.time() - start_time, 2)
        
        if not ocr_results:
            return None
        
        full_text = "\n".join([item['text'] for item in ocr_results])

        # 2. LLM Cleaning Stage
        if not OllamaServiceManager.ensure_running():
            return None

        clean_model = overrides.get("step1_model") or config.LLM_SETTINGS.get("step1_model")
        prompt = f"{config.STANDARD_PROMPT}OCR_TEXT:{full_text}"
        
        # Check for think override
        think_enabled = overrides.get("think", False)
        
        start_time = time.time()
        clean_result = self.llm_engine.generate_response(clean_model, prompt, think=think_enabled)
        metrics['step1'] = round(time.time() - start_time, 2)
        
        if not clean_result:
            return None

        # 3. Text to JSON Stage
        json_model = overrides.get("text_to_JSON_model") or config.LLM_SETTINGS.get("text_to_JSON_model")
        json_prompt = f"{config.TEXT_TO_JSON_PROMPT}TEXT:{clean_result['answer']}"
        
        start_time = time.time()
        json_result = self.llm_engine.generate_response(json_model, json_prompt, format="json")
        metrics['json'] = round(time.time() - start_time, 2)
        
        if not json_result:
            return None

        try:
            data = json.loads(json_result['answer'])
            return {"data": data, "metrics": metrics, "json_answer": json_result['answer']}
        except:
            return None

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
