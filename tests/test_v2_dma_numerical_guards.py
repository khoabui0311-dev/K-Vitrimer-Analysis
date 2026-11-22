"""Check extreme DMA modulus ratios without silently returning Infinity."""
import pytest

from vitrifit2.thermal_analysis import analyze_dma_ramp


def test_dma_tan_delta_ratio_overflow_rejected():
    with pytest.raises(ValueError, match="tan delta overflow"):
        analyze_dma_ramp([20, 30, 40, 50],
                         [1e-300] * 4, [1e300] * 4)


def test_dma_tan_delta_peak_not_assigned_at_endpoint():
    result = analyze_dma_ramp([20, 30, 40, 50],
                              [100, 100, 100, 100],
                              [1, 2, 3, 4])
    assert result["tan_delta_peak_temperature_c"] is None
    assert result["tan_delta_peak_is_interior"] is False


def test_dma_interior_peak_is_not_dsc_tg_onset():
    result = analyze_dma_ramp([20, 30, 40, 50],
                              [100, 100, 100, 100],
                              [1, 3, 2, 1])
    assert result["tan_delta_peak_temperature_c"] == 30
    assert "not a DSC Tg onset" in result["warning"]
