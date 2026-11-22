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


@pytest.mark.parametrize("hashes", [[[]], [{"sha": "bad"}], [None], [123]])
def test_verify_rejects_unhashable_or_non_string_hash_entries(hashes):
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, "w") as archive:
        archive.writestr("manifest.json", json.dumps({
            "format": "vitrifit2-backup-v2", "original_file_hashes": hashes}))
        archive.writestr("vitrifit.sqlite3", b"placeholder")
    with pytest.raises(ValueError, match="Invalid SHA256 identifier"):
        verify_backup_bytes(payload.getvalue())


def test_verified_backup_round_trip_preserves_specimen_file_bytes(tmp_path):
    """Exercise documented offline restore in an isolated empty workspace."""
    source = VitriFitStore(tmp_path / "source")
    project = source.create_project("LCE IPN")
    sample = source.create_sample(project, "LCE2")
    specimen = create_specimen(source, sample, "film A")
    measurement = create_measurement(source, specimen, "DSC", "calorimetry")
    original = b"temperature_C,heat_flow_mW\\n20,0.1\\n30,0.2\\n"
    file_id = attach_measurement_file(source, measurement, "lce2.csv", original)
    backup = source.export_backup_bytes()
    assert verify_backup_bytes(backup)["status"] == "verified"

    restored_dir = tmp_path / "restored"
    restored_dir.mkdir()
    # Never extract arbitrary ZIP paths: copy only verifier-approved names.
    with zipfile.ZipFile(io.BytesIO(backup)) as archive:
        for name in archive.namelist():
            destination = restored_dir / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(archive.read(name))
    restored = VitriFitStore(restored_dir)
    from vitrifit2.sample_profile import get_measurement_file, list_measurement_files
    assert restored.list_projects() == source.list_projects()
    assert restored.list_samples(project) == source.list_samples(project)
    assert list_measurement_files(restored, measurement) == list_measurement_files(source, measurement)
    assert get_measurement_file(restored, file_id) == original
    assert verify_backup_bytes(restored.export_backup_bytes())["status"] == "verified"
