import pytest
from pathlib import Path
from unittest.mock import patch
from src.utils import config

def test_prompt_loading():
    """Verify that prompts are loaded from the resources directory."""
    # These should have content if the files exist and were read during import
    assert len(config.STANDARD_PROMPT) > 0
    assert len(config.TEXT_TO_JSON_PROMPT) > 0
    assert "ROLE" in config.STANDARD_PROMPT
    assert "JSON" in config.TEXT_TO_JSON_PROMPT

def test_config_defaults():
    """Verify factory defaults are correctly initialized."""
    assert config.OCR_SETTINGS["lang"] == "en"
    assert config.LLM_SETTINGS["keep_alive"] == "5m"

def test_save_and_load_config(tmp_path):
    """Test saving and loading config to a temporary file."""
    # Override CONFIG_FILE for this test
    test_config_file = tmp_path / "test_config.json"
    
    with patch('src.utils.config.CONFIG_FILE', test_config_file):
        # Initial save
        ocr = config.FACTORY_DEFAULTS["OCR_SETTINGS"].copy()
        ocr.update({"lang": "fr", "auto_crop": False})
        llm = config.FACTORY_DEFAULTS["LLM_SETTINGS"].copy()
        llm.update({"step1_model": "test-model"})
        
        config.save_config(ocr, llm)
        
        assert test_config_file.exists()
        
        # Reset globals and reload (manually since it's global)
        with patch('src.utils.config.OCR_SETTINGS', config.FACTORY_DEFAULTS["OCR_SETTINGS"].copy()):
            with patch('src.utils.config.LLM_SETTINGS', config.FACTORY_DEFAULTS["LLM_SETTINGS"].copy()):
                config.load_config()
                # Actually, load_config updates the globals in the module, 
                # but our patched variables here won't be seen by the module unless we are careful.
                # Let's just check the module level ones after the call.
                pass
        
        # To truly test load_config we'd need to let it update the module globals
        config.load_config()
        assert config.OCR_SETTINGS["lang"] == "fr"
        assert config.OCR_SETTINGS["auto_crop"] is False
