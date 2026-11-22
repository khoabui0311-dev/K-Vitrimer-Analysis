"""Explicit-column CSV import and persisted rheology analysis workflow.

This is a narrow, auditable adapter, not automatic instrument format detection.
Original bytes are stored first; derived results are versioned by source file.
"""
from __future__ import annotations

import csv
from io import StringIO
import json
from uuid import uuid4

from .frequency_sweep import analyze_frequency_sweep
from .lvr_screening import assess_oscillatory_lvr
from .sample_profile import (
    attach_measurement_file, ensure_sample_profile_schema, get_measurement_file,
)
from .persistence import _json, _now


def _parse_columns(raw_bytes, columns):
    if not isinstance(columns, dict) or not columns:
        raise ValueError("Explicit column mapping is required")
    if not isinstance(raw_bytes, bytes):
        raise TypeError("raw_bytes must be bytes")
    try:
        text = raw_bytes.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("CSV must be UTF-8 encoded") from exc
    reader = csv.DictReader(StringIO(text), strict=True)
    if not reader.fieldnames or len(set(reader.fieldnames)) != len(reader.fieldnames):
        raise ValueError("Missing or duplicate CSV headers")
    if any(not isinstance(c, str) or c not in reader.fieldnames for c in columns.values()):
        raise ValueError("Mapped CSV columns missing")
    try:
        rows = list(reader)
    except csv.Error as exc:
        raise ValueError("Malformed CSV rows") from exc
    if any(None in row for row in rows):
        raise ValueError("CSV row contains more fields than the header")
    if not rows:
        raise ValueError("CSV contains no observations")
    try:
        data = {name: [float(row[column]) for row in rows]
                for name, column in columns.items()}
    except (TypeError, ValueError, KeyError) as exc:
        raise ValueError("Non-numeric or missing mapped CSV values") from exc
    return data


def _ensure_analysis_schema(store):
    ensure_sample_profile_schema(store)
    with store._db() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS v2_measurement_analyses (
            id TEXT PRIMARY KEY,
            measurement_id TEXT NOT NULL REFERENCES v2_measurements(id),
            file_id TEXT NOT NULL REFERENCES v2_measurement_files(id),
            method TEXT NOT NULL,
            algorithm_version TEXT NOT NULL,
            config_json TEXT NOT NULL,
            results_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_v2_analyses_measurement
            ON v2_measurement_analyses(measurement_id);
        """)


def analyze_rheology_csv(store, measurement_id, filename, raw_bytes, *,
                         method, columns, frequency_unit="Hz",
                         modulus_unit="Pa", plateau_points=5,
                         departure_fraction=0.05, max_plateau_cv=0.03):
    """Validate/compute before committing file and analysis records.

    Method must match the existing measurement; units must be explicit.
    """
    _ensure_analysis_schema(store)
    required = ({"frequency", "storage_modulus", "loss_modulus"}
                if method == "frequency_sweep"
                else {"strain_percent", "storage_modulus"}
                if method == "amplitude_sweep" else None)
    if required is None or not isinstance(columns, dict) or set(columns) != required:
        raise ValueError("Unsupported rheology method or incomplete column mapping")
    with store._db() as db:
        measurement = store._require(db, "v2_measurements", measurement_id)
        if measurement["technique"] != "Rheology" or measurement["method"] != method:
            raise ValueError("Measurement technique/method mismatch")
    data = _parse_columns(raw_bytes, columns)
    if method == "frequency_sweep":
        result = analyze_frequency_sweep(
            data["frequency"], data["storage_modulus"], data["loss_modulus"],
            frequency_unit=frequency_unit, modulus_unit=modulus_unit)
    else:
        scale = {"Pa": 1, "kPa": 1e3, "MPa": 1e6}
        if modulus_unit not in scale:
            raise ValueError("Unsupported modulus unit")
        result = assess_oscillatory_lvr(
            data["strain_percent"],
            [v * scale[modulus_unit] for v in data["storage_modulus"]],
            plateau_points=plateau_points,
            departure_fraction=departure_fraction,
            max_plateau_cv=max_plateau_cv)
    # Preserve original observation order in analysis results for inspectable
    # browser plots. Raw bytes remain the authoritative immutable source.
    if method == "amplitude_sweep":
        scale = {"Pa": 1, "kPa": 1e3, "MPa": 1e6}[modulus_unit]
        result["observations"] = {
            "strain_percent": data["strain_percent"],
            "storage_modulus_pa": [v * scale for v in data["storage_modulus"]]}
    config = {"columns": columns, "frequency_unit": frequency_unit,
              "modulus_unit": modulus_unit, "plateau_points": plateau_points,
              "departure_fraction": departure_fraction,
              "max_plateau_cv": max_plateau_cv}
    file_id = attach_measurement_file(store, measurement_id, filename, raw_bytes,
                                      {"adapter": "explicit_csv", "method": method})
    analysis_id = uuid4().hex
    with store._db() as db:
        db.execute("INSERT INTO v2_measurement_analyses VALUES (?,?,?,?,?,?,?,?)",
                   (analysis_id, measurement_id, file_id, method,
                    "rheology_csv_v2", _json(config), _json(result), _now()))
    return analysis_id


def get_rheology_analysis(store, analysis_id):
    _ensure_analysis_schema(store)
    with store._db() as db:
        row = store._require(db, "v2_measurement_analyses", analysis_id)
        file = store._require(db, "v2_measurement_files", row["file_id"])
    # Recheck raw-file integrity whenever reproducing an analysis.
    get_measurement_file(store, row["file_id"])
    return {"analysis_id": analysis_id, "measurement_id": row["measurement_id"],
            "file_id": row["file_id"], "source_sha256": file["sha256"],
            "method": row["method"], "algorithm_version": row["algorithm_version"],
            "config": json.loads(row["config_json"]),
            "results": json.loads(row["results_json"])}
