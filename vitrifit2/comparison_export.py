"""Reproducible, provenance-aware export of cross-sample analysis comparisons.

Exports all saved result fields as JSON (rather than guessing a common tau
definition across Maxwell/KWW models). CSV is suitable for spreadsheet import.
"""
from __future__ import annotations

import csv
from io import StringIO
import json

from .persistence import VitriFitStore

COLUMNS = (
    "comparison_id", "comparison_name", "comparison_mode", "run_id",
    "project_id", "project_name", "sample_id", "sample_name",
    "curve_id", "source_curve_id", "temperature_c", "model",
    "tau_definition", "revision_id", "is_current",
    "config_json", "results_json",
)


def comparison_rows(store: VitriFitStore, comparison_id: str) -> list[dict]:
    """Return rows in saved run order, retaining stale analysis provenance.

    A stale run remains exportable but is marked is_current=False. Never
    silently replace it with a newer analysis, which would alter conclusions.
    """
    comparison = store.get_comparison(comparison_id)
    metadata = {run["id"]: run for run in store.list_analysis_runs()}
    rows = []
    for run_id in comparison["run_ids"]:
        run = store.get_analysis(run_id)
        meta = metadata[run_id]
        rows.append({
            "comparison_id": comparison["id"],
            "comparison_name": comparison["name"],
            "comparison_mode": comparison["mode"],
            "run_id": run_id,
            "project_id": meta["project_id"],
            "project_name": meta["project_name"],
            "sample_id": meta["sample_id"],
            "sample_name": meta["sample_name"],
            "curve_id": run["curve_id"],
            "source_curve_id": meta["source_curve_id"],
            "temperature_c": meta["temperature_c"],
            "model": run["model"],
            "tau_definition": run["tau_definition"],
            "revision_id": run["revision_id"],
            "is_current": run["is_current"],
            "config_json": json.dumps(run["config"], sort_keys=True, allow_nan=False),
            "results_json": json.dumps(run["results"], sort_keys=True, allow_nan=False),
        })
    return rows


def comparison_csv(store: VitriFitStore, comparison_id: str) -> str:
    """CSV with explicit headers and JSON-preserved fitting parameters."""
    buffer = StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=COLUMNS, lineterminator="\n")
    writer.writeheader()
    # Sample and project names are user-controlled. Prevent spreadsheet apps
    # from interpreting them as formulas when the CSV is opened.
    def safe_cell(value):
        if isinstance(value, str) and value.lstrip().startswith(
                ("=", "+", "-", "@")):
            return "'" + value
        return value

    for row in comparison_rows(store, comparison_id):
        writer.writerow({key: safe_cell(value) for key, value in row.items()})
    return buffer.getvalue()
