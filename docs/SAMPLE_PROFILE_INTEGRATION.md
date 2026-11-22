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
- DMA, DSC and tensile can be registered as metadata, but their sample-profile
  import/analysis interfaces are **not yet connected**.
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
