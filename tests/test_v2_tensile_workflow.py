"""Tensile scientific and persistent workflow regressions."""
import pytest

from vitrifit2.persistence import VitriFitStore
from vitrifit2.sample_profile import create_specimen, create_measurement
from vitrifit2.tensile_analysis import analyze_tensile
from vitrifit2.tensile_workflow import (
    import_tensile_csv, get_tensile_analysis, list_tensile_analyses,
)


def test_engineering_and_true_tensile_strain():
    result = analyze_tensile(
        [0, .01, .02, .03, .04, .05], [0, 1, 2, 3, 4, 5],
        gauge_length_mm=10, width_mm=2, thickness_mm=1,
        modulus_fit_strain_min=.001, modulus_fit_strain_max=.005)
    assert result["engineering_strain"][-1] == pytest.approx(.005)
    assert result["engineering_stress_mpa"][-1] == pytest.approx(2.5)
    assert result["true_strain_estimate"][-1] == pytest.approx(.0049875415)
    assert result["true_stress_mpa_estimate"][-1] == pytest.approx(2.5125)
    assert result["youngs_modulus_mpa"] == pytest.approx(500)
    assert result["modulus_fit_points"] == 5


def test_missing_fit_window_does_not_invent_modulus():
    result = analyze_tensile(
        [0, 1, 2, 3], [0, 1, 2, 3],
        gauge_length_mm=10, width_mm=2, thickness_mm=1)
    assert result["youngs_modulus_mpa"] is None


def test_tensile_csv_persists_and_reopens(tmp_path):
    root = tmp_path / "workspace"
    store = VitriFitStore(root)
    sample = store.create_sample(store.create_project("P"), "LCE")
    specimen = create_specimen(store, sample, "film")
    mid = create_measurement(store, specimen, "Tensile", "tensile_test")
    raw = b"extension,load\n0,0\n.01,1\n.02,2\n.03,3\n.04,4\n.05,5\n"
    aid = import_tensile_csv(
        store, mid, "tensile.csv", raw,
        columns={"displacement_mm": "extension", "force_n": "load"},
        gauge_length_mm=10, width_mm=2, thickness_mm=1)
    reopened = VitriFitStore(root)
    result = get_tensile_analysis(reopened, aid)
    assert result["results"]["max_engineering_stress_mpa"] == pytest.approx(2.5)
    assert result["results"]["youngs_modulus_mpa"] == pytest.approx(500)
    assert len(list_tensile_analyses(reopened, mid)) == 1


def test_invalid_tensile_import_does_not_attach(tmp_path):
    store = VitriFitStore(tmp_path)
    sample = store.create_sample(store.create_project("P"), "S")
    specimen = create_specimen(store, sample, "film")
    mid = create_measurement(store, specimen, "Tensile", "tensile_test")
    with pytest.raises(ValueError):
        import_tensile_csv(
            store, mid, "bad.csv", b"extension,load\n0,0\n",
            columns={"displacement_mm": "extension", "force_n": "load"},
            gauge_length_mm=0, width_mm=2, thickness_mm=1)
    assert list(store.blobs.iterdir()) == []
