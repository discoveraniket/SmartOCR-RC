import logging
import time
import os
import json
from PIL import Image
import numpy as np
from src.utils import config
from src.core.ocr_engine import OcrEngine, OCRResultProcessor
from src.core.llm_engine import OllamaServiceManager, LlmInferenceEngine
from src.utils.file_ops import TextFileHandler, LogFormatter, CSVFileHandler, ImageFileHandler
from src.utils.image_processing import ImageProcessingService

logger = logging.getLogger(__name__)

class PipelineCoordinator:
    def __init__(self, output_dir: str = None):
        self.logger = logging.getLogger(__name__)
        
        # Initialize specialized components
        self.ocr_engine = OcrEngine() # Main engine for recognition
        
        # Fast engine for detection only
        self.det_engine = OcrEngine(
            det_limit_side_len=960, 
            use_angle_cls=False, 
            show_log=False
        )
        
        self.ocr_processor = OCRResultProcessor()
        self.llm_engine = LlmInferenceEngine()
        
        # Paths from config or override
        self.output_dir = output_dir or config.OCR_SETTINGS.get("default_output_dir", "output")
        self.log_dir = os.path.join(self.output_dir, "logs")
        self.csv_path = os.path.join(self.output_dir, "results.csv")

    def process_image(self, image_path: str, step_callback: callable = None):
        result = self.extract_data(image_path, step_callback=step_callback)
        if result:
            final_data = self._finalize_output(image_path, result['json_answer'], result.get('cropped_pil'))
            if final_data:
                metrics = result.get('metrics', {})
                self.logger.info(f"Finished. Timings - Det: {metrics.get('ocr_det')}s | Rec: {metrics.get('ocr_rec')}s | Step1: {metrics.get('step1')}s | JSON: {metrics.get('json')}s")
                
                # Dump text flow to audit log if enabled
                if config.OCR_SETTINGS.get("dump_text_flow", False):
                    # Use the final processed image name for the log file to match perfectly
                    final_name = final_data.get('processed_image_name')
                    if final_name:
                        log_base = os.path.splitext(final_name)[0]
                        self._dump_text_flow(image_path, result, log_base)
                
                return {"data": final_data, "metrics": metrics}
        return None

    def _dump_text_flow(self, image_path: str, result: dict, log_base: str):
        """Dumps the text data flow (OCR + LLM) to a text file for auditing."""
        try:
            log_filename = f"{log_base}.txt"
            log_path = os.path.join(self.log_dir, log_filename)
            
            content = []
            content.append(f"SOURCE IMAGE: {image_path}")
            content.append(f"FINAL NAME: {log_base}")
            
            content.append("\n" + "="*50)
            content.append("1. RAW OCR TEXT")
            content.append("="*50)
            content.append(result.get('raw_text', ''))
            
            content.append("\n" + "="*50)
            content.append("2. LLM CLEANED TEXT")
            content.append("="*50)
            content.append(result.get('cleaned_text', ''))
            
            content.append("\n" + "="*50)
            content.append("3. FINAL JSON OUTPUT")
            content.append("="*50)
            content.append(result.get('json_answer', ''))
            
            TextFileHandler.write(log_path, "\n".join(content))
        except Exception as e:
            self.logger.error(f"Failed to dump text flow: {e}")

    def extract_data(self, image_path: str, model_overrides: dict = None, step_callback: callable = None):
        """Runs OCR and LLM stages. Supports optional auto-cropping."""
        self.logger.info(f"--- Processing: {os.path.basename(image_path)} ---")
        metrics = {}
        overrides = model_overrides or {}
        
        # 1. OCR Stage (Initial Detection - Fast Pass)
        start_time_det = time.time()
        raw_ocr = self.det_engine.run_inference(image_path)
        ocr_results = self.ocr_processor.process_paddle_output(raw_ocr)
        metrics['ocr_det'] = round(time.time() - start_time_det, 2)
        self.logger.info(f"OCR Detection took: {metrics['ocr_det']}s")
        if step_callback: step_callback(metrics)
        
        metrics['ocr_rec'] = 0
        final_ocr_results = ocr_results
        cropped_pil = None

        # 2. Auto-Crop logic
        if config.OCR_SETTINGS.get("auto_crop", False) and ocr_results:
            self.logger.info("Applying auto-crop for better accuracy...")
            start_time_rec = time.time()
            # Use default padding + 50 extra as requested
            padding = int(config.OCR_SETTINGS.get("crop_padding", 20)) + 50
            bounds = ImageProcessingService.calculate_text_bounds(ocr_results, padding=padding)
            
            if bounds:
                pil_img = Image.open(image_path)
                cropped_pil = ImageProcessingService.crop_to_content(pil_img, bounds)
                
                # Convert PIL to numpy for PaddleOCR (expects BGR for some versions, but Paddle handles RGB too)
                img_np = np.array(cropped_pil)
                
                # Run OCR again on cropped image
                raw_ocr_crop = self.ocr_engine.run_inference(img_np)
                final_ocr_results = self.ocr_processor.process_paddle_output(raw_ocr_crop)
                
                self.logger.info("Re-ran OCR on cropped image.")
            
            metrics['ocr_rec'] = round(time.time() - start_time_rec, 2)
            self.logger.info(f"OCR Recognition took: {metrics['ocr_rec']}s")
            if step_callback: step_callback(metrics)
        
        # Total OCR metric for UI compatibility
        metrics['ocr'] = round(metrics['ocr_det'] + metrics['ocr_rec'], 2)
        
        if not final_ocr_results:
            self.logger.warning("No OCR results found.")
            return None
        
        full_text = "\n".join([item['text'] for item in final_ocr_results])

        # 3. LLM Cleaning Stage
        if not OllamaServiceManager.ensure_running():
            self.logger.error("Ollama service not running.")
            return None

        clean_model = overrides.get("step1_model") or config.LLM_SETTINGS.get("step1_model")
        
        # Use configurable prompt if available
        base_prompt = config.LLM_SETTINGS.get("standard_prompt", "USE_DEFAULT")
        if base_prompt == "USE_DEFAULT":
            base_prompt = config.STANDARD_PROMPT
            
        prompt = f"{base_prompt}OCR_TEXT:{full_text}"
        
        # Check for think override
        think_enabled = overrides.get("think", False)
        
        self.logger.info(f"Running LLM cleaning with model: {clean_model}...")
        start_time_step1 = time.time()
        clean_result = self.llm_engine.generate_response(clean_model, prompt, think=think_enabled)
        metrics['step1'] = round(time.time() - start_time_step1, 2)
        self.logger.info(f"LLM Cleaning took: {metrics['step1']}s")
        if step_callback: step_callback(metrics)
        
        if not clean_result:
            return None

        # 3. Text to JSON Stage
        json_model = overrides.get("text_to_JSON_model") or config.LLM_SETTINGS.get("text_to_JSON_model")
        
        # Use configurable prompt if available
        json_base_prompt = config.LLM_SETTINGS.get("text_to_json_prompt", "USE_DEFAULT")
        if json_base_prompt == "USE_DEFAULT":
            json_base_prompt = config.TEXT_TO_JSON_PROMPT
            
        json_prompt = f"{json_base_prompt}TEXT:{clean_result['answer']}"
        
        self.logger.info(f"Running LLM JSON extraction with model: {json_model}...")
        start_time_json = time.time()
        json_result = self.llm_engine.generate_response(json_model, json_prompt, format="json")
        metrics['json'] = round(time.time() - start_time_json, 2)
        self.logger.info(f"LLM JSON extraction took: {metrics['json']}s")
        if step_callback: step_callback(metrics)
        
        if not json_result:
            return None

        try:
            data = json.loads(json_result['answer'])
            return {
                "data": data, 
                "metrics": metrics, 
                "json_answer": json_result['answer'], 
                "cropped_pil": cropped_pil,
                "raw_text": full_text,
                "cleaned_text": clean_result['answer']
            }
        except Exception as e:
            self.logger.error(f"Failed to parse LLM JSON output: {e}")
            return None

    def _finalize_output(self, original_image_path: str, json_string: str, cropped_pil: Image.Image = None):
        try:
            data = json.loads(json_string)
            category = data.get('category', 'UNKNOWN')
            id_val = data.get('id', 'UNKNOWN')
            
            # Save or Copy image to output folder
            ext = os.path.splitext(original_image_path)[1]
            new_name = f"{category}_{id_val}{ext}"
            
            if cropped_pil:
                new_path = os.path.join(self.output_dir, new_name)
                ImageProcessingService.save_image(cropped_pil, new_path)
                self.logger.info(f"Saved cropped image to {new_path}")
            else:
                new_path = ImageFileHandler.copy_and_rename(original_image_path, self.output_dir, new_name)
                self.logger.info(f"Copied original image to {new_path}")
            
            # Update CSV
            data['processed_image_name'] = os.path.basename(new_path)
            CSVFileHandler.append_row(self.csv_path, data)
            
            self.logger.info(f"Successfully processed and saved to {new_path}")
            return data
        except Exception as e:
            self.logger.error(f"Finalization failed: {e}")
            return None
