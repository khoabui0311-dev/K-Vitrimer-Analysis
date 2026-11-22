"""Persistence regressions for additive specimen/measurement profiles."""
import pytest

from vitrifit2.persistence import VitriFitStore
from vitrifit2.sample_profile import (
    create_measurement, create_specimen, get_sample_profile,
)


def test_profile_persists_multiple_specimens_and_techniques(tmp_path):
    root = tmp_path / "research"
    store = VitriFitStore(root)
    project = store.create_project("Vitrimer LCE")
    sample = store.create_sample(project, "VUGT")
    a = create_specimen(store, sample, "disk-1", {"thickness_mm": 1})
    b = create_specimen(store, sample, "film-2", {"orientation": "draw"})
    rheo = create_measurement(store, a, "Rheology", "amplitude_sweep",
                              {"temperature_c": 40, "frequency_hz": 1})
    create_measurement(store, b, "DMA", "temperature_ramp",
                       {"heating_rate_c_min": 3})
    reopened = VitriFitStore(root)
    profile = get_sample_profile(reopened, sample)
    assert len(profile["specimens"]) == 2
    assert profile["techniques"]["DSC"] == []
    assert profile["techniques"]["Tensile"] == []
    assert profile["techniques"]["Rheology"][0]["measurement_id"] == rheo
    assert profile["techniques"]["Rheology"][0]["conditions"]["temperature_c"] == 40


def test_existing_relaxation_curves_remain_accessible(tmp_path):
    store = VitriFitStore(tmp_path)
    sample = store.create_sample(store.create_project("P"), "S")
    imported = store.import_experiment(
        sample, "original.csv", b"immutable",
        [{"source_curve_id": "c", "temperature_c": 70,
          "time_s": [.01, 1], "modulus_mpa": [1, .5]}])
    create_specimen(store, sample, "new specimen")
    assert store.get_original_file(imported["experiment_id"]) == b"immutable"
    assert store.get_curve(imported["curve_ids"][0])["time_s"] == [.01, 1]


def test_invalid_references_and_metadata_rejected(tmp_path):
    store = VitriFitStore(tmp_path)
    with pytest.raises(KeyError):
        create_specimen(store, "missing", "s")
    sample = store.create_sample(store.create_project("P"), "S")
    with pytest.raises(ValueError):
        create_specimen(store, sample, " ", {})
    specimen = create_specimen(store, sample, "s")
    with pytest.raises(ValueError):
        create_measurement(store, specimen, "Unknown", "other")
    with pytest.raises(KeyError):
        create_measurement(store, "missing", "DMA", "temperature_ramp")
