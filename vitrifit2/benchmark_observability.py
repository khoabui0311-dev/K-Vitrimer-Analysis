"""Measurement-window observability diagnostics for relaxation times.

A fitted relaxation time outside the observed window is extrapolative.
This module uses observed time limits and the model's predicted 1/e crossing
to distinguish measured from extrapolated characteristic times.
"""
from __future__ import annotations

import math
import numpy as np
from scipy.optimize import brentq
from can_relax.core.models import Maxwell, SingleKWW, TwoMaxwell

_MODELS = {"maxwell": Maxwell, "kww": SingleKWW, "dual_maxwell": TwoMaxwell}


def relaxation_observability(time_s, *, model, parameters,
                            threshold=math.exp(-1)):
    """Classify predicted 1/e crossing relative to measured time interval.

    Time values must be nonnegative, ordered, and include at least two points.
    Returns crossing time even if outside the window where mathematically
    bracketable; this is explicitly flagged as extrapolation.
    """
    if model not in _MODELS:
        raise ValueError("Unsupported relaxation model")
    t = np.asarray(time_s, dtype=float)
    if (t.ndim != 1 or len(t) < 2 or not np.all(np.isfinite(t))
            or np.any(t < 0) or np.any(np.diff(t) <= 0)):
        raise ValueError("Need finite increasing nonnegative measurement times")
    if not math.isfinite(threshold) or not 0 < threshold < 1:
        raise ValueError("threshold must be between zero and one")
    params = np.asarray(parameters, dtype=float)
    if not np.all(np.isfinite(params)):
        raise ValueError("Nonfinite model parameters")
    expected_count = {"maxwell": 1, "kww": 2, "dual_maxwell": 3}[model]
    if len(params) != expected_count:
        raise ValueError("Incorrect model parameter count")
    if (model == "maxwell" and params[0] <= 0
            or model == "kww" and (params[0] <= 0 or not 0 < params[1] <= 1)
            or model == "dual_maxwell" and (
                not 0 <= params[0] <= 1 or params[1] <= 0 or params[2] <= 0)):
        raise ValueError("Invalid physical model parameters")
    if model in ("maxwell", "kww"):
        tau = float(params[0] * (-math.log(threshold)) ** (
            1 / (params[1] if model == "kww" else 1)))
    else:
        implementation = TwoMaxwell()
        upper = max(float(params[1]), float(params[2])) * 100
        tau = float(brentq(
            lambda value: float(implementation.func(value, *params)) - threshold,
            0., upper))
    first, last = float(t[0]), float(t[-1])
    location = ("before_window" if tau < first else
                "after_window" if tau > last else "inside_window")
    return {
        "model": model,
        "crossing_time_s": tau,
        "first_observed_time_s": first,
        "last_observed_time_s": last,
        "location": location,
        "observed_crossing": location == "inside_window",
        "warning": (None if location == "inside_window" else
                    "Predicted crossing lies outside measurement window; "
                    "reported characteristic time is extrapolated"),
    }
