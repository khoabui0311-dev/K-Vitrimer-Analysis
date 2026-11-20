"""Bridge the current validated relaxation parser into persistent experiments.

This adapter intentionally invokes the EXISTING v1 input parser, preserving
its unit conversions, replicate IDs, temperature rules and error reporting.
"""
from __future__ import annotations

from pathlib import Path
import tempfile

from can_relax.io.parser import parse_curve_records
from .persistence import VitriFitStore

SUPPORTED_SUFFIXES = {".csv", ".txt", ".xlsx"}


def import_relaxation_upload(store: VitriFitStore, sample_id: str,
                             filename: str, original_bytes: bytes,
                             metadata: dict | None = None) -> dict:
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        raise ValueError("Use a CSV, TXT or XLSX relaxation file")
    if not original_bytes:
        raise ValueError("Input file is empty")
    with tempfile.TemporaryDirectory(prefix="vitrifit2_parser_") as tmp:
        input_path = Path(tmp) / f"upload{suffix}"
        input_path.write_bytes(original_bytes)
        parsed = parse_curve_records(input_path)
    # Keep the original instrument bytes unchanged; parsed data is separate.
    curves = []
    for item in parsed:
        df = item["Data"]
        curves.append({
            "source_curve_id": item["Curve_ID"],
            "temperature_c": item["Temp"],
            "time_s": df["Time"].astype(float).tolist(),
            "modulus_mpa": df["Modulus"].astype(float).tolist(),
        })
    return store.import_experiment(sample_id, filename, original_bytes, curves,
        metadata={"technique": "stress_relaxation", "parser": "can_relax.io.parser",
                  **(metadata or {})})
