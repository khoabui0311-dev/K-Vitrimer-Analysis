"""Technique-independent, immutable sample-analysis provenance export.

This manifest is metadata + analysis, not a substitute for raw source bytes.
It supports rheology, DMA, DSC and tensile records without a separate schema.
"""
from __future__ import annotations

import json

from .persistence import _json
from .rheology_workflow import _ensure_analysis_schema
from .sample_profile import get_measurement_file


def export_sample_analysis_manifest(store, analysis_ids, *, include_results=True):
    if not isinstance(analysis_ids, (list, tuple)) or not analysis_ids:
        raise ValueError("At least one analysis ID required")
    if any(not isinstance(a, str) or not a for a in analysis_ids):
        raise ValueError("Invalid analysis ID")
    if len(set(analysis_ids)) != len(analysis_ids):
        raise ValueError("Duplicate analysis IDs")
    _ensure_analysis_schema(store)
    analyses = []
    for aid in analysis_ids:
        with store._db() as db:
            row = store._require(db, "v2_measurement_analyses", aid)
            source = store._require(db, "v2_measurement_files", row["file_id"])
            measurement = store._require(db, "v2_measurements", row["measurement_id"])
            specimen = store._require(db, "v2_specimens", measurement["specimen_id"])
            sample = store._require(db, "samples", specimen["sample_id"])
            project = store._require(db, "projects", sample["project_id"])
        # Fail export rather than silently attesting to a missing/corrupt blob.
        get_measurement_file(store, row["file_id"])
        item = {
            "analysis_id": row["id"], "created_at": row["created_at"],
            "method": row["method"], "algorithm_version": row["algorithm_version"],
            "config": json.loads(row["config_json"]),
            "project_id": project["id"], "project_name": project["name"],
            "sample_id": sample["id"], "sample_name": sample["name"],
            "specimen_id": specimen["id"], "specimen_label": specimen["label"],
            "specimen_metadata": json.loads(specimen["metadata_json"]),
            "measurement_id": measurement["id"],
            "technique": measurement["technique"],
            "measurement_method": measurement["method"],
            "measurement_conditions": json.loads(measurement["conditions_json"]),
            "source_file_id": source["id"],
            "source_filename": source["filename"],
            "source_sha256": source["sha256"],
            "source_byte_count": source["byte_count"],
        }
        if include_results:
            item["results"] = json.loads(row["results_json"])
        analyses.append(item)
    return _json({
        "format": "vitrifit2-sample-analysis-manifest-v1",
        "contains_raw_bytes": False,
        "source_integrity_verified": True,
        "analyses": analyses,
        "warning": ("Export original raw files or a complete workspace backup "
                    "alongside this manifest for full reproducibility."),
    }).encode("utf-8")
