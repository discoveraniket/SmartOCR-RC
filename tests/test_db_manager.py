import pytest
import pandas as pd
import sqlite3
from pathlib import Path
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.rc_processor.db_manager import DatabaseManager

def test_convert_csv_to_sqlite(tmp_path):
    csv_path = tmp_path / "data.csv"
    pd.DataFrame({
        "Ration Card No.": ["0001234567", "0009876543"],
        "Name": ["Alice", "Bob"]
    }).to_csv(csv_path, index=False)

    db_path = tmp_path / "test.db"
    
    manager = DatabaseManager()
    success, msg = manager.convert_csv_to_sqlite(str(csv_path), str(db_path), "beneficiaries")
    
    assert success
    assert db_path.exists()
    
    conn = sqlite3.connect(db_path)
    df = pd.read_sql("SELECT * FROM beneficiaries", conn)
    conn.close()
    
    assert len(df) == 2
    assert df.iloc[0]["Ration Card No."] == "0001234567" # string preservation
