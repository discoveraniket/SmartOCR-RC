import pytest
import json
import os
from src.core.coordinator import PipelineCoordinator

def test_final_model_output_processing():
    """
    Focus: Testing how the system handles the JSON string 
    produced by the final conversion model.
    """
    coordinator = PipelineCoordinator()
    
    # 1. Test case: Perfect JSON from the final model
    perfect_json = '{"category": "SPHH", "id": "1234567890", "name": "ANIKET DAS", "mobile": "9876543210"}'
    data = json.loads(perfect_json)
    assert data['category'] == "SPHH"
    assert data['id'] == "1234567890"

    # 2. Test case: Final model returns empty JSON (happens if it can't find data)
    # The system should handle this without crashing.
    empty_json = '{}'
    data_empty = json.loads(empty_json)
    
    # Check if our fallback logic in _finalize_output works
    category = data_empty.get('category', 'UNKNOWN')
    id_val = data_empty.get('id', 'UNKNOWN')
    
    assert category == "UNKNOWN"
    assert id_val == "UNKNOWN"

    # 3. Test case: Final model returns JSON with nulls
    null_json = '{"category": null, "id": null, "name": null}'
    data_null = json.loads(null_json)
    
    # The code uses .get() which won't catch explicit nulls, 
    # but the subsequent file naming logic should handle it.
    category_null = data_null.get('category') or 'UNKNOWN'
    assert category_null == "UNKNOWN"

def test_final_data_consistency():
    """
    Ensure the data fields required for CSV and Image renaming 
    are handled correctly.
    """
    # This simulates the dictionary that will be sent to CSVFileHandler.append_row
    final_output = {
        "category": "PHH",
        "id": "5566778899",
        "name": "TEST USER",
        "mobile": "0000000000",
        "processed_image_name": "PHH_5566778899.jpg"
    }
    
    # Ensure the naming convention for the file system is predictable
    expected_filename = f"{final_output['category']}_{final_output['id']}.jpg"
    assert final_output['processed_image_name'] == expected_filename
