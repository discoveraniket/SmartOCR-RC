import pytest
from unittest.mock import MagicMock, patch
from src.core.llm_engine import LlmInferenceEngine

@patch('src.core.llm_engine.ModelManager.ensure_model_loaded')
@patch('ollama.generate')
@patch('ollama.pull')
def test_generate_response_success(mock_pull, mock_generate, mock_ensure):
    """Test successful LLM response parsing and duration conversion."""
    # Setup mock
    mock_ensure.return_value = True
    mock_generate.return_value = {
        'response': ' Cleaned Text ',
        'thinking': ' Thinking process ',
        'total_duration': 5000000000  # 5 seconds in nanoseconds
    }
    
    engine = LlmInferenceEngine()
    result = engine.generate_response("test-model", "test-prompt", think=True)
    
    assert result is not None
    assert result['answer'] == "Cleaned Text"
    assert result['thinking'] == "Thinking process"
    assert result['duration'] == 5.0

@patch('ollama.generate')
@patch('ollama.pull')
def test_generate_response_failure(mock_pull, mock_generate):
    """Test engine handling of Ollama failures."""
    from src.core.exceptions import LlmError
    mock_generate.side_effect = Exception("Ollama Down")
    
    engine = LlmInferenceEngine()
    with pytest.raises(LlmError):
        engine.generate_response("test-model", "test-prompt")
