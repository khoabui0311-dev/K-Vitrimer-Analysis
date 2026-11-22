"""Quantify relaxation-fit sensitivity to measurement-window truncation.

Uses the same production models as VitriFit and reports fitted parameters
for progressively shorter portions of a single measurement.
"""
from __future__ import annotations

import math
import numpy as np
from scipy.optimize import curve_fit
from can_relax.core.models import Maxwell, SingleKWW

_MODELS = {"maxwell": Maxwell, "kww": SingleKWW}


def window_sensitivity(time_s, normalized_modulus, *, model="kww",
                       fractions=(1.0, .75, .5, .25), min_points=12):
    """Fit prefixes of an ordered trace, preserving physical time coordinates.

    Fractions denote *observation count*, not fractions of elapsed time.
    This distinction matters for logarithmically sampled measurements.
    """
    if model not in _MODELS:
        raise ValueError("Window sensitivity currently supports Maxwell/KWW")
    t = np.asarray(time_s, dtype=float)
    y = np.asarray(normalized_modulus, dtype=float)
    if (t.ndim != 1 or y.ndim != 1 or t.shape != y.shape
            or len(t) < min_points or min_points < 8
            or not np.all(np.isfinite(t)) or not np.all(np.isfinite(y))
            or np.any(t < 0) or np.any(np.diff(t) <= 0)):
        raise ValueError("Need finite ordered observations and sufficient points")
    if (not fractions or any(not math.isfinite(f) or not 0 < f <= 1
                             for f in fractions)):
        raise ValueError("Fractions must be in (0,1]")
    fitted = []
    implementation = _MODELS[model]()
    for fraction in fractions:
        count = max(min_points, min(len(t), int(round(len(t) * fraction))))
        ti, yi = t[:count], y[:count]
        try:
            params, _ = curve_fit(implementation.func, ti, yi,
                                  p0=implementation.get_initial_guess(ti, yi),
                                  bounds=implementation.get_bounds(),
                                  maxfev=20000)
            fitted.append({
                "fraction": float(fraction), "points": int(count),
                "last_time_s": float(ti[-1]),
                "parameters": [float(p) for p in params],
                "status": "ok",
            })
        except (RuntimeError, ValueError, FloatingPointError, OverflowError) as exc:
            fitted.append({
                "fraction": float(fraction), "points": int(count),
                "last_time_s": float(ti[-1]),
                "status": "failed", "error": str(exc),
            })
    full = next((item for item in fitted if item["fraction"] == 1
                 and item["status"] == "ok"), None)
    if full is not None:
        for item in fitted:
            if item["status"] == "ok":
                item["relative_parameter_change"] = [
                    abs(value - reference) / max(abs(reference), 1e-12)
                    for value, reference in zip(
                        item["parameters"], full["parameters"])]
    return {
        "model": model, "windows": fitted,
        "warning": ("Short-window stability is a sensitivity diagnostic, "
                    "not evidence that a fit is mechanistically correct"),
    }
