"""Persisted rheology analysis history, reprocessing and sample comparisons.

All records refer to immutable source files. No old analysis is overwritten.
Comparison requires explicitly compatible measurement conditions and units.
"""
from __future__ import annotations

import json
import math
from uuid import uuid4

from .persistence import _json, _now
from .rheology_workflow import (
    _ensure_analysis_schema, _parse_columns, get_rheology_analysis,
)
from .sample_profile import get_measurement_file
from .frequency_sweep import analyze_frequency_sweep
from .lvr_screening import assess_oscillatory_lvr
from .lvr_compatibility import assess_lvr_compatibility


def list_rheology_analyses(store, measurement_id):
    """Return ordered history without replacing any prior result."""
    _ensure_analysis_schema(store)
    with store._db() as db:
        row = store._require(db, "v2_measurements", measurement_id)
        if row["technique"] != "Rheology":
            raise ValueError("Measurement is not rheology")
        analyses = db.execute(
            "SELECT id FROM v2_measurement_analyses WHERE measurement_id=? "
            "ORDER BY created_at,id", (measurement_id,)).fetchall()
    return [get_rheology_analysis(store, a["id"]) for a in analyses]


def reanalyze_rheology_file(store, analysis_id, *, plateau_points=None,
                            departure_fraction=None, max_plateau_cv=None):
    """Create a new LVR analysis from the same immutable raw file.

    Frequency sweep is intentionally excluded: its algorithm has no
    configurable fit parameters here. No source file is reattached.
    """
    previous = get_rheology_analysis(store, analysis_id)
    if previous["method"] != "amplitude_sweep":
        raise ValueError("Reanalysis settings are supported for amplitude sweeps only")
    config = dict(previous["config"])
    for key, value in (
        ("plateau_points", plateau_points),
        ("departure_fraction", departure_fraction),
        ("max_plateau_cv", max_plateau_cv),
    ):
        if value is not None:
            config[key] = value
    raw = get_measurement_file(store, previous["file_id"])
    data = _parse_columns(raw, config["columns"])
    scales = {"Pa": 1.0, "kPa": 1e3, "MPa": 1e6}
    if config["modulus_unit"] not in scales:
        raise ValueError("Unsupported modulus unit")
    results = assess_oscillatory_lvr(
        data["strain_percent"],
        [v * scales[config["modulus_unit"]] for v in data["storage_modulus"]],
        plateau_points=config["plateau_points"],
        departure_fraction=config["departure_fraction"],
        max_plateau_cv=config["max_plateau_cv"])
    key = uuid4().hex
    with store._db() as db:
        db.execute(
            "INSERT INTO v2_measurement_analyses VALUES (?,?,?,?,?,?,?,?)",
            (key, previous["measurement_id"], previous["file_id"],
             previous["method"], "rheology_csv_v1", _json(config),
             _json(results), _now()))
    return key


def _analysis_context(store, analysis_id):
    analysis = get_rheology_analysis(store, analysis_id)
    with store._db() as db:
        measurement = store._require(db, "v2_measurements",
                                     analysis["measurement_id"])
        specimen = store._require(db, "v2_specimens", measurement["specimen_id"])
        sample = store._require(db, "samples", specimen["sample_id"])
    return {"analysis": analysis, "measurement_id": measurement["id"],
            "specimen_id": specimen["id"], "sample_id": sample["id"],
            "sample_name": sample["name"], "method": measurement["method"],
            "conditions": json.loads(measurement["conditions_json"])}


def compare_rheology_analyses(store, analysis_ids, *, required_condition_keys):
    """Return auditable comparison, not a fitted master curve.

    The caller explicitly chooses condition keys (e.g. temperature_c,
    frequency_hz, strain_percent, geometry_id, material_state_id).
    Missing values are *never* considered equal. Every source is retained.
    """
    if not isinstance(analysis_ids, (list, tuple)) or len(analysis_ids) < 2:
        raise ValueError("Select at least two analyses")
    if len(set(analysis_ids)) != len(analysis_ids):
        raise ValueError("Duplicate analysis IDs are not allowed")
    if not isinstance(required_condition_keys, (list, tuple)) or not required_condition_keys:
        raise ValueError("Explicit comparison condition keys required")
    if any(not isinstance(k, str) or not k.strip() for k in required_condition_keys):
        raise ValueError("Invalid comparison condition key")
    if len(set(required_condition_keys)) != len(required_condition_keys):
        raise ValueError("Duplicate comparison keys")
    contexts = [_analysis_context(store, aid) for aid in analysis_ids]
    methods = {c["method"] for c in contexts}
    if len(methods) != 1:
        raise ValueError("Cannot compare different rheology methods directly")
    reference = contexts[0]["conditions"]
    mismatch = []
    for key in required_condition_keys:
        if key not in reference or any(
                key not in c["conditions"] or c["conditions"][key] != reference[key]
                for c in contexts[1:]):
            mismatch.append(key)
    return {"status": "conditions_matched" if not mismatch else "incompatible_conditions",
            "mismatched_or_missing_keys": mismatch,
            "required_condition_keys": list(required_condition_keys),
            "method": contexts[0]["method"],
            "analyses": contexts,
            "warning": "Condition equality is exact metadata equality, not evidence of equivalent specimen history, LVR or uncertainty."}


def check_frequency_sweep_lvr(store, frequency_analysis_id, lvr_analysis_id,
                              *, temperature_tolerance_c=0.5,
                              frequency_relative_tolerance=0.01):
    """Evaluate LVR evidence for a *single-frequency* oscillatory measurement.

    A frequency sweep spans frequencies. An LVR sweep at one frequency cannot
    validate the entire sweep; caller must provide frequency_hz for a specific
    frequency point in the measurement conditions.
    """
    frequency = _analysis_context(store, frequency_analysis_id)
    lvr = _analysis_context(store, lvr_analysis_id)
    if frequency["method"] != "frequency_sweep" or lvr["method"] != "amplitude_sweep":
        raise ValueError("Require frequency-sweep and amplitude-sweep analyses")
    fcond, lcond = frequency["conditions"], lvr["conditions"]
    required_f = ("temperature_c", "frequency_hz", "strain_percent",
                  "geometry_id", "material_state_id")
    required_l = ("temperature_c", "frequency_hz", "geometry_id",
                  "material_state_id")
    if any(k not in fcond for k in required_f) or any(k not in lcond for k in required_l):
        return {"status": "not_directly_verified",
                "reason": "Missing required measurement metadata",
                "step_strain_verified": False,
                "supporting_oscillatory_evidence": False}
    return assess_lvr_compatibility(
        lvr["analysis"]["results"],
        applied_strain_percent=fcond["strain_percent"],
        experiment_mode="oscillatory_shear",
        temperature_c=fcond["temperature_c"],
        frequency_hz=fcond["frequency_hz"],
        specimen_id=frequency["specimen_id"],
        geometry_id=fcond["geometry_id"],
        material_state_id=fcond["material_state_id"],
        lvr_temperature_c=lcond["temperature_c"],
        lvr_frequency_hz=lcond["frequency_hz"],
        lvr_specimen_id=lvr["specimen_id"],
        lvr_geometry_id=lcond["geometry_id"],
        lvr_material_state_id=lcond["material_state_id"],
        temperature_tolerance_c=temperature_tolerance_c,
        frequency_relative_tolerance=frequency_relative_tolerance)
