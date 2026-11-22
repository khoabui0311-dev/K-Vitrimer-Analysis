"""Frequency-sweep calculations with explicit angular-frequency and modulus units.

No TTS or network homogeneity inference is made by this module.
"""
from __future__ import annotations

import numpy as np


def analyze_frequency_sweep(frequency, storage_modulus, loss_modulus, *,
                            frequency_unit="Hz", modulus_unit="Pa"):
    """Return SI-unit arrays, tan(delta), |eta*| and measured-domain crossovers.

    G'=G'' crossovers are linearly interpolated in log(omega) between adjacent
    measured points. A crossover is never extrapolated beyond the data.
    """
    frequency_scale = {"Hz": 2 * np.pi, "rad/s": 1.0}
    modulus_scale = {"Pa": 1., "kPa": 1e3, "MPa": 1e6}
    if frequency_unit not in frequency_scale:
        raise ValueError("frequency_unit must be Hz or rad/s")
    if modulus_unit not in modulus_scale:
        raise ValueError("modulus_unit must be Pa, kPa or MPa")
    f = np.asarray(frequency, dtype=float)
    gp = np.asarray(storage_modulus, dtype=float)
    gpp = np.asarray(loss_modulus, dtype=float)
    if (f.ndim != 1 or gp.ndim != 1 or gpp.ndim != 1
            or f.shape != gp.shape or f.shape != gpp.shape or len(f) < 2
            or not np.all(np.isfinite(f)) or not np.all(np.isfinite(gp))
            or not np.all(np.isfinite(gpp)) or np.any(f <= 0)
            or np.any(gp <= 0) or np.any(gpp < 0)
            or len(np.unique(f)) != len(f)):
        raise ValueError("Need >=2 finite, positive unique frequencies and valid moduli")
    order = np.argsort(f)
    omega = f[order] * frequency_scale[frequency_unit]
    gp = gp[order] * modulus_scale[modulus_unit]
    gpp = gpp[order] * modulus_scale[modulus_unit]
    difference = gp - gpp
    crossovers = []
    log_omega = np.log(omega)
    for i in range(len(omega)-1):
        if difference[i] == 0:
            crossovers.append(float(omega[i]))
        if difference[i] * difference[i+1] < 0:
            # Linear interpolation of modulus difference on log-frequency
            # coordinates remains finite even when G'' is zero.
            fraction = -difference[i] / (difference[i+1]-difference[i])
            crossovers.append(float(np.exp(
                log_omega[i] + fraction*(log_omega[i+1]-log_omega[i]))))
    if difference[-1] == 0:
        crossovers.append(float(omega[-1]))
    return {
        "angular_frequency_rad_s": omega.tolist(),
        "storage_modulus_pa": gp.tolist(),
        "loss_modulus_pa": gpp.tolist(),
        "tan_delta": (gpp/gp).tolist(),
        "complex_viscosity_pa_s": (np.hypot(gp, gpp)/omega).tolist(),
        "crossover_angular_frequency_rad_s": crossovers,
        "crossover_frequency_hz": (np.asarray(crossovers)/(2*np.pi)).tolist(),
        "warning": "Crossovers are interpolated only between measured points; validity depends on linear oscillatory conditions, instrument limits and specimen state.",
    }
