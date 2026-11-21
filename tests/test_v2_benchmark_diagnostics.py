"""Benchmarks for distinguishing relaxation fit quality from mechanism."""
import numpy as np
import pytest

from vitrifit2.benchmark_suite import relaxation_case
from vitrifit2.benchmark_diagnostics import evaluate_relaxation_models


def test_noise_free_maxwell_has_best_information_criterion():
    case = relaxation_case("maxwell", tau_s=100.)
    results = evaluate_relaxation_models(case.time_s, case.normalized_modulus)
    assert all(result["status"] == "ok" for result in results.values())
    assert results["maxwell"]["rmse"] < 1e-6
    assert results["maxwell"]["aicc"] < results["kww"]["aicc"]


def test_two_separated_maxwell_modes_improve_fit_over_single_maxwell():
    case = relaxation_case("dual_maxwell", fast_fraction=.5,
                           fast_tau_s=2., tau_s=500.)
    results = evaluate_relaxation_models(case.time_s, case.normalized_modulus)
    assert results["maxwell"]["status"] == "ok"
    assert results["dual_maxwell"]["status"] == "ok"
    assert results["dual_maxwell"]["rmse"] < results["maxwell"]["rmse"] * .1
    assert results["dual_maxwell"]["aicc"] < results["maxwell"]["aicc"]


def test_seeded_noise_produces_reproducible_diagnostics():
    case = relaxation_case("kww", tau_s=100., beta=.65,
                           noise_fraction=.005, seed=19)
    a = evaluate_relaxation_models(case.time_s, case.normalized_modulus,
                                   models=("maxwell", "kww"))
    b = evaluate_relaxation_models(case.time_s, case.normalized_modulus,
                                   models=("maxwell", "kww"))
    assert a == b
    assert a["kww"]["status"] == "ok"
    assert a["kww"]["rmse"] > 0
    assert a["kww"]["aicc"] < a["maxwell"]["aicc"]


@pytest.mark.parametrize("time,modulus", [
    ([0, 1, 2], [1, .5, .2]),
    ([0, 1, 1, 3, 4, 5], [1, .8, .7, .6, .5, .4]),
    ([0, 1, 2, 3, 4, 5], [1, .8, np.nan, .6, .5, .4]),
])
def test_invalid_observations_rejected(time, modulus):
    with pytest.raises(ValueError):
        evaluate_relaxation_models(time, modulus)


def test_unknown_model_rejected():
    case = relaxation_case("maxwell")
    with pytest.raises(ValueError):
        evaluate_relaxation_models(case.time_s, case.normalized_modulus,
                                   models=("unknown",))
