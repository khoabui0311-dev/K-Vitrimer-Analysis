import pytest
import pandas as pd
import tempfile
import os
from can_relax.io.parser import parse_wide_format_data, parse_curve_records

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


def _csv(tmp_path, text):
    path = tmp_path / "curves.csv"
    path.write_text(text, encoding="utf-8")
    return path


@pytest.mark.parametrize("suffix", [".csv", ".xlsx"])
def test_documented_pair_headers_preserve_replicates_and_signed_temperatures(tmp_path, suffix):
    rows = [["-20 °C", None, -20, None, -20.5, None],
            ["Time", "Modulus"] * 3,
            [0, 2, 0, 3, 0, 4], [1, 1, 2, 1, 3, 1]]
    path = tmp_path / ("curves" + suffix)
    df = pd.DataFrame(rows)
    if suffix == ".xlsx":
        df.to_excel(path, header=False, index=False)
    else:
        df.to_csv(path, header=False, index=False)
    records = parse_curve_records(path)
    assert [r["Temp"] for r in records] == [-20., -20., -20.5]
    assert len({r["Curve_ID"] for r in records}) == 3
    assert records[1]["Data"]["Modulus"].tolist() == [3., 1.]
    with pytest.raises(ValueError, match="Duplicate temperature"):
        parse_wide_format_data(path)


def test_triplet_unit_conversion_and_signed_integer(tmp_path):
    path = _csv(tmp_path, "Temp (°C),Time (min),Modulus (Pa)\n-20,0.5,1500000\n-20,1,500000")
    curve = parse_curve_records(path)[0]
    assert curve["Temp"] == -20
    assert curve["Data"]["Time"].tolist() == [30., 60.]
    assert curve["Data"]["Modulus"].tolist() == [1.5, .5]


def test_quantity_suffixes_and_ragged_curve_lengths(tmp_path):
    path = _csv(tmp_path, "Temp_A,Time_A,Modulus_A,Temp_B,Time_B,Modulus_B\n"
                "-20.5 C,1 min,1000 kPa,120,1 s,1 MPa\n-20.5 C,2 min,500 kPa,,,")
    records = parse_curve_records(path)
    assert records[0]["Data"].to_numpy().tolist() == [[60., 1.], [120., .5]]
    assert len(records[1]["Data"]) == 1


@pytest.mark.parametrize("header,rows,match", [
    ("Temp,Time,Modulus", "100,0,1\n101,1,.5", "constant"),
    ("Temp,Time,Modulus", "100,0,1\n100,1,", "incomplete"),
    ("Temp,Time (hours),Modulus", "100,0,1", "Unsupported time unit"),
    ("Temp (K),Time,Modulus", "373,0,1", "Unsupported temp unit"),
    ("Temp,Time,Modulus", "100,0,2 psi", "Unsupported mod unit"),
    ("Temp,Time,Modulus", "100,nope,1", "Invalid time"),
    ("Temp,Time,Modulus (MPa)", "100,0,1000 Pa", "Conflicting mod units"),
    ("Temp,Time,Modulus", "-274,0,1", "absolute zero"),
])
def test_invalid_input_fails_explicitly(tmp_path, header, rows, match):
    with pytest.raises(ValueError, match=match):
        parse_curve_records(_csv(tmp_path, header + "\n" + rows))


def test_duplicate_triplet_headers_preserve_both_curves(tmp_path):
    path = _csv(tmp_path, "Temp,Time,Modulus,Temp,Time,Modulus\n100,0,1,100,0,2")
    records = parse_curve_records(path)
    assert len(records) == 2
    assert [r["Data"]["Modulus"].iloc[0] for r in records] == [1., 2.]


def test_underscore_unit_suffixes_are_converted(tmp_path):
    path = _csv(tmp_path, "Temp_C,Time_min,Modulus_kPa\n100,1,1000")
    data = parse_curve_records(path)[0]["Data"]
    assert data.to_numpy().tolist() == [[60., 1.]]


@pytest.mark.parametrize('suffix', ['.csv', '.xlsx'])
def test_sparse_temperature_and_temperature_only_padding(tmp_path, suffix):
    rows = [['Temp', 'Time', 'Modulus', 'Temp', 'Time', 'Modulus'],
            [100, 0, 2, 120, 0, 3],
            [None, 1, 1, 120, None, None],
            [' ', 2, .5, 120, ' ', ' ']]
    path = tmp_path / ('sparse' + suffix)
    frame = pd.DataFrame(rows)
    if suffix == '.xlsx':
        frame.to_excel(path, header=False, index=False)
    else:
        frame.to_csv(path, header=False, index=False)
    records = parse_curve_records(path)
    assert [r['Temp'] for r in records] == [100, 120]
    assert [len(r['Data']) for r in records] == [3, 1]
    assert records[0]['Data']['Modulus'].tolist() == [2, 1, .5]


def test_sparse_temperature_still_rejects_conflicts_and_missing_metadata(tmp_path):
    with pytest.raises(ValueError, match='constant'):
        parse_curve_records(_csv(tmp_path, 'Temp,Time,Modulus\n100,0,2\n,1,1\n120,2,.5'))
    with pytest.raises(ValueError, match='missing temperature'):
        parse_curve_records(_csv(tmp_path, 'Temp,Time,Modulus\n,0,2\n,1,1'))


def test_incomplete_pair_reports_actual_file_row(tmp_path):
    with pytest.raises(ValueError, match=r'file row\(s\) 4'):
        parse_curve_records(_csv(tmp_path, '100,\nTime,Modulus\n0,2\n1,'))


def test_leading_time_only_acquisition_rows_are_reported(tmp_path):
    record = parse_curve_records(_csv(tmp_path,
        'Temperature,Modulus,Step time\n120,,.167\n120,141.54,.500\n120,140.99,.834'))[0]
    assert record['Data']['Time'].tolist() == [.5, .834]
    assert record['Data']['Modulus'].tolist() == [141.54, 140.99]
    assert 'row(s) 2' in record['Import_Warnings'][0]


@pytest.mark.parametrize('rows', ['100,,2\n100,1,1', '100,0,2\n100,1,\n100,2,1', '100,0,\n100,1,'])
def test_other_partial_observations_remain_errors(tmp_path, rows):
    with pytest.raises(ValueError, match='incomplete'):
        parse_curve_records(_csv(tmp_path, 'Temp,Time,Modulus\n' + rows))
