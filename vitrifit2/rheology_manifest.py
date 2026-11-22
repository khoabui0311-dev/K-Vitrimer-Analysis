"""Reproducible JSON manifest for a specimen-centric rheology analysis.

No external network, paid services, or nonstandard dependencies.
"""
from __future__ import annotations

import json

from .rheology_history import _analysis_context
from .sample_profile import get_measurement_file


def build_rheology_manifest(store, analysis_ids, *, include_results=True):
    """Export an auditable snapshot with verified raw-file digests.

    This JSON manifest does not embed raw file bytes; the content-addressed
    originals remain in the local store and must accompany external archiving.
    """
    if not isinstance(analysis_ids, (list, tuple)) or not analysis_ids:
        raise ValueError("At least one analysis ID required")
    if len(set(analysis_ids)) != len(analysis_ids):
        raise ValueError("Duplicate analysis IDs")
    items = []
    for aid in analysis_ids:
        context = _analysis_context(store, aid)
        a = context["analysis"]
        original = get_measurement_file(store, a["file_id"])
        entry = {
            "analysis_id": a["analysis_id"],
            "measurement_id": a["measurement_id"],
            "specimen_id": context["specimen_id"],
            "sample_id": context["sample_id"],
            "sample_name": context["sample_name"],
            "technique": "Rheology",
            "method": a["method"],
            "measurement_conditions": context["conditions"],
            "algorithm_version": a["algorithm_version"],
            "analysis_configuration": a["config"],
            "raw_file_id": a["file_id"],
            "raw_file_sha256": a["source_sha256"],
            "raw_file_byte_count": len(original),
        }
        if include_results:
            entry["results"] = a["results"]
        items.append(entry)
    return {"schema_version": "vitrifit2-rheology-manifest-1",
            "raw_files_embedded": False,
            "analyses": items,
            "warning": "Preserve original raw files separately; manifest alone cannot reproduce instrument acquisition."}


def export_rheology_manifest_json(store, analysis_ids, *, include_results=True):
    return json.dumps(
        build_rheology_manifest(store, analysis_ids, include_results=include_results),
        allow_nan=False, sort_keys=True, indent=2).encode("utf-8")
