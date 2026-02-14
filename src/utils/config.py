import os
import json

CONFIG_FILE = "config.json"

# --- DEFAULT CONFIGURATION SETTINGS ---

FACTORY_DEFAULTS = {
    "OCR_SETTINGS": {
        "lang": "en",
        "use_angle_cls": True,
        "show_log": False,
        "ocr_version": "PP-OCRv4",
        "use_gpu": False,
        "det_db_thresh": 0.3,
        "det_db_box_thresh": 0.3,
        "det_db_unclip_ratio": 2.0,
        "det_limit_side_len": 1500,
        "drop_score": 0.05,
        "enable_mkldnn": True,
        "cpu_threads": 4,
        "rec_image_shape": "3, 48, 320",
        "default_input_dir": "data",
        "default_output_dir": "output",
        "crop_padding": 20,
        "auto_crop": True
    },
    "KEY_MAP": {
        "viewer_next": "<Control-Right>",
        "viewer_prev": "<Control-Left>",
        "viewer_save_data": "<Control-s>",
        "viewer_save_img": "<Control-S>",
        "viewer_rotate": "<Control-r>",
        "viewer_crop": "<Control-c>",
        "viewer_reprocess": "<Control-a>",
        "viewer_settings": "<Control-g>",
        "viewer_reset": "<Control-0>"
    },
    "LLM_SETTINGS": {
        "step1_model": "deepseek-r1:8b",
        "text_to_JSON_model": "deepseek-r1:8b",
        "models_path": r"D:\LLMs\models",
        "max_loaded_models": "3",
        "keep_alive": "5m"
    }
}

OCR_SETTINGS = FACTORY_DEFAULTS["OCR_SETTINGS"].copy()
LLM_SETTINGS = FACTORY_DEFAULTS["LLM_SETTINGS"].copy()
KEY_MAP = FACTORY_DEFAULTS["KEY_MAP"].copy()

def load_config():
    global OCR_SETTINGS, LLM_SETTINGS, KEY_MAP
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)
                OCR_SETTINGS.update(config.get("OCR_SETTINGS", {}))
                LLM_SETTINGS.update(config.get("LLM_SETTINGS", {}))
                KEY_MAP.update(config.get("KEY_MAP", {}))
        except Exception as e:
            print(f"Error loading config: {e}")

def save_config(ocr_settings, llm_settings, key_map=None):
    config = {
        "OCR_SETTINGS": ocr_settings,
        "LLM_SETTINGS": llm_settings,
        "KEY_MAP": key_map or KEY_MAP
    }
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=4)
    except Exception as e:
        print(f"Error saving config: {e}")

# Initial load
load_config()

STANDARD_PROMPT = """
### ROLE
You are a precision data extraction engine specialized in processing messy OCR text from official documents.

### TASK
Extract specific data points from the provided OCR text and return them in a strictly structured JSON format.

### EXTRACTION RULES
1. **Ration Card ID**:
   - Locate keywords "Ration Card ID :" or similar as OCR might misspell it.
   - The ID consists of two parts:
     - Category (Alphabetic code): Any one of ["AAY", "PHH", "SPHH", "RKSY-I", "RKSY-II"]
     - ID (Numeric): exactly 10 digits.
   - *Correction Logic*: If the OCR has joined the category and ID (e.g., "SPHH1234567890"), split them. If the category is misspelled, map it to the nearest valid entry from the list above.

2. **Card Holder Name**:
   - Locate the keyword "Name of the Card Holder:" or similar OCR variations.
   - Extract the name (FirstName LastName) following this label.

3. **Mobile Number**:
    - **Location**: Most likely found in the final 20% of the text or the last few lines
    - **OCR Correction**:
    - Replace common character misreads: 'or 'o' -> '0', 'I' or 'l' -> '1', 'S' -> '5, 'B' -> '8'.
    - **Digit Count**: If the count is slightly off (e.g., 9 or 11 digits), use surrounding context to determine if a digit was missed or added by OCR and normalize it to 10 digits if possible; dont return null.

### CONSTRAINTS
- **No Dummy Data**: If a field is not found, return `null`. Do not invent placeholders.
- **OCR Resilience**: Correct common OCR character substitutions (e.g., 'O' instead of '0' in the numeric ID).
- **Format**: Output ONLY valid JSON. No conversational filler or explanations.

### OUTPUT SCHEMA
{
    "category" : "String (AAY, PHH, SPHH, RKSY-I, or RKSY-II)",
    "id" : "String (10 digits)",
    "name" : "String (Upper Case)",
    "mobile" : "String (10 digits)"
}
"""

STANDARD_PROMPT1 = """
You are a precision data extraction tool. Your task is to extract the 'Ration Card ID' from the provided OCR text.

RULES:
1. Look for the keyword "Ration Card ID :" or similar (OCR might misspell it as "Ratioa Card" or "Ratio Card").
2. The ID consists of two parts:
   - Category (Alphabetic code): One of ["AAY", "PHH", "SPHH", "RKSY-I", "RKSY-II"]
   - ID (Numeric): exactly 10 digits.
3. IMPORTANT: If the OCR is messy or joined, separate them and correct the code to the nearest valid category.
4. Look for the keyword "Name of the Card Holder:" or similar (OCR might misspell it)
    - Following the "Name of the Card Holder:" is a name. extract it as "name"
5. Look for a 10 digit indian mobile number. Usually found at the end of the text string. Extract it as "mobile". make sure its digit only.
4. Do not use dummy data. Use only the ID present in the text.

Example JSON:
{{
    "category" : "SPHH",
    "id" : "1234567890",
    "name" : "FIRSTNAME LASTNAME",
    "mobile" : "0123456789"
}}

Output ONLY valid JSON.
"""

# Thinking models benefit from instructions to use their scratchpad
THINKING_PROMPT = """
You are an expert reasoning agent. Your task is to analyze messy OCR text and extract the 'Ration Card ID'.

ANALYSIS STEPS:
1. Identify potential Ration Card ID keywords (e.g., "Ratioa Card").
2. Locate the numeric part (10 digits).
3. Identify the prefix category. If it's garbled (e.g. SPHN), determine which valid category it is meant to be from this list: ["AAY", "PHH", "SPHH", "RKSY-I", "RKSY-II"].
4. Verify the final ID against the rules.

Output ONLY valid JSON after your reasoning.
JSON structure:
{{
    "category" : "CODE",
    "id" : "1234567890"
}}
"""

TEXT_TO_JSON_PROMPT = """
Convert this text into a JSON object
JSON Template:
{{
    "category" : "SPHH",
    "id" : "1234567890",
    "name" : "String (Upper Case)",
    "mobile" : "String (10 digits)"
}}
"""
