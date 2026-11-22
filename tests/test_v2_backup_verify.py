"""Read-only backup validation regressions."""
import io
import json
import zipfile

import pytest

from vitrifit2.backup_verify import verify_backup_bytes
from vitrifit2.persistence import VitriFitStore
from vitrifit2.sample_profile import (
    create_specimen, create_measurement, attach_measurement_file,
)


def test_verify_backup_with_sample_profile(tmp_path):
    store = VitriFitStore(tmp_path / "data")
    sample = store.create_sample(store.create_project("P"), "S")
    specimen = create_specimen(store, sample, "film")
    measurement = create_measurement(store, specimen, "DSC", "calorimetry")
    attach_measurement_file(store, measurement, "dsc.csv", b"T,heat\n1,2\n3,4\n")
    status = verify_backup_bytes(store.export_backup_bytes())
    assert status["status"] == "verified"
    assert status["raw_blob_count"] == 1
    assert status["database_integrity"] == "ok"


def test_verify_rejects_missing_raw_blob(tmp_path):
    store = VitriFitStore(tmp_path)
    sample = store.create_sample(store.create_project("P"), "S")
    specimen = create_specimen(store, sample, "film")
    measurement = create_measurement(store, specimen, "DSC", "calorimetry")
    attach_measurement_file(store, measurement, "raw.csv", b"abc")
    original = store.export_backup_bytes()
    output = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(original)) as src, zipfile.ZipFile(output, "w") as dst:
        for item in src.namelist():
            if not item.startswith("raw_blobs/"):
                dst.writestr(item, src.read(item))
    with pytest.raises(ValueError, match="unexpected or missing"):
        verify_backup_bytes(output.getvalue())


def test_verify_rejects_unknown_entries(tmp_path):
    store = VitriFitStore(tmp_path)
    original = store.export_backup_bytes()
    output = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(original)) as src, zipfile.ZipFile(output, "w") as dst:
        for item in src.namelist():
            dst.writestr(item, src.read(item))
        dst.writestr("../escape", b"unsafe")
    with pytest.raises(ValueError, match="unexpected or missing"):
        verify_backup_bytes(output.getvalue())


def test_verify_rejects_bad_archive():
    with pytest.raises(ValueError):
        verify_backup_bytes(b"not a ZIP")


def test_verify_rejects_invalid_sqlite_snapshot():
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, "w") as archive:
        archive.writestr("manifest.json", json.dumps({
            "format": "vitrifit2-backup-v2", "original_file_hashes": []}))
        archive.writestr("vitrifit.sqlite3", b"not a sqlite database")
    with pytest.raises(ValueError, match="Invalid or incomplete"):
        verify_backup_bytes(payload.getvalue())


@pytest.mark.parametrize("manifest", [[], None, "not an object", 42])
def test_verify_rejects_non_object_manifest_with_clear_error(manifest):
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, "w") as archive:
        archive.writestr("manifest.json", json.dumps(manifest))
        archive.writestr("vitrifit.sqlite3", b"placeholder")
    with pytest.raises(ValueError, match="manifest must be a JSON object"):
        verify_backup_bytes(payload.getvalue())
