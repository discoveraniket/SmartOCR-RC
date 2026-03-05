import pytest
import sqlite3
import pandas as pd
from pathlib import Path
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.rc_processor.search_manager import SearchManager

def test_search_ration_card(tmp_path):
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(db_path)
    pd.DataFrame({
        "Ration Card No.": ["1234567890", "0987654321"],
        "Name": ["Alice", "Bob"],
        "Category": ["PHH", "AAY"]
    }).to_sql("beneficiaries", conn, index=False)
    conn.close()

    manager = SearchManager(str(db_path))
    success, msg = manager.connect()
    assert success
    
    # Test exact match
    res, count = manager.search_ration_card("1234567890")
    assert count == 1
    assert res["Name"] == "Alice"
    assert "Mobile No" in res # Mobile is randomly added

    # Test partial match
    res, count = manager.search_ration_card("098")
    assert count == 1
    assert res["Name"] == "Bob"
    
    # Test not found
    res, count = manager.search_ration_card("555")
    assert count == 0
    assert res is None
