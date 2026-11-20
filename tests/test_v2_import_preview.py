"""Realistic relaxation upload preview and native legacy XLS acceptance.

The original instrument observations are never trimmed, sorted, normalized
or collapsed on import. Users inspect quality warnings before saving.
"""
from io import BytesIO
import hashlib

from fastapi.testclient import TestClient
import pytest
import xlwt

from can_relax.io.parser import parse_curve_records
from vitrifit2.api import app, get_store
from vitrifit2.import_adapter import import_relaxation_upload, preview_relaxation_upload
from vitrifit2.persistence import VitriFitStore


def legacy_xls_bytes() -> bytes:
    """Create actual Excel BIFF8 bytes, not a renamed CSV or XLSX file."""
    book = xlwt.Workbook()
    sheet = book.add_sheet("SRA")
    rows = [
        ["Temp", "Time (s)", "Modulus (MPa)",
         "Temp", "Time (s)", "Modulus (MPa)"],
        [100, 0.01, 3.5, 100, 0.01, 4.5],
        ["", 1, 3.0, "", 1, 4.0],
        ["", 2, 2.5, "", 2, 3.5],
    ]
    for i, row in enumerate(rows):
        for j, value in enumerate(row):
            sheet.write(i, j, value)
    output = BytesIO()
    book.save(output)
    return output.getvalue()


def test_legacy_xls_is_read_with_replicates_and_source_bytes(tmp_path):
    raw = legacy_xls_bytes()
    path = tmp_path / "VUGT-13-11.xls"
    path.write_bytes(raw)
    parsed = parse_curve_records(path)
    assert len(parsed) == 2
    assert [r["Temp"] for r in parsed] == [100, 100]
    assert [r["Curve_ID"] for r in parsed] == ["curve_001", "curve_002"]
    assert parsed[1]["Data"]["Modulus"].tolist() == [4.5, 4, 3.5]
    store = VitriFitStore(tmp_path / "research")
    sample = store.create_sample(store.create_project("VUGT"), "VUGT 13/11")
    preview = preview_relaxation_upload("VUGT-13-11.xls", raw)
    assert preview["curve_count"] == 2
    assert preview["replicates_per_temperature"] == {"100": 2}
    assert preview["saved"] is False
    assert preview["file_sha256"] == hashlib.sha256(raw).hexdigest()
    assert len(store.list_experiments(sample)) == 0
    saved = import_relaxation_upload(
        store, sample, "VUGT-13-11.xls", raw,
        metadata={"preview_sha256": preview["file_sha256"],
                  "preview_curve_count": preview["curve_count"]})
    assert len(saved["curve_ids"]) == 2
    assert store.get_original_file(saved["experiment_id"]) == raw
    for cid in saved["curve_ids"]:
        curve = store.get_curve(cid)
        assert curve["time_s"] == [0.01, 1, 2]
        assert curve["mask"] == [True, True, True]


def test_preview_warns_but_never_modifies_invalid_time_or_modulus(tmp_path):
    raw = b"Temp,Time,Modulus\n100,0,2\n,1,1\n,1,0\n,0.5,-0.1\n"
    result = preview_relaxation_upload("VUGT 100C.csv", raw)
    assert result["curve_count"] == 1
    assert result["needs_review"] is True
    quality = result["curves"][0]
    assert quality["nonpositive_modulus_points"] == 2
    assert quality["duplicate_time_steps"] == 1
    assert quality["decreasing_time_steps"] == 1
    assert quality["first_time_s"] == 0
    assert len(result["warnings"]) >= 4
    assert quality["preview_time_s"] == [0, 1, 1, .5]
    assert quality["preview_modulus_mpa"] == [2, 1, 0, -.1]
    store = VitriFitStore(tmp_path / "data")
    sample = store.create_sample(store.create_project("LCE"), "IPN")
    saved = import_relaxation_upload(store, sample, "VUGT 100C.csv", raw,
        metadata={"preview_sha256": result["file_sha256"],
                  "review_warnings_acknowledged": True})
    data = store.get_curve(saved["curve_ids"][0])
    assert data["time_s"] == [0, 1, 1, .5]
    assert data["modulus_mpa"] == [2, 1, 0, -.1]
    experiment = store.list_experiments(sample)[0]
    assert experiment["metadata"]["import_requires_review"] is True
    assert len(experiment["metadata"]["import_warnings"]) >= 4
    assert experiment["metadata"]["review_warnings_acknowledged"] is True


def test_preview_endpoint_read_only_and_sha256_validation(tmp_path):
    store = VitriFitStore(tmp_path / "data")
    app.dependency_overrides[get_store] = lambda: store
    try:
        with TestClient(app) as client:
            sample = store.create_sample(store.create_project("LCE"), "IPN")
            raw = legacy_xls_bytes()
            response = client.post("/api/import-preview",
                files={"file": ("legacy.xls", raw, "application/vnd.ms-excel")})
            assert response.status_code == 200, response.text
            preview = response.json()
            assert preview["curve_count"] == 2
            assert preview["canonical_units"] == {
                "time": "s", "modulus": "MPa", "temperature": "°C"}
            assert store.list_experiments(sample) == []
            response = client.post(
                "/api/samples/"+sample+"/experiments",
                files={"file": ("legacy.xls", raw, "application/vnd.ms-excel")},
                data={"metadata": '{"preview_sha256":"incorrect","preview_curve_count":2}'})
            assert response.status_code == 422
            assert "changed after" in response.json()["detail"]
            assert store.list_experiments(sample) == []
            response = client.post(
                "/api/samples/"+sample+"/experiments",
                files={"file": ("legacy.xls", raw, "application/vnd.ms-excel")},
                data={"metadata": (
                    '{"preview_sha256":"'+preview["file_sha256"]+'",'
                    '"preview_curve_count":2}')})
            assert response.status_code == 201, response.text
            assert len(store.list_experiments(sample)) == 1
    finally:
        app.dependency_overrides.clear()


def test_xls_fake_file_fails_with_useful_error(tmp_path):
    with pytest.raises(ValueError, match="Cannot read legacy XLS workbook"):
        preview_relaxation_upload("renamed_file.xls", b"not a real BIFF spreadsheet")
    store = VitriFitStore(tmp_path / "data")
    sample = store.create_sample(store.create_project("P"), "S")
    assert store.list_experiments(sample) == []


def test_preview_respects_canonical_units_and_replicates(tmp_path):
    raw = (
        b"Temp (C),Time (min),Modulus (kPa),Temp (C),Time (min),Modulus (kPa)\n"
        b"80,1,1000,80,1,1200\n"
        b"80,2,500,80,2,700\n"
    )
    preview = preview_relaxation_upload("replicates.csv", raw)
    assert preview["replicates_per_temperature"] == {"80": 2}
    assert preview["curves"][0]["first_time_s"] == 60
    assert preview["curves"][0]["first_modulus_mpa"] == 1.0
    assert preview["curves"][1]["first_modulus_mpa"] == 1.2
    assert preview["saved"] is False
