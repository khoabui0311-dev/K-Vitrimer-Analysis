"""Explicit-column tensile analysis for specimen-centred measurements.

Stress uses engineering force/initial area; true stress assumes homogeneous
incompressible uniaxial deformation and is reported as a conditional estimate.
"""
from __future__ import annotations

import math
import numpy as np


def analyze_tensile(displacement_mm, force_n, *, gauge_length_mm,
                    width_mm, thickness_mm, modulus_fit_strain_min=0.0005,
                    modulus_fit_strain_max=0.005, calculate_true=True):
    arrays = (np.asarray(displacement_mm, dtype=float),
              np.asarray(force_n, dtype=float))
    x, force = arrays
    if (x.ndim != 1 or force.ndim != 1 or x.shape != force.shape or len(x) < 4
            or not np.all(np.isfinite(x)) or not np.all(np.isfinite(force))):
        raise ValueError("Need at least four paired finite tensile observations")
    geometry = (gauge_length_mm, width_mm, thickness_mm)
    if any(not isinstance(v, (int, float)) or isinstance(v, bool)
           or not math.isfinite(v) or v <= 0 for v in geometry):
        raise ValueError("Positive initial gauge length, width and thickness required")
    if (not 0 <= modulus_fit_strain_min < modulus_fit_strain_max):
        raise ValueError("Invalid modulus fit window")
    # Displacement zero must be selected by the operator before import.
    strain = x / gauge_length_mm
    if np.any(strain <= -1):
        raise ValueError("Engineering strain <= -1 is physically invalid")
    stress_mpa = force / (width_mm * thickness_mm)
    mask = (strain >= modulus_fit_strain_min) & (strain <= modulus_fit_strain_max)
    modulus = None
    modulus_r2 = None
    if np.count_nonzero(mask) >= 3 and np.ptp(strain[mask]) > 0:
        coeff = np.polyfit(strain[mask], stress_mpa[mask], 1)
        modulus = float(coeff[0])
        predicted = np.polyval(coeff, strain[mask])
        ss_tot = float(np.sum((stress_mpa[mask] - np.mean(stress_mpa[mask])) ** 2))
        if ss_tot > 0:
            modulus_r2 = float(1 - np.sum((stress_mpa[mask] - predicted) ** 2) / ss_tot)
    true_strain = np.log1p(strain) if calculate_true else None
    true_stress = stress_mpa * (1 + strain) if calculate_true else None
    return {
        "engineering_strain": strain.tolist(),
        "engineering_stress_mpa": stress_mpa.tolist(),
        "true_strain_estimate": None if true_strain is None else true_strain.tolist(),
        "true_stress_mpa_estimate": None if true_stress is None else true_stress.tolist(),
        "max_engineering_stress_mpa": float(np.max(stress_mpa)),
        "strain_at_max_stress": float(strain[int(np.argmax(stress_mpa))]),
        "last_recorded_engineering_strain": float(strain[-1]),
        "youngs_modulus_mpa": modulus,
        "modulus_fit_r2": modulus_r2,
        "modulus_fit_points": int(np.count_nonzero(mask)),
        "modulus_fit_window": [modulus_fit_strain_min, modulus_fit_strain_max],
        "warning": ("Crosshead displacement is not necessarily local gauge strain; "
                    "true stress assumes constant volume and uniform deformation. "
                    "Last recorded point is not necessarily fracture. "
                    "Modulus is omitted unless >=3 measured points occur in the specified fit window.")
    }
