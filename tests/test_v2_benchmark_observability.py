"""Tests for characteristic-time observability relative to acquisition window."""
import math
import pytest
from vitrifit2.benchmark_observability import relaxation_observability


def test_maxwell_crossing_inside_window():
    result = relaxation_observability((.01, 10., 100., 1000.),
                                      model="maxwell", parameters=(100.,))
    assert result["predicted_crossing_within_window"] is True
    assert result["measured_crossing_observed"] is False
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


@pytest.mark.parametrize("parameters", [100., [[100.]], [float("nan")]])
def test_model_parameter_shape_and_finiteness_rejected(parameters):
    with pytest.raises(ValueError):
        relaxation_observability((1., 10., 100.),
                                 model="maxwell", parameters=parameters)


def test_empirical_and_predicted_crossings_are_independent():
    result = relaxation_observability(
        (1., 10., 100., 1000.), model="maxwell",
        parameters=(10000.,), normalized_modulus=(1., .5, .2, .1))
    assert result["location"] == "after_window"
    assert result["measured_crossing_observed"] is True
    assert result["measured_crossing_location"] == "inside_window"
    assert result["warning"]


def test_kww_crossing_depends_on_threshold_but_tau_is_one_over_e():
    result = relaxation_observability(
        (.01, 1., 100., 1000.), model="kww",
        parameters=(100., .5), threshold=math.exp(-2))
    assert result["crossing_time_s"] == pytest.approx(400.)


@pytest.mark.parametrize("threshold", ["0.5", None, True, float("nan"), 0, 1])
def test_invalid_threshold_types_and_bounds_rejected(threshold):
    with pytest.raises(ValueError, match="threshold"):
        relaxation_observability((1., 10., 100.), model="maxwell",
                                 parameters=(10.,), threshold=threshold)


def test_upward_measured_crossing_not_misclassified_as_relaxation():
    result = relaxation_observability(
        (1., 10., 100.), model="maxwell", parameters=(10.,),
        normalized_modulus=(.1, .2, .9))
    assert result["measured_crossing_observed"] is False
    assert result["measured_crossing_time_s"] is None


@pytest.mark.parametrize("model, parameters, threshold", [
    ("maxwell", (1e308,), math.exp(-2)),
    ("kww", (1e308, .5), math.exp(-2)),
    ("dual_maxwell", (.5, 1e308, 1e308), math.exp(-1)),
    ("dual_maxwell", (.5, 1., 2.), 1e-300),
])
def test_unrepresentable_or_unbracketed_crossing_rejected(model, parameters, threshold):
    with pytest.raises(ValueError, match="crossing|bracket"):
        relaxation_observability((.01, 1., 10.), model=model,
                                 parameters=parameters, threshold=threshold)


def test_empirical_crossing_reports_acquisition_bracket_not_false_precision():
    result = relaxation_observability(
        (1., 10., 100., 1000.), model="kww", parameters=(100., .5),
        normalized_modulus=(1., .9, .2, .1))
    assert result["measured_crossing_bracket_s"] == [10., 100.]
    assert 10. < result["measured_crossing_time_s"] < 100.
    assert result["crossing_time_s"] == pytest.approx(100.)


def test_unobserved_empirical_crossing_has_no_acquisition_bracket():
    result = relaxation_observability(
        (1., 10., 100.), model="maxwell", parameters=(10.,),
        normalized_modulus=(1., .9, .8))
    assert result["measured_crossing_time_s"] is None
    assert result["measured_crossing_bracket_s"] is None


def test_exact_threshold_at_first_acquired_point_is_observed():
    threshold = math.exp(-1)
    result = relaxation_observability(
        (10., 20., 30.), model="maxwell", parameters=(100.,),
        normalized_modulus=(threshold, .3, .2))
    assert result["measured_crossing_observed"] is True
    assert result["measured_crossing_time_s"] == pytest.approx(10.)
    assert result["measured_crossing_bracket_s"] == [10., 10.]
    assert result["location"] == "after_window"


def test_exact_threshold_at_last_acquired_point_is_observed():
    threshold = math.exp(-1)
    result = relaxation_observability(
        (1., 10., 100.), model="maxwell", parameters=(100.,),
        normalized_modulus=(1., .7, threshold))
    assert result["measured_crossing_observed"] is True
    assert result["measured_crossing_time_s"] == pytest.approx(100.)
    assert result["measured_crossing_bracket_s"] == [10., 100.]


def test_noisy_relaxation_multiple_downward_crossings_are_flagged():
    threshold = math.exp(-1)
    result = relaxation_observability(
        (1., 2., 3., 4., 5.), model="maxwell", parameters=(3.,),
        normalized_modulus=(.9, .2, .6, .1, .05))
    assert result["measured_downward_crossing_count"] == 2
    assert result["measured_multiple_crossings"] is True
    assert result["measured_crossing_bracket_s"] == [1., 2.]
    assert 1. < result["measured_crossing_time_s"] < 2.


def test_monotone_relaxation_has_one_downward_crossing():
    result = relaxation_observability(
        (1., 2., 3., 4.), model="maxwell", parameters=(3.,),
        normalized_modulus=(1., .8, .2, .1))
    assert result["measured_downward_crossing_count"] == 1
    assert result["measured_multiple_crossings"] is False
