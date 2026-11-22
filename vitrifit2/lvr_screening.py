"""Conservative, unit-explicit oscillatory LVR screening.

This estimates departure from a user-selected low-amplitude storage-modulus
plateau. It does NOT certify linear step-strain stress relaxation.
"""
from __future__ import annotations

import numpy as np


def assess_oscillatory_lvr(strain_percent, storage_modulus_pa, *,
                           plateau_points=5, departure_fraction=0.05,
                           max_plateau_cv=0.03):
    """Return measured LVR screening boundary or an indeterminate status.

    Strain is oscillatory amplitude in percent, not fractional strain.
    The first plateau_points *sorted* measurements define the candidate
    plateau. Only the first departure is reported; no interpolation through
    unmeasured strain ranges or temperatures is implied.
    """
    x = np.asarray(strain_percent, dtype=float)
    g = np.asarray(storage_modulus_pa, dtype=float)
    if (x.ndim != 1 or g.ndim != 1 or x.shape != g.shape
            or len(x) < 4 or not np.all(np.isfinite(x))
            or not np.all(np.isfinite(g)) or np.any(x <= 0)
            or np.any(g <= 0) or len(np.unique(x)) != len(x)):
        raise ValueError("Need >=4 finite positive unique strain/modulus pairs")
    if (not isinstance(plateau_points, int) or isinstance(plateau_points, bool)
            or plateau_points < 3 or plateau_points >= len(x)):
        raise ValueError("plateau_points must be >=3 and leave test points")
    if not np.isfinite(departure_fraction) or not 0 < departure_fraction < 1:
        raise ValueError("departure_fraction must be in (0,1)")
    if not np.isfinite(max_plateau_cv) or not 0 < max_plateau_cv < 1:
        raise ValueError("max_plateau_cv must be in (0,1)")
    order = np.argsort(x)
    x, g = x[order], g[order]
    baseline = float(np.median(g[:plateau_points]))
    cv = float(np.std(g[:plateau_points], ddof=1) / baseline)
    result = {
        "plateau_modulus_pa": baseline,
        "plateau_cv": cv,
        "departure_fraction": float(departure_fraction),
        "plateau_strain_range_percent": [float(x[0]), float(x[plateau_points-1])],
        "first_departure_strain_percent": None,
        "highest_measured_in_range_strain_percent": None,
        "status": "indeterminate",
        "warning": "Oscillatory LVR screening is frequency-, temperature-, geometry- and specimen-dependent; it does not prove step-strain linearity.",
    }
    if cv > max_plateau_cv:
        result["warning"] = "Candidate low-amplitude plateau is unstable; inspect noise, drift and plateau selection. " + result["warning"]
        return result
    departure = np.flatnonzero(
        np.abs(g[plateau_points:] / baseline - 1) > departure_fraction)
    if len(departure):
        idx = int(departure[0] + plateau_points)
        result["status"] = "departure_detected"
        result["first_departure_strain_percent"] = float(x[idx])
        result["highest_measured_in_range_strain_percent"] = float(x[idx-1])
    else:
        result["status"] = "no_departure_in_measured_range"
        result["highest_measured_in_range_strain_percent"] = float(x[-1])
    return result
