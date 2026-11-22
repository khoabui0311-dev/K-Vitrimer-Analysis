# VitriFit 2.0 Sample Profile — integrated prototype

Status: **implemented in the feature branch, pending full runtime validation**.
This is an additive experimental workflow; v1 remains unchanged and is not
replaced. No paid API, external service or CI job is required.

## Local launch

Install the repository's existing Python requirements plus
`requirements-v2.txt`. Run the existing `run_v2.py` launcher, then open
the local browser address it reports. The FastAPI service is restricted to
localhost and is not intended for deployment to the internet.

In the sidebar choose a project and sample, then open **Sample Profile**.
Create a specimen, choose Rheology and either amplitude_sweep or
frequency_sweep, enter measurement conditions as JSON, then create the
measurement. Upload UTF-8 CSV with a header row and map each required column
explicitly. Specify frequency and modulus units before import.

- Amplitude sweep CSV example: `strain,Gp` with columns
  `{"strain_percent":"strain","storage_modulus":"Gp"}`.
  Strain values are **percent**, not fractional strain.
- Frequency sweep CSV example: `freq,Gp,Gpp` with columns
  `{"frequency":"freq","storage_modulus":"Gp","loss_modulus":"Gpp"}`.
  Frequency unit must be Hz or rad/s. Modulus unit is Pa, kPa or MPa.

The interface shows analysis history, frequency-sweep G′/G″ plots, LVR
screening status, reanalysis of LVR thresholds and provenance export. The
comparison control checks selected analysis conditions; it does **not**
perform statistical aggregation or justify TTS.

## Persistence and provenance

New tables are additive to the existing local SQLite store:
`v2_specimens`, `v2_measurements`, `v2_measurement_files`,
`v2_measurement_analyses`. Source bytes are stored content-addressed by
SHA256. Each new analysis records file ID, method, algorithm version, units,
column mapping and result JSON. Reanalysis creates a new record against the
same raw file; it does not overwrite historical results.

Provenance JSON does not contain original raw bytes. Archive both the
manifest and the raw files. The API can download individual original bytes.

## Limitations and scientific caveats

- This adapter accepts explicit UTF-8 CSV only, not proprietary instrument
  formats, XLS or auto-detected columns.
- DMA temperature ramps, DSC traces and tensile tests now have explicit-CSV
  import, persisted analysis and measured-data plots. This does not imply\n  validated instrument-specific parsing or publication-ready transition fits.
- The current comparison requires exact metadata equality on user-selected
  keys. The user must select scientifically meaningful conditions.
- A single-frequency oscillatory LVR measurement cannot certify a full
  frequency sweep, intermediate temperatures or step-strain relaxation.
- Frequency crossover is interpolated only within measured frequency points.
- No uncertainty quantification or instrument-limit checks are performed
  in this adapter; interpret outputs as screening analyses.
- Raw-file content-addressed writes are not yet coordinated with a single
  transactional blob/database journal. Back up the local workspace.
- Browser compilation, integration tests and publication figure parity
  remain release blockers until actually run and reviewed.

## Validation checklist (pending execution)

1. `pytest -q tests/test_v2_sample_api.py tests/test_v2_rheology_workflow.py tests/test_v2_rheology_history.py tests/test_v2_rheology_manifest.py tests/test_v2_sample_profile.py`
2. Run the frontend build in `vitrifit2/web` using the project's existing
   package scripts; inspect any TypeScript errors.
3. Browser smoke test: create sample → specimen → amplitude sweep → CSV
   import → reanalysis → reopen after restart → manifest.
4. Test missing columns, malformed CSV, empty file, wrong units, mismatched
   specimen/temperature/frequency, and corrupted raw blob.
5. Compare original v1 publication figures against saved golden examples.
6. Verify existing v1 projects and trim/undo/redo still work unchanged.

Do not merge this feature branch into main until those checks pass.

## Additional thermal and mechanical CSV adapters

**DMA temperature ramp:** header columns mapped to `temperature_c`,
`storage_modulus` and `loss_modulus`. Choose Pa, kPa, MPa or GPa.
The reported tan-delta maximum is an observed peak candidate only if the
maximum is internal to the measured range; it is not automatically a Tg onset.
Split cooling/heating loops before import; this adapter requires strictly
increasing temperatures.

**DSC:** map `temperature_c` and `heat_flow`; specify units (mW, W,
W/g or mW/mg) and heating rate if known. Plots preserve the raw sign
convention. Tg onset and enthalpy are intentionally not assigned: reliable
results require a user-selected baseline, sample mass and sign convention.

**Tensile:** map `displacement_mm` and `force_n`, then enter original
gauge length, width and thickness in mm. Young's modulus uses only measured
points within the explicit fit window. True stress assumes constant volume
and homogeneous deformation. Crosshead extension is not necessarily local
gauge strain; last point is not automatically fracture.

Run `pytest -q tests/test_v2_thermal_workflow.py tests/test_v2_thermal_api.py tests/test_v2_tensile_workflow.py tests/test_v2_tensile_api.py`
in addition to the existing v2 tests. All are committed but have **not**
been executed in the current development session.

The local environment cannot resolve github.com for cloning; a full
repository build and test run must be completed before merging.

## Backup safety and unified provenance (2026-11-22)

A critical backup-completeness bug was identified and fixed: the legacy
`/api/backup` implementation originally archived only hashes referenced by
`experiments.file_sha256`. The current implementation also enumerates
`v2_measurement_files.sha256` when that table exists, deduplicates by digest,
and verifies each blob before writing it into the ZIP. The archive manifest
format is now `vitrifit2-backup-v2`; the database and raw blob paths remain
unchanged. Backward compatibility with existing v1 workspace databases is
preserved by checking table existence first.

`POST /api/v2/analyses/manifest` now exports a technique-independent
analysis manifest with project/sample/specimen/measurement hierarchy,
conditions, algorithm version, config, source filename, SHA256 and optionally
results. The Sample Profile export button uses this endpoint for all
techniques. A manifest contains **no raw bytes** and is not a substitute
for the full backup or separately downloaded original files.

New regression tests:
`tests/test_v2_backup_sample_profile.py` and
`tests/test_v2_sample_manifest.py`. These are committed but remain
**unexecuted** until a full local checkout and pytest run is possible.

## Read-only backup verification UI and API

The Sample Profile now provides a **Verify backup** control for local ZIP files.
`POST /api/v2/backup/verify` reads the uploaded archive and verifies:

- Expected entry names and no duplicate ZIP names.
- Supported manifest format and valid unique SHA-256 identifiers.
- Exact raw-blob membership and digest integrity.
- SQLite `PRAGMA integrity_check`.
- All raw digests referenced by both legacy experiments and v2 specimen
  attachments are present in the manifest.

The verifier **never restores or extracts** the backup to the workspace.
The HTTP upload is capped at 512 MiB and uncompressed ZIP metadata is
limited to 2 GiB, with conservative compression-ratio checks. Larger
legitimate backups require a future streaming verifier; do not assume that
a size-limit rejection indicates corruption.

Run `pytest -q tests/test_v2_backup_verify.py tests/test_v2_backup_verify_api.py`
as part of the release gate. The new tests have been committed but not
executed in this environment. No restore button is exposed until safe
staged restoration and rollback have been tested.
