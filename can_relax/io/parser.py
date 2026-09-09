"""Validated wide relaxation input; canonical units are seconds, MPa and Celsius."""
import pathlib
import re
from zipfile import BadZipFile

import numpy as np
import pandas as pd

_NUMBER = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?"
_FACTORS = {
    "time": {"s": 1., "sec": 1., "seconds": 1., "min": 60., "minutes": 60.},
    "mod": {"pa": 1e-6, "kpa": 1e-3, "mpa": 1.},
    "temp": {"c": 1., "°c": 1., "degc": 1., "celsius": 1.},
}


def _load_file_robustly(file_path):
    path = pathlib.Path(file_path)
    if path.suffix.lower() in (".csv", ".txt"):
        try:
            return pd.read_csv(path, sep=None, engine="python", header=None)
        except UnicodeDecodeError:
            return pd.read_csv(path, sep=None, engine="python", header=None, encoding="latin-1")
    if path.suffix.lower() == ".xlsx":
        try:
            return pd.read_excel(path, header=None)
        except (BadZipFile, ImportError) as exc:
            raise ValueError(f'Cannot read XLSX workbook: {exc}') from exc
    raise ValueError("Unsupported file type; use CSV, TXT or XLSX (convert legacy XLS first).")


def _kind(label):
    text = str(label).strip().lower()
    if re.search(r"storage|loss|g_prime|g['′]|frequency|stress", text):
        raise ValueError("Expected time-domain relaxation modulus. Convert stress using the imposed strain; storage/loss modulus and frequency data are not relaxation modulus.")
    if re.search(r"temp|celsius|°c", text):
        return "temp"
    if re.search(r"modulus|\b(?:mpa|kpa|pa)\b", text):
        return "mod"
    if re.search(r"time|\b(?:sec|seconds?|min|minutes?|s)\b", text):
        return "time"
    return None


def _header_unit(label, kind):
    text = str(label).strip().lower()
    groups = re.findall(r"\(([^)]+)\)|\[([^]]+)\]", text)
    if groups:
        unit = next(part for part in groups[0] if part).strip()
        if unit not in _FACTORS[kind]:
            raise ValueError(f"Unsupported {kind} unit {unit!r} in header {label!r}.")
        return unit
    # Recognized unit suffixes are units; legacy A/B/number suffixes are IDs.
    suffix = text.rsplit("_", 1)[-1] if "_" in text else None
    if suffix in _FACTORS[kind]:
        return suffix
    if suffix in ("h", "hr", "hours", "ms", "gpa", "psi", "k", "f"):
        raise ValueError(f"Unsupported {kind} unit {suffix!r} in header {label!r}.")
    clean = re.sub(r"_[a-z0-9]+$", "", text)
    tokens = clean.split()
    for token in tokens:
        if token in _FACTORS[kind]:
            return token
    if len(tokens) > 1 and tokens[-1] not in ("modulus", "temperature", "time"):
        raise ValueError(f"Unrecognized unit in header {label!r}; use parentheses for units.")
    return None


def _quantity(value, kind, header_unit=None):
    match = re.fullmatch(rf"\s*({_NUMBER})\s*([^\d]*)\s*", str(value))
    if not match:
        raise ValueError(f"Invalid {kind} value: {value!r}.")
    number = float(match.group(1))
    unit = match.group(2).strip().lower()
    if unit and unit not in _FACTORS[kind]:
        raise ValueError(f"Unsupported {kind} unit {unit!r} in {value!r}.")
    if unit and header_unit and _FACTORS[kind][unit] != _FACTORS[kind][header_unit]:
        raise ValueError(f"Conflicting {kind} units in header and value {value!r}.")
    if not np.isfinite(number):
        raise ValueError(f"Non-finite {kind} value: {value!r}.")
    converted = number * _FACTORS[kind].get(unit or header_unit, 1.)
    if not np.isfinite(converted):
        raise ValueError(f"Non-finite {kind} value after unit conversion: {value!r}.")
    return converted


