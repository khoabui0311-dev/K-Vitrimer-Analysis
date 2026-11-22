"""Independent tests for frequency-sweep SI conversion and crossovers."""
import math
import pytest

from vitrifit2.frequency_sweep import analyze_frequency_sweep


def test_hz_and_kpa_conversion_and_viscosity():
    result = analyze_frequency_sweep([1, 10], [1, 2], [.5, 1],
                                     frequency_unit="Hz", modulus_unit="kPa")
    assert result["angular_frequency_rad_s"][0] == pytest.approx(2*math.pi)
    assert result["storage_modulus_pa"] == pytest.approx([1000, 2000])
    assert result["tan_delta"] == pytest.approx([.5, .5])
    assert result["complex_viscosity_pa_s"][0] == pytest.approx(
        math.hypot(1000, 500)/(2*math.pi))
    assert result["crossover_frequency_hz"] == []


def test_crossover_interpolated_only_in_measured_range():
    result = analyze_frequency_sweep([1, 100], [10, 10], [100, 1])
    assert len(result["crossover_frequency_hz"]) == 1
    assert 1 < result["crossover_frequency_hz"][0] < 100


def test_exact_measured_crossover_is_reported_once():
    result = analyze_frequency_sweep([1, 10, 100], [10, 10, 10], [20, 10, 5])
    assert result["crossover_frequency_hz"] == pytest.approx([10])


def test_unsorted_frequencies_are_sorted():
    result = analyze_frequency_sweep([10, 1], [20, 10], [10, 5])
    assert result["storage_modulus_pa"] == pytest.approx([10, 20])


@pytest.mark.parametrize("frequency,gp,gpp", [
    ([0, 1], [1, 1], [1, 1]),
    ([1, 1], [1, 1], [1, 1]),
    ([1, 2], [1, 0], [1, 1]),
    ([1, 2], [1, 1], [1, -1]),
    ([1], [1], [1]),
])
def test_invalid_sweep_rejected(frequency, gp, gpp):
    with pytest.raises(ValueError):
        analyze_frequency_sweep(frequency, gp, gpp)


def test_invalid_units_rejected():
    with pytest.raises(ValueError):
        analyze_frequency_sweep([1, 2], [1, 2], [1, 2], frequency_unit="rpm")
