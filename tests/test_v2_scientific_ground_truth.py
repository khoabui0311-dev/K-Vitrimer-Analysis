"""Scientific ground-truth checks for the complete saved-curve fitting workflow.

The instrument-like observations below are synthetic and contain no user data.
They test the full path through immutable import, manual per-curve trimming,
legacy fitting, and persistence rather than testing only a model equation.
"""
import numpy as np
import pytest

from vitrifit2.persistence import VitriFitStore
from vitrifit2.science import fit_saved_curve


@pytest.mark.parametrize(
    "model,tau_s,beta",
    [("Maxwell", 24.0, 1.0), ("Single_KWW", 24.0, 0.65)],
)
def test_synthetic_ground_truth_fit_and_provenance(tmp_path, model, tau_s, beta):
    store = VitriFitStore(tmp_path / "v2")
    project = store.create_project("Synthetic validation")
    sample = store.create_sample(project, "Known ground truth")
    time = np.geomspace(0.01, 300, 140)
    modulus = 2.5 * np.exp(-((time / tau_s) ** beta))
    experiment = store.import_experiment(
        sample, "synthetic.csv", b"synthetic-data-no-real-sample",
        [{"source_curve_id": "known-70C", "temperature_c": 70,
          "time_s": time.tolist(), "modulus_mpa": modulus.tolist()}])
    curve_id = experiment["curve_ids"][0]
    result = fit_saved_curve(store, curve_id, model=model)
    fitted = result["results"]
    assert fitted["tau_s"] == pytest.approx(tau_s, rel=0.15)
    assert fitted["r2"] > 0.99
    if model == "Single_KWW":
        assert fitted["beta"] == pytest.approx(beta, abs=0.1)
    saved = store.get_analysis(result["run_id"])
    assert saved["is_current"]
    assert saved["revision_id"] == fitted["revision_id"]
    assert saved["config"]["preprocessing"] == "manual_per_curve_mask"
    store.apply_region(curve_id, "keep", 0.1, 250)
    assert not store.get_analysis(result["run_id"])["is_current"]
    assert store.get_analysis(result["run_id"])["results"]["tau_s"] == fitted["tau_s"]
    refitted = fit_saved_curve(store, curve_id, model=model)
    assert refitted["run_id"] != result["run_id"]
    assert refitted["results"]["tau_s"] == pytest.approx(tau_s, rel=0.15)
    assert store.get_analysis(refitted["run_id"])["is_current"]
    assert not store.get_analysis(result["run_id"])["is_current"]
    assert refitted["results"]["revision_id"] != fitted["revision_id"]
