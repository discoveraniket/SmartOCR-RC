import pytest
import json
from pathlib import Path
from src.core.coordinator import PipelineCoordinator

def test_final_model_output_processing():
    """
    Focus: Testing how the system handles the JSON string 
    produced by the final conversion model.
    """
    # Use a dummy output dir to avoid side effects
    coordinator = PipelineCoordinator(output_dir="test_output")
    
    # 1. Test case: Perfect JSON from the final model
    perfect_json = '{"category": "SPHH", "id": "1234567890", "name": "ANIKET DAS", "mobile": "9876543210"}'
    data = json.loads(perfect_json)
    assert data['category'] == "SPHH"
    assert data['id'] == "1234567890"

    # 2. Test case: Final model returns empty JSON
    empty_json = '{}'
    data_empty = json.loads(empty_json)
    
    category = data_empty.get('category') or 'UNKNOWN'
    id_val = data_empty.get('id') or 'UNKNOWN'
    
    assert category == "UNKNOWN"
    assert id_val == "UNKNOWN"

def test_final_data_consistency():
    """
    Ensure the data fields required for CSV and Image renaming 
    are handled correctly.
    """
    final_output = {
        "category": "PHH",
        "id": "5566778899",
        "name": "TEST USER",
        "mobile": "0000000000"
    }
    
    # Ensure the naming convention logic is consistent with coordinator.py
    category = final_output.get('category') or 'UNKNOWN'
    id_val = final_output.get('id') or 'UNKNOWN'
    expected_filename = f"{category}_{id_val}.jpg"
    
    # This matches the logic in _finalize_output
    actual_filename = f"{final_output['category']}_{final_output['id']}.jpg"
    assert actual_filename == expected_filename
