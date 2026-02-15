class AppError(Exception):
    """Base exception for the application."""
    pass

class ServiceUnavailableError(AppError):
    """Raised when a required service (like Ollama) is not available."""
    pass

class OcrError(AppError):
    """Raised when OCR processing fails."""
    pass

class LlmError(AppError):
    """Raised when LLM inference fails."""
    pass

class ConfigurationError(AppError):
    """Raised when there is an issue with the application configuration."""
    pass
