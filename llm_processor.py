import os
import time
import logging
import subprocess
import ollama
import config

logger = logging.getLogger(__name__)

class LlmManager:
    def __init__(self, model_name: str = None):
        os.environ["OLLAMA_MODELS"] = r"D:\LLMs\models"

    def initialize_service(self) -> bool:
        """Starts Ollama service."""
        return self._ensure_running()

    def _ensure_running(self) -> bool:
        try:
            ollama.list()
            return True
        except Exception:
            logger.info("Starting Ollama service...")
            try:
                subprocess.Popen(["ollama", "serve"], 
                                stdout=subprocess.DEVNULL, 
                                stderr=subprocess.DEVNULL,
                                creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0)
                for _ in range(5):
                    time.sleep(2)
                    try:
                        ollama.list()
                        return True
                    except: continue
                return False
            except Exception as e:
                logger.error(f"Failed to launch Ollama: {e}")
                return False

    def _ensure_model_loaded(self, model_name: str) -> bool:
        try:
            logger.info(f"Ensuring model '{model_name}' is ready...")
            ollama.pull(model_name)
            return True
        except Exception as e:
            logger.error(f"Model load failed: {e}")
            return False

    def clean_text(self, model: str, prompt: str, think: bool = False) -> dict:
        """Step 2: Deep Extraction."""
        self._ensure_model_loaded(model)
        try:
            response = ollama.generate(model=model, prompt=prompt, think=think)
            return {
                "answer": response.get('response', '').strip(),
                "thinking": response.get('thinking', '').strip() if think else None
            }
        except Exception as e:
            logger.error(f"Deep Extraction failed: {e}")
            return None

    def to_json(self, model, prompt) -> dict:
        """Step 3: Qwen Text-to-JSON Conversion."""
        self._ensure_model_loaded(model)
        try:
            response = ollama.generate(model=model, prompt=prompt, format="json", think=False)
            return {
                "answer": response.get('response', '').strip(),
                "thinking": None
            }
        except Exception as e:
            logger.error(f"JSON conversion failed: {e}")
            return None
