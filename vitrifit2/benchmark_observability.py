"""Measurement-window observability diagnostics for relaxation times.

A fitted relaxation time outside the observed window is extrapolative.
This module uses observed time limits and the model's predicted 1/e crossing
to distinguish within-window predictions from extrapolation.
Measured threshold crossings require actual measured response values.
"""
from __future__ import annotations

import math
import numpy as np
from scipy.optimize import brentq
from can_relax.core.models import Maxwell, SingleKWW, TwoMaxwell

_MODELS = {"maxwell": Maxwell, "kww": SingleKWW, "dual_maxwell": TwoMaxwell}


def relaxation_observability(time_s, *, model, parameters,
                            threshold=math.exp(-1), normalized_modulus=None):
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
    if (isinstance(threshold, (bool, np.bool_))
            or not isinstance(threshold, (int, float, np.integer, np.floating))
            or not math.isfinite(threshold) or not 0 < threshold < 1):
        raise ValueError("threshold must be between zero and one")
    try:
        params = np.asarray(parameters, dtype=float)
    except (TypeError, ValueError) as exc:
        raise ValueError("Invalid model parameters") from exc
    if params.ndim != 1 or not np.all(np.isfinite(params)):
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
        if not math.isfinite(upper) or upper <= 0:
            raise ValueError("Dual-Maxwell crossing bracket overflows")
        try:
            tau = float(brentq(
                lambda value: float(implementation.func(value, *params)) - threshold,
                0., upper))
        except ValueError as exc:
            raise ValueError("Dual-Maxwell crossing cannot be bracketed") from exc
    if not math.isfinite(tau) or tau < 0:
        raise ValueError("Predicted crossing time is nonfinite; check parameters")
    empirical_crossing = None
    empirical_bracket = None
    measured_downward_crossing_count = 0
    if normalized_modulus is not None:
        y = np.asarray(normalized_modulus, dtype=float)
        if (y.ndim != 1 or y.shape != t.shape
                or not np.all(np.isfinite(y))):
            raise ValueError("Measured response must match finite measurement times")
        # Only an actual measured bracket establishes empirical observability.
        # Linear interpolation is descriptive, not an independent fitted tau.
        # Exact equality at the first recorded point is an observed crossing,
        # even though no preceding acquisition interval exists.
        if y[0] == threshold:
            empirical_crossing = float(t[0])
            empirical_bracket = [float(t[0]), float(t[0])]
            measured_downward_crossing_count = 1
        else:
            brackets = np.flatnonzero(
                (y[:-1] >= threshold) & (y[1:] <= threshold))
            measured_downward_crossing_count = int(len(brackets))
            if len(brackets):
                i = int(brackets[0])
                empirical_bracket = [float(t[i]), float(t[i+1])]
                empirical_crossing = (float(t[i]) if y[i] == threshold else
                    float(t[i] + (threshold-y[i]) * (t[i+1]-t[i])
                          / (y[i+1]-y[i])) if y[i+1] != y[i] else float(t[i]))
    first, last = float(t[0]), float(t[-1])
    # An empirical crossing can disagree with a model prediction; keep both.
    empirical_location = (None if empirical_crossing is None else
                          "inside_window")
    location = ("before_window" if tau < first else
                "after_window" if tau > last else "inside_window")
    return {
        "model": model,
        "crossing_time_s": tau,
        "first_observed_time_s": first,
        "last_observed_time_s": last,
        "location": location,
        "predicted_crossing_within_window": location == "inside_window",
        "measured_crossing_time_s": empirical_crossing,
        "measured_crossing_bracket_s": empirical_bracket,
        "measured_downward_crossing_count": measured_downward_crossing_count,
        "measured_multiple_crossings": measured_downward_crossing_count > 1,
        "measured_crossing_observed": empirical_crossing is not None,
        "measured_crossing_location": empirical_location,
        "warning": (None if location == "inside_window" else
                    "Predicted crossing lies outside measurement window; "
                    "reported characteristic time is extrapolated"),
    }
