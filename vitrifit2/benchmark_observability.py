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
        # Count distinct transitions from above to at/below the threshold.
        # A plateau at the threshold is one event, not one event per interval.
        crossings = []
        if y[0] == threshold:
            crossings.append((float(t[0]), [float(t[0]), float(t[0])]))
        for i in range(len(y) - 1):
            if y[i] > threshold and y[i+1] <= threshold:
                crossing = float(t[i] + (threshold-y[i]) * (t[i+1]-t[i])
                                 / (y[i+1]-y[i]))
                crossings.append((crossing, [float(t[i]), float(t[i+1])]))
        measured_downward_crossing_count = len(crossings)
        if crossings:
            empirical_crossing, empirical_bracket = crossings[0]
    first, last = float(t[0]), float(t[-1])
    # An empirical crossing can disagree with a model prediction; keep both.
    empirical_location = (None if empirical_crossing is None else
                          "inside_window")
    location = ("before_window" if tau < first else
                "after_window" if tau > last else "inside_window")
    warnings = []
    if location != "inside_window":
        warnings.append("Predicted crossing lies outside measurement window; "
                        "reported characteristic time is extrapolated")
    if measured_downward_crossing_count > 1:
        warnings.append("Multiple measured downward threshold crossings; "
                        "empirical crossing time is ambiguous and may be noise-sensitive")
    # Model and measured crossings are independent. A large disagreement
    # warrants review even if each time lies inside the acquisition window.
    crossing_ratio = None
    log_crossing_ratio = None
    if empirical_crossing is not None and empirical_crossing > 0 and tau > 0:
        # Compare in log space to avoid overflow when times differ greatly.
        log_crossing_ratio = abs(math.log(tau) - math.log(empirical_crossing))
        crossing_ratio = (math.exp(log_crossing_ratio) if log_crossing_ratio <= math.log(
            np.finfo(float).max) else None)
        if log_crossing_ratio >= math.log(2):
            warnings.append("Model-predicted and measured threshold crossings "
                            "differ by at least a factor of two")
    return {
        "model": model,
        "crossing_time_s": tau,
        "first_observed_time_s": first,
        "last_observed_time_s": last,
        "location": location,
        "predicted_crossing_within_window": location == "inside_window",
        "measured_crossing_time_s": empirical_crossing,
        "model_measured_crossing_ratio": crossing_ratio,
        "model_measured_log_crossing_ratio": log_crossing_ratio,
        "measured_crossing_bracket_s": empirical_bracket,
        "measured_downward_crossing_count": measured_downward_crossing_count,
        "measured_multiple_crossings": measured_downward_crossing_count > 1,
        "measured_crossing_observed": empirical_crossing is not None,
        "measured_crossing_location": empirical_location,
        "warning": " ".join(warnings) if warnings else None,
    }
