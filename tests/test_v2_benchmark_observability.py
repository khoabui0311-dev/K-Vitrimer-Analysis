"""Tests for characteristic-time observability relative to acquisition window."""
import math
import pytest
from vitrifit2.benchmark_observability import relaxation_observability


def test_maxwell_crossing_inside_window():
    result = relaxation_observability((.01, 10., 100., 1000.),
                                      model="maxwell", parameters=(100.,))
    assert result["observed_crossing"] is True
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
