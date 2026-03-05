import os
import time
import logging
import subprocess
import atexit
from src.utils import config
from typing import Optional, Dict, Any
from src.core.exceptions import ServiceUnavailableError, LlmError

logger = logging.getLogger(__name__)

class OllamaServiceManager:
    """Handles the lifecycle of the Ollama background service."""
    
    _process: Optional[subprocess.Popen] = None
    _started_by_us: bool = False

    @classmethod
    def ensure_running(cls) -> bool:
        """Checks if Ollama is running, attempts to start it if not."""
        try:
            import ollama
            ollama.list()
            return True
        except ImportError:
            logger.error("Ollama library not found. Please install it using 'pip install ollama'.")
            return False
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

                # Use CREATE_NO_WINDOW (0x08000000) to hide the terminal on Windows
                CREATE_NO_WINDOW = 0x08000000
                cls._process = subprocess.Popen(
                    ["ollama", "serve"], 
                    stdout=subprocess.DEVNULL, 
                    stderr=subprocess.DEVNULL,
                    env=env,
                    creationflags=CREATE_NO_WINDOW if os.name == 'nt' else 0
                )
                cls._started_by_us = True
                
                # Register shutdown hook
                atexit.register(cls.shutdown)
                
                # Wait for service to respond (up to 10 seconds)
                import ollama
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
                
    @classmethod
    def shutdown(cls):
        """Terminates the Ollama process if it was started by this application."""
        if cls._started_by_us and cls._process:
            logger.info("Shutting down the managed Ollama service...")
            try:
                cls._process.terminate()
                cls._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning("Ollama service did not terminate gracefully. Forcing kill.")
                cls._process.kill()
            except Exception as e:
                logger.error(f"Error while shutting down Ollama: {e}")
            finally:
                cls._process = None
                cls._started_by_us = False

class ModelManager:
    """Handles model-specific operations like pulling/loading."""
    
    def __init__(self):
        models_path = config.LLM_SETTINGS.get("models_path")
        if models_path:
            os.environ["OLLAMA_MODELS"] = models_path

    def ensure_model_loaded(self, model_name: str) -> bool:
        """Ensures the specified model is available locally. Checks local list first."""
        try:
            import ollama
            
            # Check if model already exists locally
            local_models = ollama.list()
            # ollama.list() returns an object where .models is a list of model objects
            # Each model object has a 'model' attribute (name:tag)
            model_exists = any(m.get('model') == model_name or m.get('name') == model_name for m in local_models.get('models', []))
            
            if model_exists:
                return True
                
            logger.warning(f"Model '{model_name}' not found locally.")
            return False
        except ImportError:
            logger.error("Ollama library not found.")
            return False
        except Exception as e:
            logger.error(f"Error checking local models: {e}")
            return False

    def pull_model(self, model_name: str) -> bool:
        """Explicitly pulls a model from the registry."""
        try:
            import ollama
            logger.info(f"Pulling model '{model_name}'...")
            ollama.pull(model_name)
            return True
        except Exception as e:
            logger.error(f"Model pull failed for '{model_name}': {e}")
            return False

class LlmInferenceEngine:
    """Handles communication with Ollama for text generation."""
    
    def __init__(self, model_manager: Optional[ModelManager] = None):
        self.model_manager = model_manager or ModelManager()

    def is_ready(self) -> bool:
        """Checks if the LLM engine (Ollama) is accessible."""
        return OllamaServiceManager.ensure_running()

    def generate_response(self, model: str, prompt: str, format: Optional[str] = None, think: bool = False) -> Optional[Dict[str, Any]]:
        """
        Generates a response from Ollama.
        Raises ServiceUnavailableError if Ollama is down.
        Raises LlmError if inference fails.
        """
        try:
            import ollama
        except ImportError:
            raise LlmError("Ollama library not installed.")

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
