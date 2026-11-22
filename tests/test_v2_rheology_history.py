"""Integration tests for history, reanalysis, comparisons and LVR evidence."""
import pytest

from vitrifit2.persistence import VitriFitStore
from vitrifit2.sample_profile import create_measurement, create_specimen
from vitrifit2.rheology_workflow import analyze_rheology_csv
from vitrifit2.rheology_history import (
    list_rheology_analyses, reanalyze_rheology_file,
    compare_rheology_analyses, check_frequency_sweep_lvr,
)


@pytest.fixture
def setup(tmp_path):
    store = VitriFitStore(tmp_path)
    project = store.create_project("LCE")
    sample = store.create_sample(project, "VUGT")
    specimen = create_specimen(store, sample, "disc-1")
    return store, specimen


def amplitude(store, specimen, *, temp=40, freq=1):
    mid = create_measurement(
        store, specimen, "Rheology", "amplitude_sweep",
        {"temperature_c": temp, "frequency_hz": freq,
         "geometry_id": "plate-8mm", "material_state_id": "annealed"})
    raw = b"strain,Gp\n.01,1000\n.02,1000\n.03,1000\n.04,1000\n.05,1000\n.1,990\n.2,900\n"
    aid = analyze_rheology_csv(
        store, mid, "lvr.csv", raw, method="amplitude_sweep",
        columns={"strain_percent": "strain", "storage_modulus": "Gp"})
    return mid, aid


def frequency(store, specimen, *, temp=40, freq=1, strain=.05):
    mid = create_measurement(
        store, specimen, "Rheology", "frequency_sweep",
        {"temperature_c": temp, "frequency_hz": freq,
         "strain_percent": strain, "geometry_id": "plate-8mm",
         "material_state_id": "annealed"})
    aid = analyze_rheology_csv(
        store, mid, "freq.csv", b"f,Gp,Gpp\n1,1000,200\n10,1200,300\n",
        method="frequency_sweep",
        columns={"frequency": "f", "storage_modulus": "Gp",
                 "loss_modulus": "Gpp"})
    return mid, aid


def test_reanalysis_is_immutable_and_reopens(setup):
    store, specimen = setup
    mid, original = amplitude(store, specimen)
    new = reanalyze_rheology_file(store, original, departure_fraction=.15)
    reopened = VitriFitStore(store.root)
    history = list_rheology_analyses(reopened, mid)
    assert {a["analysis_id"] for a in history} == {original, new}
    old = next(a for a in history if a["analysis_id"] == original)
    newer = next(a for a in history if a["analysis_id"] == new)
    assert old["config"]["departure_fraction"] == .05
    assert newer["config"]["departure_fraction"] == .15
    assert old["file_id"] == newer["file_id"]
    assert old["source_sha256"] == newer["source_sha256"]
    assert old["results"]["status"] == "departure_detected"
    assert newer["results"]["status"] == "no_departure_in_measured_range"


def test_comparison_requires_explicit_matching_conditions(setup):
    store, specimen = setup
    _, a = amplitude(store, specimen, temp=40)
    _, b = amplitude(store, specimen, temp=100)
    mismatch = compare_rheology_analyses(
        store, [a, b], required_condition_keys=["temperature_c", "frequency_hz"])
    assert mismatch["status"] == "incompatible_conditions"
    assert mismatch["mismatched_or_missing_keys"] == ["temperature_c"]
    matched = compare_rheology_analyses(
        store, [a, b], required_condition_keys=["frequency_hz"])
    assert matched["status"] == "conditions_matched"
    with pytest.raises(ValueError):
        compare_rheology_analyses(store, [a, a],
                                  required_condition_keys=["temperature_c"])


def test_lvr_evidence_requires_same_specimen_and_conditions(setup):
    store, specimen = setup
    _, lvr = amplitude(store, specimen)
    _, fs = frequency(store, specimen)
    assert check_frequency_sweep_lvr(store, fs, lvr)["status"] == "verified_oscillatory_lvr"
    _, fs_hot = frequency(store, specimen, temp=100)
    assert check_frequency_sweep_lvr(store, fs_hot, lvr)["status"] == "not_directly_verified"
    _, fs_large = frequency(store, specimen, strain=.2)
    assert check_frequency_sweep_lvr(store, fs_large, lvr)["status"] == "outside_measured_lvr"
    second_specimen = create_specimen(
        store, _sample_id(store, specimen),
        "disc-2")
    _, fs_other = frequency(store, second_specimen)
    assert check_frequency_sweep_lvr(store, fs_other, lvr)["status"] == "not_directly_verified"


def _sample_id(store, specimen):
    with store._db() as db:
        return store._require(db, "v2_specimens", specimen)["sample_id"]
