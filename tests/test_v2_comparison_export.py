"""End-to-end comparison export regression using two synthetic samples."""
import csv
from io import StringIO
import json

import pytest

from vitrifit2.comparison_export import comparison_csv, comparison_rows
from vitrifit2.persistence import VitriFitStore


def test_cross_sample_comparison_csv_survives_restart_and_trimming(tmp_path):
    store = VitriFitStore(tmp_path / "v2")
    project = store.create_project("Synthetic polymer")
    runs = []
    curve_ids = []
    for sample_name, temperature, tau in (
        ("LCE2", 70, 100.0), ("VUGT", 100, 12.5)
    ):
        sample = store.create_sample(project, sample_name)
        imported = store.import_experiment(
            sample, sample_name + ".csv", (sample_name + " raw").encode(),
            [{"source_curve_id": "relaxation", "temperature_c": temperature,
              "time_s": [0.01, 1, 10, 100],
              "modulus_mpa": [1.0, .8, .5, .2]}])
        curve = imported["curve_ids"][0]
        curve_ids.append(curve)
        runs.append(store.save_analysis(
            curve, "KWW", "1/e", {"beta_bounds": [0.2, 1.0]},
            {"tau_s": tau, "beta": 0.65}))
    comparison = store.save_comparison("LCE2 vs VUGT", "kinetics", runs)
    store.apply_region(curve_ids[0], "keep", 1, 100)
    reopened = VitriFitStore(store.root)
    rows = comparison_rows(reopened, comparison)
    assert [row["sample_name"] for row in rows] == ["LCE2", "VUGT"]
    assert [row["temperature_c"] for row in rows] == [70, 100]
    assert [row["is_current"] for row in rows] == [False, True]
    assert [json.loads(row["results_json"])["tau_s"] for row in rows] == [100, 12.5]
    assert rows[0]["revision_id"] == store.get_analysis(runs[0])["revision_id"]
    exported = list(csv.DictReader(StringIO(comparison_csv(reopened, comparison))))
    assert len(exported) == 2
    assert exported[0]["is_current"] == "False"
    assert json.loads(exported[1]["config_json"]) == {"beta_bounds": [0.2, 1.0]}
    assert [row["run_id"] for row in exported] == runs


def test_comparison_export_rejects_missing_session(tmp_path):
    store = VitriFitStore(tmp_path / "v2")
    with pytest.raises(KeyError):
        comparison_csv(store, "missing")
