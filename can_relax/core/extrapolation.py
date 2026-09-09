"""Explicit Maxwell-equivalent viscosity-threshold extrapolation."""
import numpy as np


def maxwell_equivalent_tv(slope, intercept, modulus_mpa):
    """Return Celsius at G*tau=10^12 Pa s, or NaN if no physical cooling root.

    slope is d ln(tau) / d(1/T). This is a characteristic-time proxy, not
    an integral-viscosity estimate for stretched or multimode relaxation.
    """
    if not np.all(np.isfinite([slope, intercept, modulus_mpa])) or slope <= 0 or modulus_mpa <= 0:
        return np.nan
    denominator = np.log(1e6) - np.log(modulus_mpa) - intercept
    if denominator <= 0:
        return np.nan
    temperature = slope / denominator
    return float(temperature - 273.15) if np.isfinite(temperature) else np.nan
