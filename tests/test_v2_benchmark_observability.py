"""Tests for characteristic-time observability relative to acquisition window."""
import math
import pytest
from vitrifit2.benchmark_observability import relaxation_observability


def test_maxwell_crossing_inside_window():
    result = relaxation_observability((.01, 10., 100., 1000.),
                                      model="maxwell", parameters=(100.,))
    assert result["predicted_crossing_within_window"] is True\n    assert result["measured_crossing_observed"] is False
    assert result["crossing_time_s"] == pytest.approx(100.)


def test_maxwell_crossing_after_window_is_extrapolated():
    result = relaxation_observability((.01, 1., 10.),
                                      model="maxwell", parameters=(100.,))
    assert result["location"] == "after_window"
    assert result["warning"]


def test_maxwell_crossing_before_window_is_extrapolated():
    result = relaxation_observability((10., 20., 30.),
                                      model="maxwell", parameters=(1.,))
    assert result["location"] == "before_window"


def test_kww_tau_equals_one_over_e_crossing():
    result = relaxation_observability((.01, 100., 1000.),
                                      model="kww", parameters=(100., .6))
    assert result["crossing_time_s"] == pytest.approx(100.)


def test_dual_maxwell_crossing_is_bracketed_numerically():
    result = relaxation_observability((.01, 1., 10., 100., 1000.),
                                      model="dual_maxwell",
                                      parameters=(.3, 10., 100.))
    assert 10 < result["crossing_time_s"] < 100


@pytest.mark.parametrize("parameters", [(0.,), (-1.,)])
def test_invalid_maxwell_tau_rejected(parameters):
    with pytest.raises(ValueError):
        relaxation_observability((.01, 10.), model="maxwell",
                                 parameters=parameters)


def test_predicted_crossing_is_not_evidence_of_measured_crossing():
    result = relaxation_observability((1., 10., 100., 1000.),
                                      model="maxwell", parameters=(100.,),
                                      normalized_modulus=(.9, .8, .7, .6))
    assert result["predicted_crossing_within_window"] is True
    assert result["measured_crossing_observed"] is False
    assert result["measured_crossing_time_s"] is None


def test_empirical_crossing_interpolates_measured_bracket():
    result = relaxation_observability((1., 10., 100.),
                                      model="maxwell", parameters=(100.,),
                                      normalized_modulus=(1., .5, .2))
    assert result["measured_crossing_observed"] is True
    expected = 10. + (math.exp(-1)-.5) * (100.-10.) / (.2-.5)
    assert result["measured_crossing_time_s"] == pytest.approx(expected)


def test_mismatched_measured_response_rejected():
    with pytest.raises(ValueError, match="Measured response"):
        relaxation_observability((1., 10., 100.),
                                 model="maxwell", parameters=(100.,),
                                 normalized_modulus=(1., .5))
