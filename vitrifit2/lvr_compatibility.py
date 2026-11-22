"""Conservative matching of oscillatory LVR evidence to measurement conditions.

A compatible amplitude sweep supports an oscillatory measurement only; it
never independently verifies linear step-strain relaxation.
"""
from __future__ import annotations

import math


def assess_lvr_compatibility(lvr_result, *, applied_strain_percent,
                             experiment_mode, temperature_c, frequency_hz,
                             specimen_id, geometry_id, material_state_id,
                             lvr_temperature_c, lvr_frequency_hz,
                             lvr_specimen_id, lvr_geometry_id,
                             lvr_material_state_id, lvr_mode="oscillatory_shear",
                             temperature_tolerance_c=0.5,
                             frequency_relative_tolerance=0.01):
    """Check conditions and the *measured* conservative LVR amplitude bound.

    IDs must refer to the same physical specimen, geometry and material
    state. No temperature/frequency interpolation or sample-wide inference.
    """
    numbers = (applied_strain_percent, temperature_c, frequency_hz,
               lvr_temperature_c, lvr_frequency_hz, temperature_tolerance_c,
               frequency_relative_tolerance)
    if any(not isinstance(v, (int, float)) or isinstance(v, bool)
           or not math.isfinite(v) for v in numbers):
        raise ValueError("Conditions must be finite numeric values")
    if (applied_strain_percent <= 0 or frequency_hz <= 0 or lvr_frequency_hz <= 0
            or temperature_tolerance_c < 0
            or not 0 <= frequency_relative_tolerance < 1):
        raise ValueError("Invalid strain, frequency or matching tolerance")
    if not isinstance(lvr_result, dict):
        raise ValueError("lvr_result must be a screening report")
    result = {
        "status": "not_directly_verified",
        "reason": None,
        "step_strain_verified": False,
        "supporting_oscillatory_evidence": False,
    }
    if experiment_mode != "oscillatory_shear" or lvr_mode != "oscillatory_shear":
        result["reason"] = "Oscillatory shear LVR does not certify step-strain or tensile linearity"
        return result
    if (not all(isinstance(v, str) and v.strip() for v in (
            specimen_id, geometry_id, material_state_id,
            lvr_specimen_id, lvr_geometry_id, lvr_material_state_id))
            or specimen_id != lvr_specimen_id
            or geometry_id != lvr_geometry_id
            or material_state_id != lvr_material_state_id):
        result["reason"] = "Specimen, geometry or material state differs or is unknown"
        return result
    if abs(temperature_c-lvr_temperature_c) > temperature_tolerance_c:
        result["reason"] = "Temperature not directly matched; no interpolation allowed"
        return result
    if abs(frequency_hz-lvr_frequency_hz) > (
            frequency_relative_tolerance*lvr_frequency_hz):
        result["reason"] = "Oscillatory frequency not directly matched"
        return result
    if lvr_result.get("status") not in (
            "departure_detected", "no_departure_in_measured_range"):
        result["reason"] = "No reliable low-amplitude plateau"
        return result
    limit = lvr_result.get("highest_measured_in_range_strain_percent")
    if (not isinstance(limit, (int, float)) or isinstance(limit, bool)
            or not math.isfinite(limit) or limit <= 0):
        result["reason"] = "No valid measured amplitude bound"
        return result
    result["supporting_oscillatory_evidence"] = True
    if applied_strain_percent <= limit:
        result["status"] = "verified_oscillatory_lvr"
        result["reason"] = "Amplitude within screened bound under matched conditions"
    elif (lvr_result.get("status") == "departure_detected"
          and applied_strain_percent >=
          lvr_result.get("first_departure_strain_percent", float("inf"))):
        result["status"] = "outside_measured_lvr"
        result["reason"] = "Amplitude at or beyond measured departure"
    else:
        result["reason"] = "Amplitude falls between last in-range and first out-of-range measurements"
    return result
