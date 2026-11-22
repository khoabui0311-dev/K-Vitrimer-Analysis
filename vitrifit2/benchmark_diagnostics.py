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


def rank_relaxation_models(results: dict, ambiguity_threshold: float = 2.0):
    """Rank converged fits without equating statistical preference to mechanism.

    Delta AICc < 2 denotes models without strong statistical separation.
    A missing/failed fit is not assigned an artificial penalty score.
    """
    if not math.isfinite(ambiguity_threshold) or ambiguity_threshold <= 0:
        raise ValueError("Ambiguity threshold must be positive and finite")
    eligible = [
        (name, float(result["aicc"]))
        for name, result in results.items()
        if result.get("status") == "ok" and result.get("aicc") is not None
        and math.isfinite(float(result["aicc"]))
    ]
    if not eligible:
        return {"preferred": None, "plausible": [], "ranking": [],
                "warning": "No valid AICc comparisons available"}
    eligible.sort(key=lambda item: item[1])
    minimum = eligible[0][1]
    ranking = [{"model": name, "delta_aicc": value - minimum}
               for name, value in eligible]
    plausible = [item["model"] for item in ranking
                 if item["delta_aicc"] < ambiguity_threshold]
    return {
        "preferred": ranking[0]["model"],
        "plausible": plausible,
        "ranking": ranking,
        "warning": (
            "Multiple models statistically plausible; no microscopic mechanism inferred"
            if len(plausible) > 1 else
            "Statistical model preference does not establish microscopic mechanism"
        ),
    }


def assess_parameter_identifiability(time_s, normalized_modulus, model="kww",
                                     condition_limit=1e8):
    """Local numerical Jacobian check for parameter identifiability.

    Uses log-time-constant parameterization to avoid mixed seconds/fractions
    scaling. Reports local conditioning only; does not claim global uniqueness.
    """
    if model not in _MODELS:
        raise ValueError("Unknown relaxation model")
    if not math.isfinite(condition_limit) or condition_limit <= 1:
        raise ValueError("condition_limit must be finite and > 1")
    t = np.asarray(time_s, dtype=float)
    y = np.asarray(normalized_modulus, dtype=float)
    if (t.ndim != 1 or y.ndim != 1 or t.shape != y.shape
            or len(t) < 8 or not np.all(np.isfinite(t))
            or not np.all(np.isfinite(y)) or np.any(t < 0)
            or np.any(np.diff(t) <= 0)):
        raise ValueError("Need >=8 finite ordered observations")
    implementation = _MODELS[model]()
    params, _ = curve_fit(implementation.func, t, y,
                          p0=implementation.get_initial_guess(t, y),
                          bounds=implementation.get_bounds(), maxfev=20000)
    params = np.asarray(params, dtype=float)
    # Transform strictly positive time constants to log(tau).
    tau_indices = {"maxwell": (0,), "kww": (0,),
                   "dual_maxwell": (1, 2)}[model]
    transformed = params.copy()
    for index in tau_indices:
        transformed[index] = math.log(params[index])

    def prediction(z):
        physical = z.copy()
        for index in tau_indices:
            physical[index] = math.exp(z[index])
        return np.asarray(implementation.func(t, *physical), dtype=float)

    columns = []
    for i in range(len(transformed)):
        h = 1e-5 * max(1.0, abs(transformed[i]))
        plus, minus = transformed.copy(), transformed.copy()
        plus[i] += h
        minus[i] -= h
        columns.append((prediction(plus) - prediction(minus)) / (2 * h))
    jacobian = np.column_stack(columns)
    singular = np.linalg.svd(jacobian, compute_uv=False)
    condition = (float(singular[0] / singular[-1])
                 if singular[-1] > 0 else float("inf"))
    identifiable = bool(np.isfinite(condition) and condition < condition_limit)
    return {
        "model": model,
        "parameters": [float(p) for p in params],
        "jacobian_condition_number": condition,
        "singular_values": [float(v) for v in singular],
        "locally_identifiable": identifiable,
        "warning": (None if identifiable else
                    "Poor local parameter identifiability; report intervals and "
                    "avoid mechanistic interpretation"),
    }
