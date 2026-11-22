"""Additive sample-centric specimen and measurement metadata for VitriFitStore.

Existing stress-relaxation experiments/curves are untouched. This extension
uses new tables and foreign keys, allowing older SQLite stores to reopen.
"""
from __future__ import annotations

import json
from uuid import uuid4

from .persistence import _json, _now


TECHNIQUES = frozenset(("DMA", "DSC", "Rheology", "Tensile"))
METHODS = frozenset(("stress_relaxation", "amplitude_sweep",
                     "frequency_sweep", "temperature_ramp",
                     "tensile_test", "calorimetry", "other"))


def ensure_sample_profile_schema(store):
    with store._db() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS v2_specimens (
            id TEXT PRIMARY KEY,
            sample_id TEXT NOT NULL REFERENCES samples(id),
            label TEXT NOT NULL,
            metadata_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS v2_measurements (
            id TEXT PRIMARY KEY,
            specimen_id TEXT NOT NULL REFERENCES v2_specimens(id),
            technique TEXT NOT NULL,
            method TEXT NOT NULL,
            conditions_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_v2_specimens_sample
            ON v2_specimens(sample_id);
        CREATE INDEX IF NOT EXISTS idx_v2_measurements_specimen
            ON v2_measurements(specimen_id);
        """)


def create_specimen(store, sample_id, label, metadata=None):
    ensure_sample_profile_schema(store)
    if not isinstance(label, str) or not label.strip():
        raise ValueError("Specimen label required")
    metadata = {} if metadata is None else metadata
    if not isinstance(metadata, dict):
        raise ValueError("Specimen metadata must be a dictionary")
    key = uuid4().hex
    with store._db() as db:
        store._require(db, "samples", sample_id)
        db.execute("INSERT INTO v2_specimens VALUES (?,?,?,?,?)",
                   (key, sample_id, label.strip(), _json(metadata), _now()))
    return key


def create_measurement(store, specimen_id, technique, method, conditions=None):
    ensure_sample_profile_schema(store)
    if technique not in TECHNIQUES or method not in METHODS:
        raise ValueError("Unsupported technique or method")
    conditions = {} if conditions is None else conditions
    if not isinstance(conditions, dict):
        raise ValueError("Measurement conditions must be a dictionary")
    key = uuid4().hex
    with store._db() as db:
        store._require(db, "v2_specimens", specimen_id)
        db.execute("INSERT INTO v2_measurements VALUES (?,?,?,?,?,?)",
                   (key, specimen_id, technique, method, _json(conditions), _now()))
    return key


def get_sample_profile(store, sample_id):
    """Return only persisted records; missing techniques remain empty lists."""
    ensure_sample_profile_schema(store)
    with store._db() as db:
        sample = store._require(db, "samples", sample_id)
        specimens = db.execute(
            "SELECT * FROM v2_specimens WHERE sample_id=? ORDER BY created_at,id",
            (sample_id,)).fetchall()
        result = {"sample_id": sample_id, "name": sample["name"],
                  "techniques": {technique: [] for technique in sorted(TECHNIQUES)},
                  "specimens": []}
        for specimen in specimens:
            record = {"specimen_id": specimen["id"], "label": specimen["label"],
                      "metadata": json.loads(specimen["metadata_json"]),
                      "measurements": []}
            measurements = db.execute(
                "SELECT * FROM v2_measurements WHERE specimen_id=? ORDER BY created_at,id",
                (specimen["id"],)).fetchall()
            for measurement in measurements:
                item = {"measurement_id": measurement["id"],
                        "specimen_id": specimen["id"],
                        "technique": measurement["technique"],
                        "method": measurement["method"],
                        "conditions": json.loads(measurement["conditions_json"])}
                record["measurements"].append(item)
                result["techniques"][item["technique"]].append(item)
            result["specimens"].append(record)
    return result
