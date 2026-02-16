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
from src.utils.image_processing import ImageProcessingService
from src.core.output_manager import OutputManager
from src.core.models import ProcessingMetrics, PipelineResult
from src.core.exceptions import AppError, ServiceUnavailableError, LlmError, OcrError

logger = logging.getLogger(__name__)

class PipelineCoordinator:
    """
    Orchestrates the multi-stage extraction pipeline: 
    OCR -> LLM Cleaning -> JSON Extraction -> Persistence.
    """
    
    def __init__(
        self, 
        output_dir: Optional[str] = None,
        ocr_engine: Optional[OcrEngine] = None,
        det_engine: Optional[OcrEngine] = None,
        llm_engine: Optional[LlmInferenceEngine] = None,
        output_manager: Optional[OutputManager] = None
    ):
        self.logger = logging.getLogger(__name__)
        
        # Dependency Injection with defaults
        self.ocr_engine = ocr_engine or OcrEngine()
        self.det_engine = det_engine or OcrEngine(
            det_limit_side_len=960, 
            use_angle_cls=False, 
            show_log=False
        )
        self.ocr_processor = OCRResultProcessor()
        self.llm_engine = llm_engine or LlmInferenceEngine()
        
        # Output handling
        effective_output_dir = output_dir or config.OCR_SETTINGS.get("default_output_dir", "output")
        self.output_manager = output_manager or OutputManager(effective_output_dir)

    def is_ready(self) -> bool:
        """Checks if both OCR and LLM engines are functional."""
        return self.ocr_engine.is_ready() and self.llm_engine.is_ready()

    def process_image(self, image_path: str, step_callback: Optional[callable] = None) -> Optional[Dict[str, Any]]:
        """Main entry point to process a single image through the entire pipeline."""
        result = self.extract_data(image_path, step_callback=step_callback)
        
        if not result:
            return None

        final_data = self.output_manager.finalize_result(
            image_path, 
            result.json_answer, 
            result.cropped_pil
        )
        
        if final_data:
            self.logger.info(
                f"Finished. Timings - Det: {result.metrics.ocr_det}s | "
                f"Rec: {result.metrics.ocr_rec}s | Step1: {result.metrics.step1_duration}s | "
                f"JSON: {result.metrics.json_duration}s"
            )
            
            if config.OCR_SETTINGS.get("dump_text_flow", False):
                log_base = Path(final_data['processed_image_name']).stem
                self.output_manager.save_audit_log(image_path, result.__dict__, log_base)
            
            return {"data": final_data, "metrics": result.metrics.to_dict()}
            
        return None

    def extract_data(self, image_path: str, model_overrides: Optional[dict] = None, step_callback: Optional[callable] = None) -> Optional[PipelineResult]:
        """Runs the data extraction stages: OCR -> Cleaning -> JSON."""
        self.logger.info(f"--- Starting Pipeline: {Path(image_path).name} ---")
        metrics = ProcessingMetrics()
        overrides = model_overrides or {}
        
        try:
            # 1. OCR Stage
            ocr_data = self._run_ocr_stage(image_path, metrics, step_callback)
            if not ocr_data:
                return None
            
            full_text, ocr_results, cropped_pil = ocr_data
            
            # 2. LLM Cleaning Stage
            clean_result = self._run_cleaning_stage(full_text, overrides, metrics, step_callback)
            if not clean_result:
                return None

            # 3. Text to JSON Stage
            json_result = self._run_json_stage(clean_result['answer'], overrides, metrics, step_callback)
            if not json_result:
                return None

            return self._build_pipeline_result(json_result, clean_result, full_text, metrics, cropped_pil)
        except AppError as e:
            self.logger.error(f"Pipeline error: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected pipeline failure: {e}")
            return None

    def _run_ocr_stage(self, image_path: str, metrics: ProcessingMetrics, step_callback: Optional[callable]):
        """Detects text and optionally re-runs recognition on a cropped region."""
        start_det = time.time()
        raw_ocr = self.det_engine.run_inference(image_path)
        ocr_results = self.ocr_processor.process_paddle_output(raw_ocr)
        metrics.ocr_det = round(time.time() - start_det, 2)
        
        final_ocr_results = ocr_results
        cropped_pil = None

        if config.OCR_SETTINGS.get("auto_crop", False) and ocr_results:
            cropped_pil, final_ocr_results, rec_time = self._perform_autocrop(image_path, ocr_results)
            metrics.ocr_rec = rec_time
        
        metrics.ocr_total = round(metrics.ocr_det + metrics.ocr_rec, 2)
        if step_callback:
            step_callback(metrics.to_dict())
        
        if not final_ocr_results:
            self.logger.warning("No OCR results found.")
            return None
            
        full_text = "\n".join([item['text'] for item in final_ocr_results])
        return full_text, final_ocr_results, cropped_pil

    def _perform_autocrop(self, image_path: str, ocr_results: list):
        """Crops image to text boundaries for potentially better accuracy."""
        start_rec = time.time()
        padding = int(config.OCR_SETTINGS.get("crop_padding", 20)) + 50
        bounds = ImageProcessingService.calculate_text_bounds(ocr_results, padding=padding)
        
        if not bounds:
            return None, ocr_results, 0

        with Image.open(image_path) as pil_img:
            cropped_pil = ImageProcessingService.crop_to_content(pil_img, bounds)
            # Ensure PIL image is loaded into memory before closing file
            cropped_pil.load() 
            
        img_np = np.array(cropped_pil)
        raw_ocr_crop = self.ocr_engine.run_inference(img_np)
        final_results = self.ocr_processor.process_paddle_output(raw_ocr_crop)
        
        duration = round(time.time() - start_rec, 2)
        return cropped_pil, final_results, duration

    def _run_cleaning_stage(self, full_text: str, overrides: dict, metrics: ProcessingMetrics, step_callback: Optional[callable]):
        """Passes raw OCR text to LLM for initial noise reduction."""
        if not OllamaServiceManager.ensure_running():
            return None

        model = overrides.get("step1_model") or config.LLM_SETTINGS.get("step1_model")
        
        # Handle prompt overrides
        base_prompt = config.LLM_SETTINGS.get("standard_prompt", "USE_DEFAULT")
        if base_prompt == "USE_DEFAULT":
            base_prompt = config.STANDARD_PROMPT
            
        prompt = f"{base_prompt}OCR_TEXT:{full_text}"
        think = overrides.get("think", False)
        
        self.logger.info(f"Running LLM cleaning ({model})...")
        result = self.llm_engine.generate_response(model, prompt, think=think)
        
        metrics.step1_duration = round(result.get('duration', 0), 2) if result else 0
        if step_callback:
            step_callback(metrics.to_dict())
        return result

    def _run_json_stage(self, cleaned_text: str, overrides: dict, metrics: ProcessingMetrics, step_callback: Optional[callable]):
        """Converts cleaned text into structured JSON via LLM."""
        model = overrides.get("text_to_JSON_model") or config.LLM_SETTINGS.get("text_to_JSON_model")
        
        # Handle prompt overrides
        base_prompt = config.LLM_SETTINGS.get("text_to_json_prompt", "USE_DEFAULT")
        if base_prompt == "USE_DEFAULT":
            base_prompt = config.TEXT_TO_JSON_PROMPT
            
        prompt = f"{base_prompt}\n### SOURCE TEXT:\n{cleaned_text}\n### JSON OUTPUT:"
        
        self.logger.info(f"Running LLM JSON extraction ({model})...")
        result = self.llm_engine.generate_response(model, prompt, format="json")
        
        metrics.json_duration = round(result.get('duration', 0), 2) if result else 0
        if step_callback:
            step_callback(metrics.to_dict())
        return result

    def _build_pipeline_result(self, json_res, clean_res, raw_text, metrics, cropped_pil) -> Optional[PipelineResult]:
        """Validates JSON output and bundles data into a PipelineResult model."""
        try:
            data = json.loads(json_res['answer'])
            return PipelineResult(
                data=data,
                metrics=metrics,
                json_answer=json_res['answer'],
                raw_text=raw_text,
                cleaned_text=clean_res['answer'],
                cropped_pil=cropped_pil
            )
        except Exception as e:
            self.logger.error(f"Failed to parse LLM JSON output: {e}")
            return None
