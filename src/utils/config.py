import json
import logging
from pathlib import Path
from typing import Dict, Any, List, TypedDict

logger = logging.getLogger(__name__)

CONFIG_FILE = Path("config.json")
PROMPTS_DIR = Path("src/resources/prompts")

class OcrSettings(TypedDict):
    lang: str
    use_angle_cls: bool
    show_log: bool
    ocr_version: str
    use_gpu: bool
    det_db_thresh: float
    det_db_box_thresh: float
    det_db_unclip_ratio: float
    det_limit_side_len: int
    drop_score: float
    enable_mkldnn: bool
    cpu_threads: int
    rec_image_shape: str
    default_input_dir: str
    default_output_dir: str
    crop_padding: int
    auto_crop: bool
    dump_text_flow: bool

class LlmSettings(TypedDict):
    step1_model: str
    text_to_JSON_model: str
    available_models: List[str]
    models_path: str
    max_loaded_models: str
    keep_alive: str
    standard_prompt: str
    text_to_json_prompt: str

FACTORY_DEFAULTS: Dict[str, Any] = {
    "OCR_SETTINGS": {
        "lang": "en",
        "use_angle_cls": True,
        "show_log": True,
        "ocr_version": "PP-OCRv4",
        "use_gpu": False,
        "det_db_thresh": 0.1, # 0.3,
        "det_db_box_thresh": 0.5, # 0.3,
        "det_db_unclip_ratio": 0.01, #2.0,
        "det_limit_side_len": 2880, #1500,
        "drop_score": 0.05,
        "enable_mkldnn": True,
        "cpu_threads": 18,
        "rec_image_shape": "3, 48, 320",
        "default_input_dir": "data",
        "default_output_dir": "output",
        "crop_padding": 20,
        "auto_crop": True,
        "dump_text_flow": True,
        "viewer_font_size": 18,
        "debt_db_score_mode": "slow", # <--- New param from here
        "rec_batch_num": 20,
        "enable_mkldnn": True
    },
    "KEY_MAP": {
        "viewer_next": "<Control-Right>",
        "viewer_prev": "<Control-Left>",
        "viewer_save_data": "<Control-S>",
        "viewer_save_img": "<Control-I>",
        "viewer_rotate": "<Control-R>",
        "viewer_crop": "<Control-C>",
        "viewer_reprocess": "<Control-A>",
        "viewer_settings": "<Control-G>",
        "viewer_view_log": "<Control-L>",
        "viewer_reset": "<Control-0>"
    },
    "KEY_HINTS": {
        "viewer_next": "",
        "viewer_prev": "",
        "viewer_save_data": "[S]",
        "viewer_save_img": "[I]",
        "viewer_rotate": "[R]",
        "viewer_crop": "[K]",
        "viewer_reprocess": "[A]",
        "viewer_settings": "[G]",
        "viewer_view_log": "[L]",
        "viewer_reset": "[0]"
    },
    "LLM_SETTINGS": {
        "step1_model": "deepseek-r1:8b",
        "text_to_JSON_model": "deepseek-r1:8b",
        "available_models": ["deepseek-r1:8b", "llama3.2:3b", "richardyoung/olmocr2:7b-q8", "qwen2.5:14b-instruct"],
        "models_path": r"D:\LLMs\models",
        "max_loaded_models": "3",
        "keep_alive": "5m",
        "standard_prompt": "USE_DEFAULT",
        "text_to_json_prompt": "USE_DEFAULT"
    }
}

def load_prompt(filename: str) -> str:
    """Loads a prompt from the resources directory."""
    path = PROMPTS_DIR / filename
    if path.exists():
        return path.read_text(encoding="utf-8")
    logger.warning(f"Prompt file not found: {path}")
    return ""

# Load static prompts
STANDARD_PROMPT = load_prompt("standard_prompt.txt")
STANDARD_PROMPT1 = load_prompt("standard_prompt1.txt")
THINKING_PROMPT = load_prompt("thinking_prompt.txt")
TEXT_TO_JSON_PROMPT = load_prompt("text_to_json.txt")

# Global instances for backward compatibility
OCR_SETTINGS = FACTORY_DEFAULTS["OCR_SETTINGS"].copy()
LLM_SETTINGS = FACTORY_DEFAULTS["LLM_SETTINGS"].copy()
KEY_MAP = FACTORY_DEFAULTS["KEY_MAP"].copy()
KEY_HINTS = FACTORY_DEFAULTS["KEY_HINTS"].copy()

def load_config():
    """Loads configuration from JSON file, merging with factory defaults."""
    global OCR_SETTINGS, LLM_SETTINGS, KEY_MAP, KEY_HINTS
    if CONFIG_FILE.exists():
        try:
            with CONFIG_FILE.open("r", encoding="utf-8") as f:
                config_data = json.load(f)
                OCR_SETTINGS.update(config_data.get("OCR_SETTINGS", {}))
                LLM_SETTINGS.update(config_data.get("LLM_SETTINGS", {}))
                KEY_MAP.update(config_data.get("KEY_MAP", {}))
                KEY_HINTS.update(config_data.get("KEY_HINTS", {}))
        except Exception as e:
            logger.error(f"Error loading config: {e}")

def save_config(ocr_settings: dict, llm_settings: dict, key_map: dict = None, key_hints: dict = None):
    """Saves current configuration to JSON file."""
    config_data = {
        "OCR_SETTINGS": ocr_settings,
        "LLM_SETTINGS": llm_settings,
        "KEY_MAP": key_map or KEY_MAP,
        "KEY_HINTS": key_hints or KEY_HINTS
    }
    try:
        with CONFIG_FILE.open("w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=4)
    except Exception as e:
        logger.error(f"Error saving config: {e}")

# Initial load
load_config()
