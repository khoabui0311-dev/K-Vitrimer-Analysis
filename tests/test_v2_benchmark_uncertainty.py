"""Regression tests for deterministic bootstrap uncertainty diagnostics."""
import pytest

from vitrifit2.benchmark_suite import relaxation_case
from vitrifit2.benchmark_uncertainty import bootstrap_relaxation


def test_seeded_kww_bootstrap_is_reproducible_and_contains_ground_truth():
    case = relaxation_case("kww", tau_s=100., beta=.65,
                           noise_fraction=.005, seed=12)
    first = bootstrap_relaxation(case.time_s, case.normalized_modulus,
                                 model="kww", replicates=40, seed=23)
    second = bootstrap_relaxation(case.time_s, case.normalized_modulus,
                                  model="kww", replicates=40, seed=23)
    assert first == second
    assert first["successful_replicates"] + first["failed_replicates"] == 40
    assert first["point_estimate"][0] == pytest.approx(100, rel=.05)
    assert first["point_estimate"][1] == pytest.approx(.65, abs=.05)
    assert first["lower"][0] < first["upper"][0]
    assert first["lower"][1] < first["upper"][1]


def test_maxwell_bootstrap_is_finite():
    case = relaxation_case("maxwell", tau_s=100., noise_fraction=.01, seed=14)
    result = bootstrap_relaxation(case.time_s, case.normalized_modulus,
                                  model="maxwell", replicates=30)
    assert result["lower"][0] < result["upper"][0]
    assert result["successful_replicates"] >= 25


@pytest.mark.parametrize("replicates", [0, 10, 10001, True])
def test_invalid_replicate_counts_rejected(replicates):
    case = relaxation_case("maxwell")
    with pytest.raises(ValueError):
        bootstrap_relaxation(case.time_s, case.normalized_modulus,
                             model="maxwell", replicates=replicates)
