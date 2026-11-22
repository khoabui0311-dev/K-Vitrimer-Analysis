"""Validate measurement metadata before creating an irreversible audit record."""
import pytest

from vitrifit2.persistence import VitriFitStore
from vitrifit2.sample_profile import create_measurement, create_specimen, get_sample_profile


@pytest.fixture
def specimen_context(tmp_path):
    store = VitriFitStore(tmp_path)
    project = store.create_project("IPN")
    sample = store.create_sample(project, "LCE2-VUGT")
    specimen = create_specimen(store, sample, "film A")
    return store, sample, specimen


@pytest.mark.parametrize("technique,method", [
    ("DMA", "temperature_ramp"),
    ("DMA", "stress_relaxation"),
    ("DSC", "calorimetry"),
    ("Rheology", "amplitude_sweep"),
    ("Rheology", "frequency_sweep"),
    ("Rheology", "stress_relaxation"),
    ("Tensile", "tensile_test"),
])
def test_valid_measurement_metadata(specimen_context, technique, method):
    store, sample, specimen = specimen_context
    measurement = create_measurement(store, specimen, technique, method)
    profile = get_sample_profile(store, sample)
    assert any(m["measurement_id"] == measurement
               for m in profile["techniques"][technique])


@pytest.mark.parametrize("technique,method", [
    ("DSC", "tensile_test"),
    ("DSC", "temperature_ramp"),
    ("DMA", "calorimetry"),
    ("Tensile", "frequency_sweep"),
    ("Rheology", "tensile_test"),
])
def test_invalid_pair_does_not_create_record(specimen_context, technique, method):
    store, sample, specimen = specimen_context
    with pytest.raises(ValueError, match="mismatch"):
        create_measurement(store, specimen, technique, method)
    assert get_sample_profile(store, sample)["specimens"][0]["measurements"] == []


def test_other_method_remains_available(specimen_context):
    store, _, specimen = specimen_context
    assert create_measurement(store, specimen, "DSC", "other")
