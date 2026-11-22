"""Persistent thermal CSV analyses for DMA and DSC measurements."""
from __future__ import annotations

import json
from uuid import uuid4

from .persistence import _json, _now
from .rheology_workflow import _ensure_analysis_schema, _parse_columns
from .sample_profile import attach_measurement_file, get_measurement_file
from .thermal_analysis import analyze_dma_ramp, analyze_dsc_trace


def import_thermal_csv(store, measurement_id, filename, raw_bytes, *,
                       method, columns, modulus_unit="Pa",
                       heat_flow_unit="mW", heating_rate_c_min=None):
    _ensure_analysis_schema(store)
    expected = ({"temperature_c", "storage_modulus", "loss_modulus"}
                if method == "temperature_ramp"
                else {"temperature_c", "heat_flow"}
                if method == "calorimetry" else None)
    if not isinstance(columns, dict) or expected is None or set(columns) != expected:
        raise ValueError("Explicit complete DMA or DSC column mapping required")
    with store._db() as db:
        measurement = store._require(db, "v2_measurements", measurement_id)
        if (measurement["method"] != method or
                measurement["technique"] !=
                ("DMA" if method == "temperature_ramp" else "DSC")):
            raise ValueError("Technique/method mismatch")
    data = _parse_columns(raw_bytes, columns)
    if method == "temperature_ramp":
        results = analyze_dma_ramp(
            data["temperature_c"], data["storage_modulus"],
            data["loss_modulus"], modulus_unit=modulus_unit)
    else:
        results = analyze_dsc_trace(
            data["temperature_c"], data["heat_flow"],
            heat_flow_unit=heat_flow_unit,
            heating_rate_c_min=heating_rate_c_min)
    config = {"columns": columns, "modulus_unit": modulus_unit,
              "heat_flow_unit": heat_flow_unit,
              "heating_rate_c_min": heating_rate_c_min}
    file_id = attach_measurement_file(
        store, measurement_id, filename, raw_bytes,
        {"adapter": "explicit_thermal_csv", "method": method})
    aid = uuid4().hex
    with store._db() as db:
        db.execute("INSERT INTO v2_measurement_analyses VALUES (?,?,?,?,?,?,?,?)",
                   (aid, measurement_id, file_id, method, "thermal_csv_v1",
                    _json(config), _json(results), _now()))
    return aid


def get_thermal_analysis(store, analysis_id):
    _ensure_analysis_schema(store)
    with store._db() as db:
        row = store._require(db, "v2_measurement_analyses", analysis_id)
        if row["method"] not in ("temperature_ramp", "calorimetry"):
            raise ValueError("Not a thermal analysis")
        original = store._require(db, "v2_measurement_files", row["file_id"])
    get_measurement_file(store, row["file_id"])
    return {"analysis_id": row["id"], "measurement_id": row["measurement_id"],
            "file_id": row["file_id"], "source_sha256": original["sha256"],
            "method": row["method"], "algorithm_version": row["algorithm_version"],
            "config": json.loads(row["config_json"]),
            "results": json.loads(row["results_json"])}


def list_thermal_analyses(store, measurement_id):
    _ensure_analysis_schema(store)
    with store._db() as db:
        row = store._require(db, "v2_measurements", measurement_id)
        if row["technique"] not in ("DMA", "DSC"):
            raise ValueError("Not a thermal measurement")
        records = db.execute(
            "SELECT id FROM v2_measurement_analyses "
            "WHERE measurement_id=? AND method=? ORDER BY created_at,id",
            (measurement_id, row["method"])).fetchall()
    return [get_thermal_analysis(store, record["id"]) for record in records]
