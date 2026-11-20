"""Run existing scientific models on pinned, individually trimmed curve revisions.

Reuses CurveAnalyzer and the v1 crossing semantics without its automatic global
trim. Original measured time origin and unnormalized modulus remain available.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from can_relax.core.analyzer import CurveAnalyzer
from can_relax.core.processing import DataProcessor
from can_relax.core.models import PRONY, TAU_INDICES
from can_relax.core.observations import relaxation_crossing
from .persistence import VitriFitStore


class SelectionProcessor(DataProcessor):
    """Pass explicit user selections through to the v1 fitter without auto trimming."""

    def trim_curve(self, t, g, max_points=250):
        t = np.asarray(t, dtype=float)
        g = np.asarray(g, dtype=float)
        if (t.ndim != 1 or g.shape != t.shape or len(t) < self.min_points
                or not np.all(np.isfinite(t)) or not np.all(np.isfinite(g))
                or np.any(t < 0) or np.any(g <= 0) or np.any(np.diff(t) <= 0)):
            return None, None, None
        g0 = float(g[0])
        normalized = g / g0
        if max_points is not None:
            t, normalized = self.downsample(t, normalized, max_points)
        return t, normalized, g0


def fit_saved_curve(store: VitriFitStore, curve_id: str, model: str = "Single_KWW",
                    plateau_mode: str = "Zero", fixed_plateau_mpa: float = 0,
                    component: str = "characteristic") -> dict:
    """Persist an independent scientific fit, keyed by the current trim revision."""
    if model not in ("Maxwell", "Single_KWW", "Dual_KWW", PRONY):
        raise ValueError("Unknown model")
    if component not in ("characteristic", "fast", "slow"):
        raise ValueError("Unknown relaxation-time component")
    if model in ("Maxwell", "Single_KWW") and component != "characteristic":
        raise ValueError("Single-mode models have only characteristic tau")
    if model in ("Dual_KWW", PRONY) and component == "characteristic":
        raise ValueError("Select the fast or slow component for multi-mode models")

    curve = store.get_curve(curve_id)
    t = np.asarray(curve["time_s"], dtype=float)[curve["mask"]]
    g = np.asarray(curve["modulus_mpa"], dtype=float)[curve["mask"]]
    if len(t) < 8:
        raise ValueError("At least eight measured points are required for fitting")
    if np.any(g <= 0):
        raise ValueError("Selected data includes non-positive modulus; exclude artifacts explicitly")
    # Fitter must receive strictly increasing time. Do not reindex source data:
    # mask indices always refer to immutable instrument row positions.
    if np.any(np.diff(t) <= 0):
        raise ValueError("Selected raw time is not strictly increasing; inspect and exclude duplicates")
    raw_crossing = relaxation_crossing(t, g)
    fitter = CurveAnalyzer()
    fitter.processor = SelectionProcessor()
    raw = pd.DataFrame({"Time": t, "Modulus": g})
    analyzed = fitter.fit_one_temp(curve["temperature_c"], raw, fit_model=model,
                                   plateau_mode=plateau_mode,
                                   fixed_plateau=float(fixed_plateau_mpa))
    if not analyzed.get("Valid") or not analyzed.get("Fits", {}).get(model, {}).get("success"):
        raise ValueError(str(analyzed.get("Reason", "Nonlinear fit failed")))
    fit = analyzed["Fits"][model]
    params = np.asarray(fit["popt"], dtype=float)
    indices = TAU_INDICES[model]
    if len(indices) == 1:
        tau = float(params[indices[0]])
    else:
        tau = float(params[indices[0 if component == "fast" else -1]])
    definition = f"fit:{model}:{component}"
    beta = float(params[1]) if model == "Single_KWW" else None
    fit_time = np.asarray(analyzed["Raw"]["t"], dtype=float)
    predicted = np.asarray(fit["curve"], dtype=float)
    result = {
        "tau_s": tau, "beta": beta,
        "r2": float(fit["r2"]), "aicc": float(fit["aic"]), "bic": float(fit["bic"]),
        "parameters": [float(v) for v in params],
        "flags": list(fit.get("flags", [])), "warnings": list(analyzed.get("Warnings", [])),
        "raw_1e": {
            "status": raw_crossing["status"],
            "tau_s": float(raw_crossing["tau"]) if raw_crossing["status"] == "observed" else None,
            "crossing_s": float(raw_crossing["crossing_time"])
            if raw_crossing["status"] == "observed" else None,
        },
        "reference_time_s": float(fit_time[0]),
        "reference_modulus_mpa": float(analyzed["Raw"]["G0"]),
        "retained_points": len(t),
        "fit_time_s": fit_time.tolist(),
        "fit_normalized_observed": np.asarray(analyzed["Raw"]["g"], dtype=float).tolist(),
        "fit_normalized_prediction": predicted.tolist(),
        "revision_id": curve["active_revision_id"],
    }
    config = {"plateau_mode": plateau_mode,
              "fixed_plateau_mpa": float(fixed_plateau_mpa),
              "component": component, "origin": "original_elapsed_time",
              "preprocessing": "manual_per_curve_mask", "scientific_engine": "can_relax.CurveAnalyzer"}
    run_id = store.save_analysis(curve_id, model, definition, config, result)
    return {"run_id": run_id, "model": model, "tau_definition": definition,
            "is_current": True, "results": result}


def suggest_automatic_trim(store: VitriFitStore, curve_id: str) -> dict:
    """Propose (but never apply) boundaries from the existing v1 algorithm.

    V1 also sorts, averages duplicate times, and filters invalid modulus.
    This returns only a contiguous range; internal artifact exclusions are not
    implied, and a manual fit still checks for nonpositive/duplicate data.
    """
    curve = store.get_curve(curve_id)
    original_t = np.asarray(curve["time_s"], dtype=float)
    original_g = np.asarray(curve["modulus_mpa"], dtype=float)
    proposed_t, _, _ = DataProcessor().trim_curve(original_t, original_g,
                                                  max_points=None)
    if proposed_t is None:
        raise ValueError("Automatic trim could not identify a valid measurement window")
    start, end = float(proposed_t[0]), float(proposed_t[-1])
    return {"curve_id": curve_id, "mode": "keep", "start_s": start,
            "end_s": end, "proposed_points": int(len(proposed_t)),
            "applied": False,
            "note": "Suggested using the legacy heuristic. Inspect and apply for this curve only; no points were changed."}
