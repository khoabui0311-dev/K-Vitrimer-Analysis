"""Reproducible residual-bootstrap uncertainty for relaxation benchmarks.

Bootstrap estimates are conditional on the chosen model and the residual
resampling assumption; not evidence for a molecular mechanism.
"""
from __future__ import annotations

import numpy as np
from scipy.optimize import curve_fit

from can_relax.core.models import Maxwell, SingleKWW, TwoMaxwell

_MODELS = {"maxwell": Maxwell, "kww": SingleKWW, "dual_maxwell": TwoMaxwell}


def bootstrap_relaxation(time_s, normalized_modulus, *, model="kww",
                         replicates=200, seed=1729, confidence=0.95):
    """Return percentile intervals from fixed-seed residual bootstrap.

    Resamples centered residuals independently, holding measured times fixed.
    This is not a block bootstrap and may understate uncertainty for
    serially correlated experimental measurements.
    """
    if model not in _MODELS:
        raise ValueError("Unknown relaxation model")
    if (not isinstance(replicates, int) or isinstance(replicates, bool)
            or not 20 <= replicates <= 10000):
        raise ValueError("replicates must be an integer between 20 and 10000")
    if not np.isfinite(confidence) or not .5 < confidence < 1:
        raise ValueError("confidence must be strictly between 0.5 and 1")
    t = np.asarray(time_s, dtype=float)
    y = np.asarray(normalized_modulus, dtype=float)
    if (t.ndim != 1 or y.ndim != 1 or t.shape != y.shape
            or len(t) < 8 or not np.all(np.isfinite(t))
            or not np.all(np.isfinite(y)) or np.any(t < 0)
            or np.any(np.diff(t) <= 0)):
        raise ValueError("Need >=8 finite ordered relaxation observations")
    implementation = _MODELS[model]()
    bounds = implementation.get_bounds()
    initial = implementation.get_initial_guess(t, y)
    optimum, _ = curve_fit(implementation.func, t, y, p0=initial,
                           bounds=bounds, maxfev=20000)
    # Canonicalize the point estimate as well as the bootstrap draws.
    # Two-Maxwell arms are exchangeable: (w, tau1, tau2) is equivalent
    # to (1-w, tau2, tau1). Report tau1 <= tau2 consistently.
    if model == "dual_maxwell" and optimum[1] > optimum[2]:
        optimum = np.asarray([1.0 - optimum[0], optimum[2], optimum[1]])
    predicted = np.asarray(implementation.func(t, *optimum), dtype=float)
    residual = y - predicted
    residual -= residual.mean()
    rng = np.random.default_rng(seed)
    estimates = []
    failures = 0
    for _ in range(replicates):
        simulated = predicted + rng.choice(residual, size=len(residual),
                                           replace=True)
        try:
            params, _ = curve_fit(implementation.func, t, simulated,
                                  p0=optimum, bounds=bounds, maxfev=10000)
            if np.all(np.isfinite(params)):
                estimates.append(params)
            else:
                failures += 1
        except (ValueError, RuntimeError, FloatingPointError, OverflowError):
            failures += 1
    if not estimates:
        raise ValueError("All bootstrap refits failed")
    estimates = np.asarray(estimates, dtype=float)
    # Canonicalize exchangeable Maxwell arms for meaningful marginal CIs.
    if model == "dual_maxwell":
        swapped = estimates[:, 1] > estimates[:, 2]
        estimates[swapped, 0] = 1 - estimates[swapped, 0]
        old_fast = estimates[swapped, 1].copy()
        estimates[swapped, 1] = estimates[swapped, 2]
        estimates[swapped, 2] = old_fast
    alpha = (1 - confidence) / 2
    lower, upper = np.quantile(estimates, [alpha, 1-alpha], axis=0)
    return {
        "model": model,
        "point_estimate": [float(v) for v in optimum],
        "lower": [float(v) for v in lower],
        "upper": [float(v) for v in upper],
        "confidence": float(confidence),
        "successful_replicates": int(len(estimates)),
        "failed_replicates": int(failures),
        "warning": ("Independent residual resampling assumes exchangeable "
                    "errors; serial correlation and model mismatch can "
                    "invalidate these intervals"),
    }
