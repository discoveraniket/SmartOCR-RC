import pytest
import os
import csv
from src.core.result_handler import ResultDataHandler

@pytest.fixture
def dummy_csv(tmp_path):
    csv_path = tmp_path / "results.csv"
    with open(csv_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=["processed_image_name", "category", "id"])
        writer.writeheader()
        writer.writerow({"processed_image_name": "IMG1.jpg", "category": "PHH", "id": "1"})
        writer.writerow({"processed_image_name": "IMG2.jpg", "category": "AAY", "id": "2"})
    return str(csv_path), str(tmp_path)

def test_load_results(dummy_csv):
    csv_path, output_dir = dummy_csv
    handler = ResultDataHandler(csv_path, output_dir)
    assert len(handler.results) == 2
    assert handler.current_index == 0
    assert handler.get_current_item()['id'] == "1"

def test_next_prev_item(dummy_csv):
    csv_path, output_dir = dummy_csv
    handler = ResultDataHandler(csv_path, output_dir)
    assert handler.next_item() is True
    assert handler.current_index == 1
    assert handler.next_item() is False
    assert handler.prev_item() is True
    assert handler.current_index == 0

def test_save_edit(dummy_csv):
    csv_path, output_dir = dummy_csv
    handler = ResultDataHandler(csv_path, output_dir)
    handler.save_edit(0, {"category": "UPDATED"})
    
    # Reload and verify
    handler2 = ResultDataHandler(csv_path, output_dir)
    assert handler2.results[0]['category'] == "UPDATED"

def test_delete_item(dummy_csv):
    csv_path, output_dir = dummy_csv
    handler = ResultDataHandler(csv_path, output_dir)
    assert handler.delete_item(0) is True
    assert len(handler.results) == 1
    assert handler.results[0]['id'] == "2"

def test_rename_files_mock(dummy_csv, tmp_path):
    csv_path, output_dir = dummy_csv
    img_path = tmp_path / "IMG1.jpg"
    img_path.write_text("dummy image")
    
    handler = ResultDataHandler(csv_path, output_dir)
    new_name = handler.rename_item_files(0, "NEW_CAT", "99")
    
    assert new_name == "NEW_CAT_99.jpg"
    assert (tmp_path / "NEW_CAT_99.jpg").exists()
    assert not (tmp_path / "IMG1.jpg").exists()
    assert handler.results[0]['processed_image_name'] == "NEW_CAT_99.jpg"
