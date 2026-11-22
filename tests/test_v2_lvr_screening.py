"""Regression tests for conservative oscillatory LVR screening."""
import numpy as np
import pytest

from vitrifit2.lvr_screening import assess_oscillatory_lvr


def test_known_plateau_and_first_departure():
    x = [.01, .02, .03, .04, .05, .1, .2, .4]
    g = [1000, 1001, 999, 1002, 998, 990, 940, 850]
    result = assess_oscillatory_lvr(x, g)
    assert result["status"] == "departure_detected"
    assert result["first_departure_strain_percent"] == pytest.approx(.2)
    assert result["highest_measured_in_range_strain_percent"] == pytest.approx(.1)


def test_no_departure_is_not_claimed_infinite_lvr():
    result = assess_oscillatory_lvr(
        [.01, .02, .03, .04, .05, .1],
        [1000, 1000, 1000, 1000, 1000, 990])
    assert result["status"] == "no_departure_in_measured_range"
    assert result["first_departure_strain_percent"] is None


def test_noisy_plateau_is_indeterminate():
    result = assess_oscillatory_lvr(
        [.01, .02, .03, .04, .05, .1],
        [1000, 1100, 900, 1000, 1050, 500])
    assert result["status"] == "indeterminate"


def test_unsorted_input_is_sorted_by_strain():
    x = np.array([.2, .05, .01, .1, .04, .03, .02])
    g = np.array([900, 1000, 1000, 990, 1000, 1000, 1000])
    result = assess_oscillatory_lvr(x, g)
    assert result["first_departure_strain_percent"] == pytest.approx(.2)


@pytest.mark.parametrize("x,g", [
    ([.01, .01, .03, .04], [1, 1, 1, 1]),
    ([.01, .02, .03, .04], [1, 0, 1, 1]),
    ([.01, .02, .03], [1, 1, 1]),
])
def test_invalid_inputs_rejected(x, g):
    with pytest.raises(ValueError):
        assess_oscillatory_lvr(x, g)
