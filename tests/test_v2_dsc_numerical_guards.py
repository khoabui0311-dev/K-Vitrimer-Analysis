"""Guard scientific DSC metadata and numerical derivatives."""
import pytest

from vitrifit2.thermal_analysis import analyze_dsc_trace


@pytest.mark.parametrize("rate", [0, -1, float("nan"), float("inf"), True, "10"])
def test_invalid_dsc_heating_rate_rejected(rate):
    with pytest.raises(ValueError, match="Heating rate"):
        analyze_dsc_trace([20, 30, 40, 50], [1, 2, 3, 4],
                          heating_rate_c_min=rate)


def test_dsc_does_not_falsely_assign_tg_from_slope_maximum():
    result = analyze_dsc_trace([20, 30, 40, 50, 60], [1, 1, 2, 4, 4],
                               heating_rate_c_min=5)
    assert result["t_g_onset_c"] is None
    assert result["enthalpy_j_g"] is None
    assert result["max_abs_heat_flow_slope_temperature_c"] in [30, 40, 50]


def test_dsc_derivative_overflow_is_rejected():
    with pytest.raises(ValueError, match="slope overflow"):
        analyze_dsc_trace([20, 20 + 1e-12, 30, 40],
                          [1e300, -1e300, 0, 1])
