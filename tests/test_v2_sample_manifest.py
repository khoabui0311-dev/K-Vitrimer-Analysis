"""Cross-technique provenance export and integrity regressions."""
import hashlib
import json

import pytest

from vitrifit2.persistence import VitriFitStore
from vitrifit2.sample_profile import create_measurement, create_specimen
from vitrifit2.thermal_workflow import import_thermal_csv
from vitrifit2.tensile_workflow import import_tensile_csv
from vitrifit2.sample_manifest import export_sample_analysis_manifest


def test_unified_manifest_across_techniques(tmp_path):
    store = VitriFitStore(tmp_path)
    sample = store.create_sample(store.create_project("Project"), "LCE2")
    specimen = create_specimen(store, sample, "film", {"batch": "B1"})
    dma = create_measurement(
        store, specimen, "DMA", "temperature_ramp",
        {"frequency_hz": 1, "heating_rate_c_min": 3})
    tensile = create_measurement(store, specimen, "Tensile", "tensile_test")
    dma_raw = b"T,Ep,Epp\n20,1000,100\n30,900,180\n40,700,350\n50,500,100\n60,400,40\n"
    aid_dma = import_thermal_csv(
        store, dma, "dma.csv", dma_raw, method="temperature_ramp",
        columns={"temperature_c": "T", "storage_modulus": "Ep",
                 "loss_modulus": "Epp"}, modulus_unit="MPa")
    tensile_raw = b"x,F\n0,0\n.01,1\n.02,2\n.03,3\n.04,4\n.05,5\n"
    aid_tensile = import_tensile_csv(
        store, tensile, "tensile.csv", tensile_raw,
        columns={"displacement_mm": "x", "force_n": "F"},
        gauge_length_mm=10, width_mm=2, thickness_mm=1)
    manifest = json.loads(export_sample_analysis_manifest(
        store, [aid_dma, aid_tensile], include_results=False))
    assert manifest["source_integrity_verified"]
    assert not manifest["contains_raw_bytes"]
    assert {a["technique"] for a in manifest["analyses"]} == {"DMA", "Tensile"}
    assert all("results" not in a for a in manifest["analyses"])
    assert manifest["analyses"][0]["source_sha256"] == hashlib.sha256(dma_raw).hexdigest()
    assert manifest["analyses"][0]["specimen_metadata"]["batch"] == "B1"
    with pytest.raises(ValueError, match="Duplicate"):
        export_sample_analysis_manifest(store, [aid_dma, aid_dma])
    (store.blobs / hashlib.sha256(dma_raw).hexdigest()).write_bytes(b"tampered")
    with pytest.raises(IOError):
        export_sample_analysis_manifest(store, [aid_dma])