def _record(data, time_idx, mod_idx, labels, curve_id, temp_idx=None, temperature=None):
    indices = [time_idx, mod_idx] + ([] if temp_idx is None else [temp_idx])
    block = data.iloc[:, indices].replace(r'^\s*$', np.nan, regex=True)
    # Temperature is constant curve metadata. Spreadsheets commonly enter it
    # once (including merged cells), or fill it beyond a shorter curve's end.
    if temp_idx is not None:
        temp_unit = _header_unit(labels[temp_idx], "temp")
        temperatures = [_quantity(v, "temp", temp_unit) for v in block.iloc[:, 2].dropna()]
        if not temperatures:
            raise ValueError(f"{curve_id}: missing temperature; enter a constant temperature at least once in this triplet.")
        temperature = temperatures[0]
        if not np.allclose(temperatures, temperature, rtol=0, atol=1e-8):
            raise ValueError(f"{curve_id}: temperature must be constant within a curve.")
    block = block.loc[~block.iloc[:, :2].isna().all(axis=1)]
    if block.empty:
        raise ValueError(f"{curve_id}: curve contains no observations.")
    import_warnings = []
    leading = 0
    for _, row in block.iterrows():
        if pd.notna(row.iloc[0]) and pd.isna(row.iloc[1]):
            leading += 1
        else:
            break
    if leading and leading < len(block):
        rows = ', '.join(str(int(i)+1) for i in block.index[:leading])
        import_warnings.append(f'{curve_id}: skipped leading time-only row(s) {rows} with no modulus; recorded time origin preserved.')
        block = block.iloc[leading:]
    incomplete = block.iloc[:, :2].isna().any(axis=1)
    if incomplete.any():
        rows = ', '.join(str(int(i) + 1) for i in block.index[incomplete][:5])
        raise ValueError(f"{curve_id}: incomplete observation at file row(s) {rows}; each observation needs both time and modulus. Fill the missing value or clear both cells for an unused row.")
    time_unit = _header_unit(labels[time_idx], "time")
    mod_unit = _header_unit(labels[mod_idx], "mod")
    times = [_quantity(v, "time", time_unit) for v in block.iloc[:, 0]]
    moduli = [_quantity(v, "mod", mod_unit) for v in block.iloc[:, 1]]
    if temperature <= -273.15:
        raise ValueError(f"{curve_id}: temperature must exceed absolute zero.")
    if any(t < 0 for t in times):
        raise ValueError(f"{curve_id}: elapsed time cannot be negative.")
    return {"Temp": float(temperature), "Curve_ID": curve_id, "Import_Warnings": import_warnings,
            "Data": pd.DataFrame({"Time": times, "Modulus": moduli})}


def parse_curve_records(file_path):
    """Return ordered {Temp, Curve_ID, Data} records, preserving replicates.

    Temp is Celsius; Data contains Time (seconds) and Modulus (MPa). Missing unit
    labels mean canonical units. Curve_ID is a stable file-local positional ID.
    Triplet temperatures may be entered once or repeated consistently. Empty
    time/modulus pairs are padding; a partially filled pair is an error.
    Leading time-only acquisition rows are skipped with Import_Warnings.
    Invalid schemas, values, incomplete rows and ambiguous units raise ValueError.
    """
    raw = _load_file_robustly(file_path).replace(r'^\s*$', np.nan, regex=True).dropna(axis=1, how="all")
    if raw.empty:
        raise ValueError("The file contains no data.")
    labels = list(raw.iloc[0])
    kinds = [_kind(label) for label in labels]
    records = []
    if "temp" in kinds and "time" in kinds:
        if len(labels) % 3:
            raise ValueError("Triplet layout requires repeated Temp, Time, Modulus columns.")
        for start in range(0, len(labels), 3):
            block_kinds = kinds[start:start + 3]
            if sorted(str(k) for k in block_kinds) != ["mod", "temp", "time"]:
                raise ValueError("Each triplet must contain exactly one Temp, Time and Modulus column.")
            records.append(_record(raw.iloc[1:], start + block_kinds.index("time"),
                                   start + block_kinds.index("mod"), labels,
                                   f"curve_{len(records) + 1:03d}",
                                   temp_idx=start + block_kinds.index("temp")))
    else:
        if len(raw) < 3 or len(labels) % 2:
            raise ValueError("Expected Temp/Time/Modulus triplets or temperature headers above Time/Modulus pairs.")
        quantity_labels = list(raw.iloc[1])
        for start in range(0, len(labels), 2):
            temperature = _quantity(labels[start], "temp")
            if not pd.isna(labels[start + 1]):
                if _quantity(labels[start + 1], "temp") != temperature:
                    raise ValueError("A time/modulus pair has conflicting temperature headers.")
            if [_kind(v) for v in quantity_labels[start:start + 2]] != ["time", "mod"]:
                raise ValueError("Each temperature header must sit above a Time, Modulus pair.")
            records.append(_record(raw.iloc[2:], start, start + 1, quantity_labels,
                                   f"curve_{len(records) + 1:03d}", temperature=temperature))
    return records


def parse_wide_format_data(file_path):
    """Return {temperature: Data}; reject duplicates instead of overwriting them.

    Use parse_curve_records for multiple measurements at the same temperature.
    """
    curves = {}
    for record in parse_curve_records(file_path):
        temperature = record["Temp"]
        if temperature in curves:
            raise ValueError(f"Duplicate temperature {temperature:g} °C; use parse_curve_records to preserve replicates.")
        curves[temperature] = record["Data"]
    return curves
