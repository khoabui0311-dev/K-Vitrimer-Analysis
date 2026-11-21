"""Import and preview relaxation data with the validated v1 scientific parser.

No silent conversion to a different scientific technique: a DMA, DSC, tensile
or raw-force file is not relabelled as stress relaxation. The preview shows
measurement intervals, replicate identifiers and warnings before committing.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import tempfile

import numpy as np

from can_relax.io.parser import parse_curve_records
from .persistence import VitriFitStore

SUPPORTED_SUFFIXES = {".csv", ".txt", ".xls", ".xlsx"}


def _parse_relaxation_file(filename: str, original_bytes: bytes) -> list[dict]:
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        raise ValueError("Use a CSV, TXT, XLS or XLSX relaxation file")
    if not isinstance(original_bytes, bytes) or not original_bytes:
        raise ValueError("Input file is empty or not bytes")
    with tempfile.TemporaryDirectory(prefix="vitrifit2_parser_") as tmp:
        input_path = Path(tmp) / ("upload" + suffix)
        input_path.write_bytes(original_bytes)
        return parse_curve_records(input_path)


def _curve_quality(item: dict) -> dict:
    df = item["Data"]
    times = df["Time"].to_numpy(dtype=float)
    modulus = df["Modulus"].to_numpy(dtype=float)
    delta = np.diff(times)
    nonpositive = int(np.sum(modulus <= 0))
    duplicates = int(np.sum(delta == 0))
    backwards = int(np.sum(delta < 0))
    warnings = list(item.get("Import_Warnings", []))
    if nonpositive:
        warnings.append(
            f"{item['Curve_ID']}: {nonpositive} non-positive modulus points; "
            "these must be excluded explicitly before nonlinear fitting.")
    if duplicates:
        warnings.append(
            f"{item['Curve_ID']}: {duplicates} repeated timestamps; inspect "
            "and exclude individual artifacts before fitting.")
    if backwards:
        warnings.append(
            f"{item['Curve_ID']}: {backwards} decreasing timestamp intervals; "
            "instrument-order measurements were preserved.")
    if times[0] == 0:
        warnings.append(
            f"{item['Curve_ID']}: first elapsed time is 0 s. "
            "A logarithmic time axis requires a positive-time selection.")
    return {
        "source_curve_id": str(item["Curve_ID"]),
        "temperature_c": float(item["Temp"]),
        "points": int(len(times)),
        "first_time_s": float(times[0]),
        "last_time_s": float(times[-1]),
        "time_min_s": float(np.min(times)),
        "time_max_s": float(np.max(times)),
        "first_modulus_mpa": float(modulus[0]),
        "nonpositive_modulus_points": nonpositive,
        "duplicate_time_steps": duplicates,
        "decreasing_time_steps": backwards,
        "warnings": warnings,
    }


def preview_relaxation_upload(filename: str, original_bytes: bytes) -> dict:
    """Read-only scientific preview; does not write a database record.

    Returns one record per detected curve, including multiple measurements at
    the same temperature, and optional decimated chart points for the browser.
    """
    parsed = _parse_relaxation_file(filename, original_bytes)
    curves = []
    for item in parsed:
        summary = _curve_quality(item)
        data = item["Data"]
        indices = np.unique(np.linspace(0, len(data)-1, min(len(data), 120)).astype(int))
        summary["preview_time_s"] = [float(data["Time"].iloc[i]) for i in indices]
        summary["preview_modulus_mpa"] = [float(data["Modulus"].iloc[i]) for i in indices]
        curves.append(summary)
    temperatures = [curve["temperature_c"] for curve in curves]
    replicates = {
        temp: temperatures.count(temp) for temp in sorted(set(temperatures))
        if temperatures.count(temp) > 1
    }
    warnings = [msg for curve in curves for msg in curve["warnings"]]
    return {
        "filename": Path(filename).name,
        "file_sha256": hashlib.sha256(original_bytes).hexdigest(),
        "file_bytes": len(original_bytes),
        "technique": "stress_relaxation",
        "canonical_units": {"time": "s", "modulus": "MPa", "temperature": "°C"},
        "curves": curves,
        "curve_count": len(curves),
        "temperatures_c": sorted(set(temperatures)),
        "replicates_per_temperature": {
            f"{temp:g}": count for temp, count in replicates.items()
        },
        "warnings": warnings,
        "needs_review": bool(warnings),
        "saved": False,
    }


def import_relaxation_upload(store: VitriFitStore, sample_id: str,
                             filename: str, original_bytes: bytes,
                             metadata: dict | None = None) -> dict:
    """Commit the original bytes and unmodified canonical parsed observations.

    The preview does not modify, normalize, trim or sort any recorded points.
    Import warnings are persisted with the experiment for future review.
    """
    if metadata and metadata.get("preview_sha256") is not None:
        digest = hashlib.sha256(original_bytes).hexdigest()
        if str(metadata["preview_sha256"]) != digest:
            raise ValueError("The selected source file changed after its preview; inspect it again.")
    parsed = _parse_relaxation_file(filename, original_bytes)
    if metadata and metadata.get("preview_curve_count") is not None:
        if int(metadata["preview_curve_count"]) != len(parsed):
            raise ValueError("Curve count changed after preview; inspect this file again.")
    summaries = [_curve_quality(item) for item in parsed]
    curves = [
        {
            "source_curve_id": item["Curve_ID"],
            "temperature_c": item["Temp"],
            "time_s": item["Data"]["Time"].astype(float).tolist(),
            "modulus_mpa": item["Data"]["Modulus"].astype(float).tolist(),
        }
        for item in parsed
    ]
    import_warnings = [text for c in summaries for text in c["warnings"]]
    audit = {
        **(metadata or {}),
        "technique": "stress_relaxation",
        "parser": "can_relax.io.parser.parse_curve_records",
        "canonical_units": {"time": "s", "modulus": "MPa", "temperature": "°C"},
        "curve_count": len(summaries),
        "curve_quality": summaries,
        "import_warnings": import_warnings,
        "import_requires_review": bool(import_warnings),
    }
    return store.import_experiment(sample_id, filename, original_bytes, curves,
                                   metadata=audit)
