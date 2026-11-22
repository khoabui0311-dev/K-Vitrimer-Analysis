"""Conservative DMA temperature-ramp and DSC transition screening.

Outputs are descriptive measurements, not unqualified Tg assignments.
No baseline subtraction, heat-flow normalization or onset extrapolation is
performed without explicit instrument and method metadata.
"""
from __future__ import annotations

import numpy as np


def _arrays(x, *ys):
    values = [np.asarray(v, dtype=float) for v in (x, *ys)]
    if (any(v.ndim != 1 or len(v) < 4 for v in values)
            or any(v.shape != values[0].shape for v in values)
            or any(not np.all(np.isfinite(v)) for v in values)):
        raise ValueError("At least four paired finite observations required")
    if np.any(np.diff(values[0]) <= 0):
        raise ValueError("Temperature must be strictly increasing; sort or split cycles first")
    return values


def analyze_dma_ramp(temperature_c, storage_modulus, loss_modulus, *,
                     modulus_unit="Pa", tan_delta=None):
    """Return measured E', E'', tan delta and observed tan-delta peak."""
    scales = {"Pa": 1.0, "kPa": 1e3, "MPa": 1e6, "GPa": 1e9}
    if modulus_unit not in scales:
        raise ValueError("DMA modulus unit must be Pa, kPa, MPa or GPa")
    t, ep, epp = _arrays(temperature_c, storage_modulus, loss_modulus)
    ep, epp = ep * scales[modulus_unit], epp * scales[modulus_unit]
    if np.any(ep <= 0) or np.any(epp < 0) or not np.all(np.isfinite(ep + epp)):
        raise ValueError("DMA moduli must be finite with E'>0 and E''>=0")
    measured = epp / ep
    if tan_delta is not None:
        provided = np.asarray(tan_delta, dtype=float)
        if provided.shape != t.shape or not np.all(np.isfinite(provided)):
            raise ValueError("Invalid supplied tan delta")
        discrepancy = float(np.max(np.abs(provided - measured)))
    else:
        discrepancy = None
    # Report only interior peaks; an endpoint maximum is not evidence of
    # a captured transition in the observed temperature window.
    peak_idx = int(np.argmax(measured))
    peak = float(t[peak_idx]) if 0 < peak_idx < len(t)-1 else None
    return {"temperature_c": t.tolist(), "storage_modulus_pa": ep.tolist(),
            "loss_modulus_pa": epp.tolist(), "tan_delta": measured.tolist(),
            "tan_delta_peak_temperature_c": peak,
            "tan_delta_peak_is_interior": peak is not None,
            "provided_tan_delta_max_absolute_difference": discrepancy,
            "warning": ("Tan-delta peak is an observed DMA alpha-relaxation candidate, "
                        "not a DSC Tg onset; frequency and heating rate matter. "
                        "No extrapolated onset is inferred.")}


def analyze_dsc_trace(temperature_c, heat_flow, *,
                      heat_flow_unit="mW", heating_rate_c_min=None):
    """Inspect a monotonic DSC segment without inventing Tg or enthalpy."""
    if heat_flow_unit not in {"mW", "W", "W/g", "mW/mg"}:
        raise ValueError("Explicit supported heat-flow unit required")
    t, q = _arrays(temperature_c, heat_flow)
    if heating_rate_c_min is not None and (
            not np.isfinite(heating_rate_c_min) or heating_rate_c_min <= 0):
        raise ValueError("Heating rate must be positive")
    slope = np.gradient(q, t)
    return {"temperature_c": t.tolist(), "heat_flow": q.tolist(),
            "heat_flow_unit": heat_flow_unit,
            "heating_rate_c_min": heating_rate_c_min,
            "max_abs_heat_flow_slope_temperature_c":
                float(t[int(np.argmax(np.abs(slope)))]),
            "t_g_onset_c": None, "enthalpy_j_g": None,
            "warning": ("Maximum heat-flow slope is not a validated Tg onset. "
                        "Tg and enthalpy require baseline selection, heat-flow sign "
                        "convention, sample mass and validated transition windows. "
                        "No thermal transition is automatically assigned.")}
