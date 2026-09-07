# Parser correction work log

Date: 2026-09-07. Scope: `can_relax/io/parser.py` and `tests/test_parser.py`.

## Implemented

- Added `parse_curve_records(file_path)`: ordered list of dictionaries with `Temp` (float, Celsius), `Curve_ID` (stable file-local positional identifier, `curve_001`, etc.), and `Data` (pandas DataFrame with `Time` in seconds and `Modulus` in MPa).
- Supports repeated temperature/time/modulus triplets, with any order within each triplet, and the README's two-row temperature-header/time-modulus-pair layout. CSV/TXT and Excel load without pandas header mangling, preserving repeated headers and replicate curves.
- Legacy `parse_wide_format_data` retains the float-keyed dictionary API for unique temperatures and raises an explicit error for duplicates instead of overwriting observations.
- Signed integer, decimal, and scientific-notation numeric values are parsed without losing their signs.
- Canonical unlabelled defaults: seconds, MPa, Celsius. Explicit seconds/minutes and Pa/kPa/MPa units in headers or cells are validated and converted. Common underscore units are supported alongside legacy `_A`/`_B` identifiers. Unsupported or conflicting unit declarations raise errors.
- Triplet temperature must remain constant (absolute tolerance 1e-8 Celsius); temperatures at/below absolute zero and negative elapsed times fail validation.
- Malformed numeric values, incomplete rows, unsupported schemas, and empty curves raise explicit errors. Entirely empty trailing observations for shorter curves are permitted.

## Validation

Command: `.venv/Scripts/python.exe -m pytest tests/test_parser.py -q`

Result: **15 passed** (0.74 seconds). Covers CSV/XLSX documented pair layout, signed temperatures, replicate preservation, duplicate triplet headers, numeric unit conversion, uneven curve lengths, malformed values, varying temperatures, conflicting/unsupported units, and incomplete rows.

Environment: `python` is not on PATH; repository `.venv/Scripts/python.exe` works. Sandboxed pytest cannot enumerate the existing user temporary directory. The same test command passed after approved escalation for pytest temporary-directory access.

## Integration and review recommendations

- GUI should consume `parse_curve_records` and retain both file identity and `Curve_ID`; positional IDs are intentionally not globally unique across files.
- GUI should catch and display parser exceptions. Errors are deliberately no longer swallowed or transformed into empty results.
- Update README's previous claim of arbitrary automatic cleaning: the contract is explicit supported schemas and unit conversion, not arbitrary column discovery.
- Remaining extensions, not silently assumed here: separate spreadsheet sheet selection, locale decimal commas in numeric strings, Fahrenheit/Kelvin conversion, and arbitrary instrument export metadata rows.
