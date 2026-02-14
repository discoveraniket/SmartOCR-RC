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
    def __init__(self):
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
        
        # Paths from config
        self.output_dir = "output"
        self.log_dir = os.path.join(self.output_dir, "logs")
        self.csv_path = os.path.join(self.output_dir, "results.csv")

    def process_image(self, image_path: str):
        result = self.extract_data(image_path)
        if result:
            return self._finalize_output(image_path, result['json_answer'], result.get('cropped_pil'))
        return None

    def extract_data(self, image_path: str, model_overrides: dict = None):
        """Runs OCR and LLM stages. Supports optional auto-cropping."""
        self.logger.info(f"--- Extracting Data: {image_path} ---")
        metrics = {}
        overrides = model_overrides or {}
        
        # 1. OCR Stage (Initial Detection - Fast Pass)
        start_time = time.time()
        raw_ocr = self.det_engine.run_inference(image_path)
        ocr_results = self.ocr_processor.process_paddle_output(raw_ocr)
        
        final_ocr_results = ocr_results
        cropped_pil = None

        # 2. Auto-Crop logic
        if config.OCR_SETTINGS.get("auto_crop", False) and ocr_results:
            self.logger.info("Applying auto-crop for better accuracy...")
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
        
        metrics['ocr'] = round(time.time() - start_time, 2)
        
        if not final_ocr_results:
            return None
        
        full_text = "\n".join([item['text'] for item in final_ocr_results])

        # 3. LLM Cleaning Stage
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
            return {"data": data, "metrics": metrics, "json_answer": json_result['answer'], "cropped_pil": cropped_pil}
        except:
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
