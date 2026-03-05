import pytest
from unittest.mock import MagicMock, patch
from src.core.llm_engine import OllamaServiceManager

@patch('ollama.list')
def test_ensure_running_already_running(mock_list):
    """Test that it returns True if Ollama is already running."""
    mock_list.return_value = []
    assert OllamaServiceManager.ensure_running() is True
    assert OllamaServiceManager._started_by_us is False

@patch('subprocess.Popen')
@patch('ollama.list')
@patch('time.sleep')
def test_ensure_running_starts_service(mock_sleep, mock_list, mock_popen):
    """Test that it attempts to start the service if not running."""
    # First call to list() fails, subsequent calls succeed
    mock_list.side_effect = [Exception("Connection Error"), {"models": []}]
    
    # Mock subprocess
    mock_process = MagicMock()
    mock_popen.return_value = mock_process
    
    # Reset state
    OllamaServiceManager._started_by_us = False
    OllamaServiceManager._process = None
    
    assert OllamaServiceManager.ensure_running() is True
    assert OllamaServiceManager._started_by_us is True
    mock_popen.assert_called_once()

def test_shutdown_process():
    """Test that shutdown terminates the process if we started it."""
    mock_process = MagicMock()
    OllamaServiceManager._process = mock_process
    OllamaServiceManager._started_by_us = True
    
    OllamaServiceManager.shutdown()
    
    mock_process.terminate.assert_called_once()
    assert OllamaServiceManager._process is None
    assert OllamaServiceManager._started_by_us is False
