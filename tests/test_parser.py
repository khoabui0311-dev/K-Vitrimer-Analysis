import pytest
import pandas as pd
import tempfile
import os
from can_relax.io.parser import parse_wide_format_data

def test_parse_wide_format_data_csv():
    # Create temporary CSV with wide format
    csv_content = "Temp_A,Time_A,Modulus_A,Temp_B,Time_B,Modulus_B\n100,0.1,1000,120,0.1,800\n100,1.0,500,120,1.0,300"
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as tmp:
        tmp.write(csv_content)
        tmp_path = tmp.name

    try:
        curves = parse_wide_format_data(tmp_path)

        assert 100.0 in curves
        assert 120.0 in curves
        
        df_100 = curves[100.0]
        assert len(df_100) == 2
        assert list(df_100['Time']) == [0.1, 1.0]
        assert list(df_100['Modulus']) == [1000.0, 500.0]
    finally:
        os.unlink(tmp_path)
