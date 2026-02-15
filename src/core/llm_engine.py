import os
import time
import logging
import subprocess
import ollama
from src.utils import config
from typing import Optional, Dict, Any
from src.core.exceptions import ServiceUnavailableError, LlmError

logger = logging.getLogger(__name__)

class OllamaServiceManager:
    """Handles the lifecycle of the Ollama background service."""
    
    @staticmethod
    def ensure_running() -> bool:
        """Checks if Ollama is running, attempts to start it if not."""
        try:
            ollama.list()
            return True
        except Exception:
            logger.info("Starting Ollama service...")
            try:
                models_path = config.LLM_SETTINGS.get("models_path")
                max_models = config.LLM_SETTINGS.get("max_loaded_models", "3")
                keep_alive = config.LLM_SETTINGS.get("keep_alive", "5m")
                
                env = os.environ.copy()
                if models_path:
                    env["OLLAMA_MODELS"] = models_path
                
                env["OLLAMA_MAX_LOADED_MODELS"] = max_models
                env["OLLAMA_KEEP_ALIVE"] = keep_alive

                subprocess.Popen(
                    ["ollama", "serve"], 
                    stdout=subprocess.DEVNULL, 
                    stderr=subprocess.DEVNULL,
                    env=env,
                    creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
                )
                
                # Wait for service to respond (up to 10 seconds)
                for _ in range(5):
                    time.sleep(2)
                    try:
                        ollama.list()
                        return True
                    except:
                        continue
                return False
            except Exception as e:
                logger.error(f"Failed to launch Ollama: {e}")
                return False

class ModelManager:
    """Handles model-specific operations like pulling/loading."""
    
    def __init__(self):
        models_path = config.LLM_SETTINGS.get("models_path")
        if models_path:
            os.environ["OLLAMA_MODELS"] = models_path

    def ensure_model_loaded(self, model_name: str) -> bool:
        """Ensures the specified model is available locally."""
        try:
            logger.info(f"Ensuring model '{model_name}' is ready...")
            ollama.pull(model_name)
            return True
        except Exception as e:
            logger.error(f"Model load failed for '{model_name}': {e}")
            return False

class LlmInferenceEngine:
    """Handles communication with Ollama for text generation."""
    
    def __init__(self, model_manager: Optional[ModelManager] = None):
        self.model_manager = model_manager or ModelManager()

    def generate_response(self, model: str, prompt: str, format: Optional[str] = None, think: bool = False) -> Optional[Dict[str, Any]]:
        """
        Generates a response from Ollama.
        Raises ServiceUnavailableError if Ollama is down.
        Raises LlmError if inference fails.
        """
        if not self.model_manager.ensure_model_loaded(model):
            raise LlmError(f"Failed to load/pull model: {model}")
            
        try:
            response = ollama.generate(model=model, prompt=prompt, format=format, think=think)
            return {
                "answer": response.get('response', '').strip(),
                "thinking": response.get('thinking', '').strip() if think else None,
                "duration": response.get('total_duration', 0) / 1e9
            }
        except ollama.ResponseError as e:
            logger.error(f"Ollama API error: {e}")
            raise LlmError(f"Ollama API error: {e}")
        except Exception as e:
            if "connection" in str(e).lower():
                raise ServiceUnavailableError("Could not connect to Ollama service.")
            logger.error(f"Unexpected inference failure: {e}")
            raise LlmError(f"Unexpected inference failure: {e}")
