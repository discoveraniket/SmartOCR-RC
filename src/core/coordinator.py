import logging
import time
import json
from pathlib import Path
from typing import Union, Optional, Any, Dict
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
        self.output_dir = Path(output_dir or config.OCR_SETTINGS.get("default_output_dir", "output"))
        self.log_dir = self.output_dir / "logs"
        self.csv_path = self.output_dir / "results.csv"

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
                        log_base = Path(final_name).stem
                        self._dump_text_flow(image_path, result, log_base)
                
                return {"data": final_data, "metrics": metrics}
        return None

    def _dump_text_flow(self, image_path: str, result: dict, log_base: str):
        """Dumps the text data flow (OCR + LLM) to a text file for auditing."""
        try:
            log_filename = f"{log_base}.txt"
            log_path = self.log_dir / log_filename
            
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
        """Runs the multi-stage extraction pipeline: OCR -> Cleaning -> JSON."""
        self.logger.info(f"--- Starting Pipeline: {Path(image_path).name} ---")
        metrics = {}
        overrides = model_overrides or {}
        
        # 1. OCR Stage
        ocr_text, ocr_results, cropped_pil = self._run_ocr_stage(image_path, metrics, step_callback)
        if not ocr_text:
            return None
        
        # 2. LLM Cleaning Stage
        clean_result = self._run_cleaning_stage(ocr_text, overrides, metrics, step_callback)
        if not clean_result:
            return None

        # 3. Text to JSON Stage
        json_result = self._run_json_stage(clean_result['answer'], overrides, metrics, step_callback)
        if not json_result:
            return None

        return self._prepare_pipeline_result(json_result, clean_result, ocr_text, metrics, cropped_pil)

    def _run_ocr_stage(self, image_path, metrics, step_callback):
        """Handles initial detection and optional auto-cropping."""
        # Initial Detection
        start_time_det = time.time()
        raw_ocr = self.det_engine.run_inference(image_path)
        ocr_results = self.ocr_processor.process_paddle_output(raw_ocr)
        metrics['ocr_det'] = round(time.time() - start_time_det, 2)
        
        metrics['ocr_rec'] = 0
        final_ocr_results = ocr_results
        cropped_pil = None

        # Auto-Crop logic
        if config.OCR_SETTINGS.get("auto_crop", False) and ocr_results:
            cropped_pil, final_ocr_results, rec_time = self._perform_autocrop(image_path, ocr_results)
            metrics['ocr_rec'] = rec_time
            if cropped_pil:
                self.logger.info("Re-ran OCR on cropped image.")
        
        metrics['ocr'] = round(metrics['ocr_det'] + metrics['ocr_rec'], 2)
        if step_callback: step_callback(metrics)
        
        if not final_ocr_results:
            self.logger.warning("No OCR results found.")
            return None, None, None
            
        full_text = "\n".join([item['text'] for item in final_ocr_results])
        return full_text, final_ocr_results, cropped_pil

    def _perform_autocrop(self, image_path, ocr_results):
        """Logic for cropping image to text bounds and re-running OCR."""
        start_time_rec = time.time()
        padding = int(config.OCR_SETTINGS.get("crop_padding", 20)) + 50
        bounds = ImageProcessingService.calculate_text_bounds(ocr_results, padding=padding)
        
        if not bounds:
            return None, ocr_results, 0

        pil_img = Image.open(image_path)
        cropped_pil = ImageProcessingService.crop_to_content(pil_img, bounds)
        img_np = np.array(cropped_pil)
        
        raw_ocr_crop = self.ocr_engine.run_inference(img_np)
        final_results = self.ocr_processor.process_paddle_output(raw_ocr_crop)
        
        duration = round(time.time() - start_time_rec, 2)
        return cropped_pil, final_results, duration

    def _run_cleaning_stage(self, full_text, overrides, metrics, step_callback):
        """Handles the first LLM pass for text cleaning."""
        if not OllamaServiceManager.ensure_running():
            self.logger.error("Ollama service not running.")
            return None

        model = overrides.get("step1_model") or config.LLM_SETTINGS.get("step1_model")
        base_prompt = config.LLM_SETTINGS.get("standard_prompt", "USE_DEFAULT")
        if base_prompt == "USE_DEFAULT":
            base_prompt = config.STANDARD_PROMPT
            
        prompt = f"{base_prompt}OCR_TEXT:{full_text}"
        think_enabled = overrides.get("think", False)
        
        self.logger.info(f"Running LLM cleaning ({model})...")
        result = self.llm_engine.generate_response(model, prompt, think=think_enabled)
        
        metrics['step1'] = round(result.get('duration', 0), 2) if result else 0
        if step_callback: step_callback(metrics)
        return result

    def _run_json_stage(self, cleaned_text, overrides, metrics, step_callback):
        """Handles the second LLM pass for JSON conversion."""
        model = overrides.get("text_to_JSON_model") or config.LLM_SETTINGS.get("text_to_JSON_model")
        base_prompt = config.LLM_SETTINGS.get("text_to_json_prompt", "USE_DEFAULT")
        if base_prompt == "USE_DEFAULT":
            base_prompt = config.TEXT_TO_JSON_PROMPT
            
        prompt = f"{base_prompt}\n### SOURCE TEXT:\n{cleaned_text}"
        
        self.logger.info(f"Running LLM JSON extraction ({model})...")
        result = self.llm_engine.generate_response(model, prompt, format="json")
        
        metrics['json'] = round(result.get('duration', 0), 2) if result else 0
        if step_callback: step_callback(metrics)
        return result

    def _prepare_pipeline_result(self, json_result, clean_result, full_text, metrics, cropped_pil):
        """Parses final JSON and packages the full result dictionary."""
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

    def _finalize_output(self, original_image_path: Union[str, Path], json_string: str, cropped_pil: Image.Image = None):
        """Saves processed image, updates CSV, and returns final data dictionary."""
        try:
            data = json.loads(json_string)
            category = data.get('category') or 'UNKNOWN'
            id_val = data.get('id') or 'UNKNOWN'
            
            # Prepare file names and paths
            orig_path = Path(original_image_path)
            new_name = f"{category}_{id_val}{orig_path.suffix}"
            output_dir = Path(self.output_dir)
            
            if cropped_pil:
                new_path = output_dir / new_name
                ImageProcessingService.save_image(cropped_pil, new_path)
                self.logger.info(f"Saved cropped image to {new_path}")
            else:
                new_path = ImageFileHandler.copy_and_rename(str(orig_path), str(output_dir), new_name)
                self.logger.info(f"Copied original image to {new_path}")
            
            # Update data and persist to CSV
            data['processed_image_name'] = Path(new_path).name
            CSVFileHandler.append_row(self.csv_path, data)
            
            self.logger.info(f"Successfully finalized: {data['processed_image_name']}")
            return data
        except Exception as e:
            self.logger.error(f"Finalization failed for {original_image_path}: {e}")
            return None
