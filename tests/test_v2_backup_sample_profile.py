"""Backup completeness tests: no new specimen raw files may be omitted."""
import hashlib
import io
import json
import zipfile

import pytest

from vitrifit2.persistence import VitriFitStore
from vitrifit2.sample_profile import (
    attach_measurement_file, create_measurement, create_specimen,
)


def test_backup_includes_legacy_and_sample_centric_raw_bytes(tmp_path):
    store = VitriFitStore(tmp_path / "workspace")
    sample = store.create_sample(store.create_project("LCE"), "LCE2")
    legacy = b"legacy relaxation source"
    store.import_experiment(sample, "relax.csv", legacy, [
        {"source_curve_id": "70C", "temperature_c": 70,
         "time_s": [.01, 1, 2], "modulus_mpa": [1, .8, .6]}])
    specimen = create_specimen(store, sample, "film-1")
    measurement = create_measurement(store, specimen, "DSC", "calorimetry")
    thermal = b"T,heat\n20,1\n30,2\n40,3\n50,4\n"
    attach_measurement_file(store, measurement, "dsc.csv", thermal)
    # Same blob may be referenced by multiple measurements: ZIP should contain
    # one copy and preserve both DB attachment rows.
    duplicate = create_measurement(store, specimen, "DMA", "temperature_ramp")
    attach_measurement_file(store, duplicate, "copy.csv", thermal)
    with zipfile.ZipFile(io.BytesIO(store.export_backup_bytes())) as archive:
        entries = archive.namelist()
        hashes = [hashlib.sha256(payload).hexdigest() for payload in (legacy, thermal)]
        assert archive.read("manifest.json")
        manifest = json.loads(archive.read("manifest.json"))
        assert manifest["format"] == "vitrifit2-backup-v2"
        assert sorted(manifest["original_file_hashes"]) == sorted(hashes)
        for payload, digest in zip((legacy, thermal), hashes):
            assert archive.read("raw_blobs/" + digest) == payload
            assert entries.count("raw_blobs/" + digest) == 1
        assert "vitrifit.sqlite3" in entries


def test_backup_refuses_corrupt_sample_centric_blob(tmp_path):
    store = VitriFitStore(tmp_path / "workspace")
    sample = store.create_sample(store.create_project("P"), "S")
    specimen = create_specimen(store, sample, "film")
    measurement = create_measurement(store, specimen, "DSC", "calorimetry")
    raw = b"original raw"
    attach_measurement_file(store, measurement, "dsc.csv", raw)
    (store.blobs / hashlib.sha256(raw).hexdigest()).write_bytes(b"tampered")
    with pytest.raises(IOError, match="Corrupt or missing"):
        store.export_backup_bytes()
