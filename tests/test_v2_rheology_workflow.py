"""End-to-end persistence regressions for the explicit CSV rheology adapter."""
import pytest

from vitrifit2.persistence import VitriFitStore
from vitrifit2.sample_profile import create_measurement, create_specimen, get_sample_profile
from vitrifit2.rheology_workflow import analyze_rheology_csv, get_rheology_analysis


def measurement(store, method):
    sample = store.create_sample(store.create_project("LCE"), "VUGT")
    specimen = create_specimen(store, sample, "disc-1")
    return sample, create_measurement(store, specimen, "Rheology", method)


def test_frequency_csv_roundtrip(tmp_path):
    store = VitriFitStore(tmp_path)
    sample, mid = measurement(store, "frequency_sweep")
    raw = b"freq,Gp,Gpp\n1,1000,500\n10,2000,1000\n"
    aid = analyze_rheology_csv(
        store, mid, "frequency.csv", raw, method="frequency_sweep",
        columns={"frequency": "freq", "storage_modulus": "Gp",
                 "loss_modulus": "Gpp"}, frequency_unit="Hz", modulus_unit="Pa")
    reopened = VitriFitStore(tmp_path)
    result = get_rheology_analysis(reopened, aid)
    assert result["results"]["tan_delta"] == pytest.approx([.5, .5])
    assert result["algorithm_version"] == "rheology_csv_v1"
    assert result["source_sha256"]
    assert len(get_sample_profile(reopened, sample)["techniques"]["Rheology"][0]["files"]) == 1


def test_amplitude_csv_roundtrip(tmp_path):
    store = VitriFitStore(tmp_path)
    _, mid = measurement(store, "amplitude_sweep")
    raw = b"strain,Gp\n0.01,1000\n0.02,1000\n0.03,1000\n0.04,1000\n0.05,1000\n0.1,990\n0.2,900\n"
    aid = analyze_rheology_csv(
        store, mid, "amplitude.csv", raw, method="amplitude_sweep",
        columns={"strain_percent": "strain", "storage_modulus": "Gp"})
    result = get_rheology_analysis(VitriFitStore(tmp_path), aid)
    assert result["results"]["status"] == "departure_detected"
    assert result["results"]["first_departure_strain_percent"] == pytest.approx(.2)


def test_invalid_import_does_not_attach_file(tmp_path):
    store = VitriFitStore(tmp_path)
    sample, mid = measurement(store, "frequency_sweep")
    with pytest.raises(ValueError):
        analyze_rheology_csv(
            store, mid, "invalid.csv", b"freq,Gp\n1,1000\n",
            method="frequency_sweep",
            columns={"frequency": "freq", "storage_modulus": "Gp",
                     "loss_modulus": "Gpp"})
    assert get_sample_profile(store, sample)["techniques"]["Rheology"][0]["files"] == []


def test_method_mismatch_rejected(tmp_path):
    store = VitriFitStore(tmp_path)
    _, mid = measurement(store, "frequency_sweep")
    with pytest.raises(ValueError, match="mismatch"):
        analyze_rheology_csv(
            store, mid, "a.csv", b"strain,Gp\n1,10\n2,9\n",
            method="amplitude_sweep",
            columns={"strain_percent": "strain", "storage_modulus": "Gp"})
