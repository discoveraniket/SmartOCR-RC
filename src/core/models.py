from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from PIL import Image

@dataclass
class ProcessingMetrics:
    ocr_det: float = 0.0
    ocr_rec: float = 0.0
    ocr_total: float = 0.0
    step1_duration: float = 0.0
    json_duration: float = 0.0
    total_duration: float = 0.0

    def to_dict(self) -> Dict[str, float]:
        return {
            "ocr_det": self.ocr_det,
            "ocr_rec": self.ocr_rec,
            "ocr": self.ocr_total,
            "step1": self.step1_duration,
            "json": self.json_duration
        }

@dataclass
class PipelineResult:
    data: Dict[str, Any]
    metrics: ProcessingMetrics
    json_answer: str
    raw_text: str
    cleaned_text: str
    cropped_pil: Optional[Image.Image] = None
