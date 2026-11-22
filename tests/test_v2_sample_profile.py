"""Persistence regressions for additive specimen/measurement profiles."""
import pytest

from vitrifit2.persistence import VitriFitStore
from vitrifit2.sample_profile import (
    attach_measurement_file, create_measurement, create_specimen,
    get_measurement_file, get_sample_profile, list_measurement_files,
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


def test_raw_file_attachment_survives_restart_and_preserves_bytes(tmp_path):
    root = tmp_path / "research"
    store = VitriFitStore(root)
    sample = store.create_sample(store.create_project("P"), "VUGT")
    specimen = create_specimen(store, sample, "disc")
    measurement = create_measurement(
        store, specimen, "Rheology", "frequency_sweep",
        {"temperature_c": 40, "frequency_hz": 1})
    raw = b"frequency,Gprime,Gdoubleprime\n1,1000,100\n"
    first = attach_measurement_file(
        store, measurement, "sweep.csv", raw, {"instrument": "rheometer"})
    second = attach_measurement_file(store, measurement, "repeat.csv", raw)
    reopened = VitriFitStore(root)
    assert get_measurement_file(reopened, first) == raw
    files = list_measurement_files(reopened, measurement)
    assert len(files) == 2
    assert files[0]["sha256"] == files[1]["sha256"]
    assert len(list((root / "raw_blobs").iterdir())) == 1
    profile = get_sample_profile(reopened, sample)
    assert len(profile["techniques"]["Rheology"][0]["files"]) == 2
    assert get_measurement_file(reopened, second) == raw


def test_attachment_rejects_missing_measurement_and_empty_bytes(tmp_path):
    store = VitriFitStore(tmp_path)
    with pytest.raises(KeyError):
        attach_measurement_file(store, "missing", "raw.csv", b"valid")
    assert list(store.blobs.iterdir()) == []
    sample = store.create_sample(store.create_project("P"), "S")
    specimen = create_specimen(store, sample, "disc")
    measurement = create_measurement(store, specimen, "DSC", "calorimetry")
    with pytest.raises(ValueError):
        attach_measurement_file(store, measurement, "raw.csv", b"")
