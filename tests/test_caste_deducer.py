import pytest
import pandas as pd
from pathlib import Path
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.rc_processor.caste_deducer import DataEnricher

def test_caste_deduction(tmp_path):
    # Create mock DB
    db_path = tmp_path / "castedb.csv"
    pd.DataFrame({
        "LAST NAME": ["GHOSH", "ANSARI", "MAHATO"],
        "CASTE": ["OBC-B", "OBC-A", "OBC-B"]
    }).to_csv(db_path, index=False)

    # Create mock data
    data_path = tmp_path / "data.csv"
    pd.DataFrame({
        "Name": ["John GHOSH", "Ali ANSARI", "Ram MAHATO", "Unknown SMITH"]
    }).to_csv(data_path, index=False)

    out_path = tmp_path / "out.csv"

    enricher = DataEnricher()
    caste_config = {'db_path': str(db_path), 'name_col': 'Name'}
    
    success, msg = enricher.enrich_data(str(data_path), str(out_path), caste_config=caste_config)
    
    assert success
    assert out_path.exists()
    
    df_out = pd.read_csv(out_path)
    assert df_out.iloc[0]["Deducted_Caste"] == "OBC-B"
    assert df_out.iloc[1]["Deducted_Caste"] == "OBC-A"
    assert df_out.iloc[2]["Deducted_Caste"] == "OBC-B"
    assert df_out.iloc[3]["Deducted_Caste"] == "GEN" # default

def test_dealer_mapping(tmp_path):
    # Create mock dealer DB
    db_path = tmp_path / "dealers.csv"
    pd.DataFrame({
        "Code": ["1001", "1002"],
        "Name": ["Dealer A", "Dealer B"]
    }).to_csv(db_path, index=False)

    # Create mock data
    data_path = tmp_path / "data.csv"
    pd.DataFrame({
        "DealerCode": ["1001", "1002", "1003"]
    }).to_csv(data_path, index=False)

    out_path = tmp_path / "out.csv"

    enricher = DataEnricher()
    dealer_config = {
        'db_path': str(db_path), 
        'data_code_col': 'DealerCode',
        'db_code_col': 'Code',
        'db_name_col': 'Name'
    }
    
    success, msg = enricher.enrich_data(str(data_path), str(out_path), dealer_config=dealer_config)
    
    assert success
    df_out = pd.read_csv(out_path)
    assert df_out.iloc[0]["Dealer_Name_Mapped"] == "Dealer A"
    assert df_out.iloc[1]["Dealer_Name_Mapped"] == "Dealer B"
    assert df_out.iloc[2]["Dealer_Name_Mapped"] == "Unknown Dealer"
