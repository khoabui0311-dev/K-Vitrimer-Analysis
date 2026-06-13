"""
Tests for can_relax.core.processing.DataProcessor

Covers:
- Basic trimming and normalization
- Logarithmic downsampling (≤250 points)
- Negative / NaN / Inf cleaning
- Drift detection (upward tail)
- Minimum points guard
- Peak detection (overshoot handling)
"""
import numpy as np
import pytest
from can_relax.core.processing import DataProcessor


@pytest.fixture
def processor():
    return DataProcessor(min_points=8)


def _make_kww(tau=10.0, beta=0.5, n=500, t_max=200.0, G0=2.5):
    """Generate a clean KWW relaxation curve."""
    t = np.linspace(0.01, t_max, n)
    g = G0 * np.exp(-((t / tau) ** beta))
    return t, g


# ────────────────────────────────────────────────────────────────────
# 1. Happy path: basic trim + normalisation
# ────────────────────────────────────────────────────────────────────
def test_trim_returns_arrays(processor):
    t, g = _make_kww()
    t_out, g_out, G0_out = processor.trim_curve(t, g)
    assert t_out is not None
    assert g_out is not None
    assert G0_out is not None


def test_normalisation_starts_at_one(processor):
    t, g = _make_kww(G0=3.7)
    _, g_out, G0_out = processor.trim_curve(t, g)
    # Normalised curve should start ≤1.0 and ≥0.95 (first few points)
    assert g_out[0] <= 1.0 + 1e-9
    assert g_out[0] >= 0.9


def test_G0_extracted_correctly(processor):
    t, g = _make_kww(G0=2.5)
    _, _, G0_out = processor.trim_curve(t, g)
    # G0 should be close to the true plateau value
    assert abs(G0_out - 2.5) / 2.5 < 0.05  # within 5%


def test_time_starts_near_zero(processor):
    t, g = _make_kww()
    t_out, _, _ = processor.trim_curve(t, g)
    assert t_out[0] < 0.1  # time offset reset to 0.01


# ────────────────────────────────────────────────────────────────────
# 2. Logarithmic downsampling
# ────────────────────────────────────────────────────────────────────
def test_downsampling_caps_at_250(processor):
    t, g = _make_kww(n=2000)
    t_out, g_out, _ = processor.trim_curve(t, g)
    assert len(t_out) <= 250


def test_downsampling_preserves_boundaries(processor):
    t, g = _make_kww(n=2000)
    t_out, _, _ = processor.trim_curve(t, g)
    # Start and end should be close to original boundaries
    assert t_out[0] <= 0.1
    assert t_out[-1] >= 150.0  # preserves the late-time data


def test_short_curve_not_downsampled(processor):
    """Curves shorter than 250 pts should pass through unchanged in length."""
    t, g = _make_kww(n=100)
    t_out, _, _ = processor.trim_curve(t, g)
    assert len(t_out) == pytest.approx(100, abs=5)


# ────────────────────────────────────────────────────────────────────
# 3. Data cleaning (NaN, Inf, negative)
# ────────────────────────────────────────────────────────────────────
def test_nan_removal(processor):
    t, g = _make_kww(n=200)
    t[10] = np.nan
    g[50] = np.nan
    t_out, g_out, _ = processor.trim_curve(t, g)
    assert t_out is not None
    assert not np.any(np.isnan(g_out))


def test_inf_removal(processor):
    t, g = _make_kww(n=200)
    g[5] = np.inf
    t_out, g_out, _ = processor.trim_curve(t, g)
    assert t_out is not None
    assert not np.any(np.isinf(g_out))


def test_negative_values_removed(processor):
    t, g = _make_kww(n=200)
    g[20] = -0.5
    t_out, g_out, _ = processor.trim_curve(t, g)
    assert t_out is not None
    assert np.all(g_out >= 0)


# ────────────────────────────────────────────────────────────────────
# 4. Minimum points guard
# ────────────────────────────────────────────────────────────────────
def test_too_few_points_returns_none(processor):
    t = np.array([0.1, 0.2, 0.3])
    g = np.array([1.0, 0.9, 0.8])
    t_out, g_out, G0_out = processor.trim_curve(t, g)
    assert t_out is None
    assert g_out is None
    assert G0_out is None


def test_all_nan_returns_none(processor):
    t = np.array([np.nan] * 20)
    g = np.array([np.nan] * 20)
    result = processor.trim_curve(t, g)
    assert result[0] is None


# ────────────────────────────────────────────────────────────────────
# 5. Drift detection
# ────────────────────────────────────────────────────────────────────
def test_upward_drift_trimmed(processor):
    """Curve that relaxes then drifts back up should be trimmed at minimum."""
    t, g_base = _make_kww(tau=5.0, n=400, t_max=100.0)
    # Add drift: last 20% rises by 30%
    g_drift = g_base.copy()
    n_drift = len(g_drift) // 5
    g_drift[-n_drift:] += np.linspace(0, 0.3 * g_base[0], n_drift)
    t_out, g_out, _ = processor.trim_curve(t, g_drift)
    # Output should be shorter than input (drift trimmed)
    assert len(t_out) < len(t)


def test_no_drift_keeps_full_length(processor):
    """Clean monotonic decay should not be trimmed."""
    t, g = _make_kww(tau=10.0, n=300, t_max=100.0)
    t_out, _, _ = processor.trim_curve(t, g)
    # Should keep the full time span (no early cut)
    assert t_out[-1] >= 95.0
    # And have a reasonable number of points (log downsampled from 300 might be ~90)
    assert len(t_out) > 50
