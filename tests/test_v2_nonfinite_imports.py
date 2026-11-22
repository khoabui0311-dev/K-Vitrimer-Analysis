"""Reject nonfinite CSV data before immutable raw-file attachment."""
import pytest

from vitrifit2.persistence import VitriFitStore
from vitrifit2.sample_profile import create_specimen, create_measurement
from vitrifit2.tensile_workflow import import_tensile_csv
from vitrifit2.thermal_workflow import import_thermal_csv


@pytest.mark.parametrize("bad_value", ["NaN", "inf", "-inf"])
def test_tensile_nonfinite_does_not_attach(tmp_path, bad_value):
    store = VitriFitStore(tmp_path)
    sample = store.create_sample(store.create_project("P"), "S")
    specimen = create_specimen(store, sample, "film")
    mid = create_measurement(store, specimen, "Tensile", "tensile_test")
    raw = f"extension,load\n0,0\n.01,1\n.02,{bad_value}\n.03,3\n".encode()
    with pytest.raises(ValueError, match="NaN or infinite"):
        import_tensile_csv(
            store, mid, "bad.csv", raw,
            columns={"displacement_mm": "extension", "force_n": "load"},
            gauge_length_mm=10, width_mm=2, thickness_mm=1)
    assert list(store.blobs.iterdir()) == []


def test_dma_nonfinite_does_not_attach(tmp_path):
    store = VitriFitStore(tmp_path)
    sample = store.create_sample(store.create_project("P"), "S")
    specimen = create_specimen(store, sample, "film")
    mid = create_measurement(store, specimen, "DMA", "temperature_ramp")
    raw = b"T,Ep,Epp\n20,100,10\n30,NaN,11\n40,80,12\n50,70,13\n"
    with pytest.raises(ValueError, match="NaN or infinite"):
        import_thermal_csv(
            store, mid, "bad.csv", raw, method="temperature_ramp",
            columns={"temperature_c": "T", "storage_modulus": "Ep",
                     "loss_modulus": "Epp"})
    assert list(store.blobs.iterdir()) == []
