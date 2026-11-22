"""Regression checks for strict CSV validation across all sample techniques."""
import pytest

from vitrifit2.rheology_workflow import _parse_columns


@pytest.mark.parametrize("raw, mapping, message", [
    (b"a,b\n1,NaN\n2,3\n", {"x": "a", "y": "b"}, "NaN"),
    (b"a,b\n1,inf\n2,3\n", {"x": "a", "y": "b"}, "NaN"),
    (b"a,b\n1,2\n3,4\n", {"x": "a", "y": "a"}, "(?i:duplicate|missing)"),
    (b"a,a\n1,2\n", {"x": "a"}, "duplicate"),
    (b"a,b\n1,2,3\n", {"x": "a", "y": "b"}, "more fields"),
    (b"a,b\n1,hello\n", {"x": "a", "y": "b"}, "Non-numeric"),
])
def test_reject_ambiguous_or_invalid_csv(raw, mapping, message):
    with pytest.raises(ValueError, match=message):
        _parse_columns(raw, mapping)


def test_preserves_original_csv_row_order():
    data = _parse_columns(
        b"T,Ep\n30,100\n20,200\n40,300\n",
        {"temperature_c": "T", "storage_modulus": "Ep"})
    assert data["temperature_c"] == [30, 20, 40]
    assert data["storage_modulus"] == [100, 200, 300]


def test_invalid_mapping_type_rejected():
    with pytest.raises(ValueError):
        _parse_columns(b"x\n1\n", ["x"])
