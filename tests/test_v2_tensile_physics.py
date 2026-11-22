"""Physical-unit and invalid-fit-window tensile regression checks."""
import numpy as np
import pytest

from vitrifit2.tensile_analysis import analyze_tensile


def test_engineering_true_strain_and_stress_with_explicit_geometry():
    # Gauge 10 mm, initial area 2 mm2, 100% engineering extension.
    result = analyze_tensile(
        [0, 2, 5, 10], [0, 2, 5, 10],
        gauge_length_mm=10, width_mm=2, thickness_mm=1,
        modulus_fit_strain_min=0, modulus_fit_strain_max=1)
    assert result["engineering_strain"][-1] == pytest.approx(1)
    assert result["engineering_stress_mpa"][-1] == pytest.approx(5)
    assert result["true_strain_estimate"][-1] == pytest.approx(np.log(2))
    assert result["true_stress_mpa_estimate"][-1] == pytest.approx(10)
    assert result["youngs_modulus_mpa"] == pytest.approx(5)


@pytest.mark.parametrize("lower,upper", [
    (float("nan"), .01), (0, float("inf")), (-.01, .01),
    (.02, .01), (0, float("nan")), (True, .01),
])
def test_invalid_modulus_windows_rejected(lower, upper):
    with pytest.raises(ValueError, match="modulus fit window"):
        analyze_tensile([0, 1, 2, 3], [0, 1, 2, 3],
                        gauge_length_mm=10, width_mm=2, thickness_mm=1,
                        modulus_fit_strain_min=lower,
                        modulus_fit_strain_max=upper)


def test_true_stress_estimate_can_be_disabled():
    result = analyze_tensile(
        [0, 1, 2, 3], [0, 1, 2, 3],
        gauge_length_mm=10, width_mm=2, thickness_mm=1,
        calculate_true=False)
    assert result["true_strain_estimate"] is None
    assert result["true_stress_mpa_estimate"] is None
