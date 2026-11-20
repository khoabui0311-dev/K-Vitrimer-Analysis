# VitriFit 2.0 — import preview and scientific quality review

## Workflow

1. Choose a project and sample in the Library.
2. Select a relaxation file: CSV, TXT, genuine Excel 97–2003 XLS,
   or XLSX. Maximum upload size is 50 MB.
3. Select **Inspect file**. This uses the existing, unit-validated
   v1 \`parse_curve_records\` logic. Nothing is written to the research database.
4. Check all detected curves, temperatures, replicate counts, time ranges,
   modulus units and any quality warnings. Click a curve row to preview it.
5. Acknowledge warnings if present, then select **Save to library**.
   The server verifies that the original file SHA256 and detected curve
   count still match the inspected file.
6. Continue to Data Preparation, where any warnings from the original
   experiment are still displayed alongside the selected curve.

## Scientific invariants

- Uploaded original bytes are immutable and content-addressed by SHA256.
- Import retains the original row order, recorded time, temperature
  and modulus values; preview drawing uses no more than 120 display
  observations per curve without dropping any saved data.
- Duplicate temperatures are **replicate curves**, never overwritten
  entries in a \`{temperature: curve}\` dictionary.
- Input conversions (time s, modulus MPa, temperature °C) are recorded
  in experiment metadata, along with quality warnings.
- The parser does not silently infer relaxation modulus from stress,
  frequency sweeps, temperature scans, DSC, DMA or tensile measurements.
  Those require separate instrument adapters and are not supported by
  this relaxation upload workflow.
- Non-positive modulus values, repeated timestamps, decreasing time
  intervals and zero initial time are diagnosed but **not deleted**.
  Nonlinear fitting may require an explicitly edited per-curve mask.
- First-time import warnings remain part of the saved audit record.
- Re-importing creates a new experiment record; SHA256-based raw
  blob storage avoids duplicating original bytes.

## Existing instrument examples and test coverage

Two previously supplied research workbooks were inspected **locally** to
understand their header patterns, not added to the GitHub repository:

- VUGT 13/11: 16 triplet-style relaxation curves with repeated temperatures.
- LCE2: 8 triplet-style relaxation curves with repeated temperatures and
  positional R1/R2-style headers.

Regression tests use **synthetic data with matching header structures and
column counts**, plus generated genuine BIFF XLS files. No confidential
instrument readings are committed to the repository.

This is a development acceptance step, not a substitute for end-to-end
interactive testing with instrument exports on the user's own machine.
