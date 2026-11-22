"""Kinetic uncertainty reporting with synthetic, known Arrhenius slope."""
import math

import pytest

from can_relax.core.kinetics import R_GAS
from vitrifit2.comparison import compare_runs
from vitrifit2.persistence import VitriFitStore


@pytest.mark.parametrize("n", [2, 3, 5])
def test_arrhenius_confidence_and_small_sample_reporting(tmp_path, n):
    store = VitriFitStore(tmp_path / "store")
    project = store.create_project("Synthetic")
    sample = store.create_sample(project, "Arrhenius")
    ids = []
    for index, temp in enumerate([70, 80, 90, 100, 110][:n]):
        inv_t = 1 / (temp + 273.15)
        tau = math.exp(-12 + 65000 / R_GAS * inv_t)
        exp = store.import_experiment(
            sample, f"synthetic-{index}.csv", f"synthetic-{index}".encode(),
            [{"source_curve_id": str(temp), "temperature_c": temp,
              "time_s": [0.01, 1, 2, 3, 4, 5, 6, 7],
              "modulus_mpa": [1, .9, .8, .7, .6, .5, .4, .3]}])
        ids.append(store.save_analysis(
            exp["curve_ids"][0], "Maxwell", "fit:Maxwell:characteristic",
            {}, {"tau_s": tau, "flags": []}))
    result = compare_runs(store, ids, "kinetics")["samples"][0]
    assert result["n_distinct_temperatures"] == n
    assert result["retained_temperature_range_c"] == [70, [80, 90, 110][{2:0,3:1,5:2}[n]]]
    assert result["Ea_kj_mol"] == pytest.approx(65, abs=1e-5)
    if n == 2:
        assert result["r2"] is None
        assert result["Ea_ci95_kj_mol"] is None
        assert "Two-point" in result["warning"]
    else:
        lo, hi = result["Ea_ci95_kj_mol"]
        assert lo <= 65 <= hi
        if n == 3:
            assert "three" in result["warning"]
