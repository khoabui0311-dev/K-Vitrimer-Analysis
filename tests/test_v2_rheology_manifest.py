"""Regression tests for portable analysis provenance manifests."""
import hashlib
import json

import pytest

from vitrifit2.persistence import VitriFitStore
from vitrifit2.sample_profile import create_measurement, create_specimen
from vitrifit2.rheology_workflow import analyze_rheology_csv
from vitrifit2.rheology_manifest import (
    build_rheology_manifest, export_rheology_manifest_json,
)


def test_manifest_roundtrip_and_raw_integrity(tmp_path):
    store = VitriFitStore(tmp_path)
    sample = store.create_sample(store.create_project("P"), "VUGT")
    specimen = create_specimen(store, sample, "disc-1")
    measurement = create_measurement(
        store, specimen, "Rheology", "frequency_sweep",
        {"temperature_c": 40, "geometry_id": "plate"})
    raw = b"f,Gp,Gpp\n1,1000,200\n10,1200,300\n"
    aid = analyze_rheology_csv(
        store, measurement, "raw.csv", raw, method="frequency_sweep",
        columns={"frequency": "f", "storage_modulus": "Gp",
                 "loss_modulus": "Gpp"})
    exported = export_rheology_manifest_json(VitriFitStore(tmp_path), [aid])
    manifest = json.loads(exported)
    entry = manifest["analyses"][0]
    assert entry["sample_id"] == sample
    assert entry["specimen_id"] == specimen
    assert entry["measurement_conditions"]["temperature_c"] == 40
    assert entry["raw_file_sha256"] == hashlib.sha256(raw).hexdigest()
    assert entry["raw_file_byte_count"] == len(raw)
    assert entry["results"]["tan_delta"] == pytest.approx([.2, .25])
    assert manifest["raw_files_embedded"] is False
    summary = build_rheology_manifest(store, [aid], include_results=False)
    assert "results" not in summary["analyses"][0]


def test_manifest_rejects_duplicate_and_missing_analysis_ids(tmp_path):
    store = VitriFitStore(tmp_path)
    with pytest.raises(ValueError):
        build_rheology_manifest(store, [])
    with pytest.raises(ValueError):
        build_rheology_manifest(store, ["a", "a"])
    with pytest.raises(KeyError):
        build_rheology_manifest(store, ["unknown"])
