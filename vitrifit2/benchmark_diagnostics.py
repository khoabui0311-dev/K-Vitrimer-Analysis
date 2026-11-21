"""Model-agnostic fit diagnostics for independent synthetic benchmark curves.

These diagnostics compare residuals and information criteria; they do not
establish microscopic relaxation mechanisms.
"""
from __future__ import annotations

import math
import numpy as np
from scipy.optimize import curve_fit

from can_relax.core.models import Maxwell, SingleKWW, TwoMaxwell

_MODELS = {"maxwell": Maxwell, "kww": SingleKWW, "dual_maxwell": TwoMaxwell}
_PARAM_COUNTS = {"maxwell": 1, "kww": 2, "dual_maxwell": 3}


def evaluate_relaxation_models(time_s, normalized_modulus,
                               models=("maxwell", "kww", "dual_maxwell")):
    """Fit a shared measured curve and report RMSE, AICc, and residual trends.

    AICc is undefined for n <= k+1 and is returned as None in that case.
    AICc is comparable only for identical points, weights, and likelihood.
    Fits here use unweighted additive Gaussian errors; no mechanism inferred.
    """
    t = np.asarray(time_s, dtype=float)
    y = np.asarray(normalized_modulus, dtype=float)
    if (t.ndim != 1 or y.ndim != 1 or t.shape != y.shape
            or len(t) < 6 or not np.all(np.isfinite(t))
            or not np.all(np.isfinite(y)) or np.any(t < 0)
            or np.any(np.diff(t) <= 0)):
        raise ValueError("Require >=6 finite, ordered relaxation observations")
    if not models or any(model not in _MODELS for model in models):
        raise ValueError("Unknown or empty relaxation model selection")
    results = {}
    for name in models:
        instance = _MODELS[name]()
        k = _PARAM_COUNTS[name]
        try:
            initial = instance.get_initial_guess(t, y)
            params, _ = curve_fit(instance.func, t, y, p0=initial,
                                  bounds=instance.get_bounds(), maxfev=20000)
            predicted = np.asarray(instance.func(t, *params), dtype=float)
            residual = y - predicted
            rss = float(np.dot(residual, residual))
            n = len(t)
            rmse = math.sqrt(rss / n)
            # AICc is finite for a perfect fit by using machine-scale RSS.
            safe_rss = max(rss, float(np.finfo(float).tiny))
            aic = n * math.log(safe_rss / n) + 2 * k
            aicc = aic + 2 * k * (k + 1) / (n - k - 1) if n > k + 1 else None
            results[name] = {
                "status": "ok", "parameters": [float(v) for v in params],
                "rmse": rmse, "aicc": aicc,
                "mean_residual": float(np.mean(residual)),
                "lag1_residual_correlation": (
                    float(np.corrcoef(residual[:-1], residual[1:])[0, 1])
                    if np.std(residual[:-1]) > 0 and np.std(residual[1:]) > 0
                    else None),
                "parameter_count": k,
            }
        except (ValueError, RuntimeError, FloatingPointError, OverflowError) as exc:
            results[name] = {"status": "failed", "error": str(exc)}
    return results
