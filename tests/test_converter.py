import pytest
from pathlib import Path
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.rc_processor.converter import BeneficiaryConverter

def test_convert_directory(tmp_path):
    # Create mock HTML files
    html1 = tmp_path / "dealer1.html"
    html1.write_text('''
    <html><body>
    <table class="mGrid">
        <tr><th>ID</th><th>Name</th></tr>
        <tr><td>1</td><td>Alice</td></tr>
        <tr><td>2</td><td>Bob</td></tr>
    </table>
    </body></html>
    ''', encoding='utf-8')

    out_csv = tmp_path / "out.csv"
    converter = BeneficiaryConverter()
    success, msg = converter.convert_directory(str(tmp_path), str(out_csv))

    assert success
    assert out_csv.exists()
    
    content = out_csv.read_text(encoding='utf-8')
    assert "Source File,ID,Name" in content
    assert "dealer1,1,Alice" in content
