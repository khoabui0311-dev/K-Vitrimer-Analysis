"""Persistent explicit CSV tensile workflow, sharing immutable measurement storage."""
from __future__ import annotations

import json
from uuid import uuid4

from .persistence import _json, _now
from .rheology_workflow import _ensure_analysis_schema, _parse_columns
from .sample_profile import attach_measurement_file, get_measurement_file
from .tensile_analysis import analyze_tensile


def import_tensile_csv(store, measurement_id, filename, raw_bytes, *,
                       columns, gauge_length_mm, width_mm, thickness_mm,
                       modulus_fit_strain_min=.0005,
                       modulus_fit_strain_max=.005, calculate_true=True):
    if set(columns) != {"displacement_mm", "force_n"}:
        raise ValueError("Explicit displacement_mm and force_n mappings required")
    _ensure_analysis_schema(store)
    with store._db() as db:
        row = store._require(db, "v2_measurements", measurement_id)
        if row["technique"] != "Tensile" or row["method"] != "tensile_test":
            raise ValueError("Measurement must be a tensile test")
    data = _parse_columns(raw_bytes, columns)
    results = analyze_tensile(
        data["displacement_mm"], data["force_n"],
        gauge_length_mm=gauge_length_mm, width_mm=width_mm,
        thickness_mm=thickness_mm,
        modulus_fit_strain_min=modulus_fit_strain_min,
        modulus_fit_strain_max=modulus_fit_strain_max,
        calculate_true=calculate_true)
    config = {"columns": columns, "gauge_length_mm": gauge_length_mm,
              "width_mm": width_mm, "thickness_mm": thickness_mm,
              "modulus_fit_strain_min": modulus_fit_strain_min,
              "modulus_fit_strain_max": modulus_fit_strain_max,
              "calculate_true": calculate_true,
              "displacement_unit": "mm", "force_unit": "N"}
    file_id = attach_measurement_file(
        store, measurement_id, filename, raw_bytes,
        {"adapter": "explicit_tensile_csv", "method": "tensile_test"})
    aid = uuid4().hex
    with store._db() as db:
        db.execute(
            "INSERT INTO v2_measurement_analyses VALUES (?,?,?,?,?,?,?,?)",
            (aid, measurement_id, file_id, "tensile_test", "tensile_csv_v1",
             _json(config), _json(results), _now()))
    return aid


def get_tensile_analysis(store, analysis_id):
    _ensure_analysis_schema(store)
    with store._db() as db:
        row = store._require(db, "v2_measurement_analyses", analysis_id)
        if row["method"] != "tensile_test":
            raise ValueError("Not a tensile analysis")
        source = store._require(db, "v2_measurement_files", row["file_id"])
    get_measurement_file(store, row["file_id"])
    return {"analysis_id": row["id"], "measurement_id": row["measurement_id"],
            "file_id": row["file_id"], "source_sha256": source["sha256"],
            "method": row["method"], "algorithm_version": row["algorithm_version"],
            "config": json.loads(row["config_json"]),
            "results": json.loads(row["results_json"])}


def list_tensile_analyses(store, measurement_id):
    _ensure_analysis_schema(store)
    with store._db() as db:
        measurement = store._require(db, "v2_measurements", measurement_id)
        if measurement["technique"] != "Tensile":
            raise ValueError("Not a tensile measurement")
        rows = db.execute(
            "SELECT id FROM v2_measurement_analyses "
            "WHERE measurement_id=? AND method='tensile_test' ORDER BY created_at,id",
            (measurement_id,)).fetchall()
    return [get_tensile_analysis(store, row["id"]) for row in rows]
