# VitriFit 2.0 — Release candidate 2

The newer source-only **2.0.0-rc.3.dev.1** reliability preview is described in
[Fit reliability](FIT_RELIABILITY.md). The notes below describe the published rc.2.

Version **2.0.0-rc.2** is a prerelease for research evaluation, not the stable
release. It replaces rc.1 as the candidate containing the new workspace.
No DOI has been assigned.

## Changes since rc.1

- Import, review and model selection in the main workspace, with dataset and
  result summaries and residual inspection.
- Group point exclusion/restoration by box/lasso, original point-number ranges
  or elapsed-time intervals, plus per-curve undo.
- Portable `.vfit` projects preserving source data, exclusions, timing, analysis,
  downstream selections and publication formatting. Reopening recalculates fits.
- Maxwell/KWW/two-Maxwell comparison on the same observations and plateau policy.
- Offline HTML reports and strict JSON numerical snapshots with provenance.
- Fit visibility switches and concise Tv labels; vector SVG/PDF and raster
  TIFF/JPEG exports with stale-download invalidation.
- Reusable `.vstyle` figure formats, custom colors, import size previews,
  optional automatic axes and one-step format undo.
- Stronger packaged tests covering fresh-session reopening, actual figure/report
  exports, offline analysis/server network guards and installer upgrades.

## Scientific validation

Seven VUGT relaxation curves from 100–180 °C were checked against an independent
log-time solver with 12 initial guesses. Fast/slow times agreed within 0.007%.
Sampling and measurement-window sensitivity were also assessed. Residuals remain
structured; at 150 °C the slow time extends beyond the measurement window.
See `VALIDATION_2.0_RC2.md` for the results, assumptions and reproducible procedure.
This is a numerical consistency/stability audit, not independent experimental
validation of a physical two-mode interpretation.

## Known limits

- Windows x64 installer only; unsigned. No macOS/Linux installer is provided.
- Each temperature is fitted independently. Arrhenius is a separate regression;
  two exponential terms do not by themselves identify two physical mechanisms.
- Production fitting still uses one starting point, automatic peak/drift
  preprocessing, logarithmic downsampling and retained-reference normalization.
  The independent multi-start solver is a validation tool, not a new app option.
- Covariance errors are local estimates. Slow modes beyond the measured window
  and small/overlapping modes can be poorly constrained. Residual structure and
  sensitivity to data selection must be reviewed even when R² is high.
- Arrhenius regression intervals do not propagate fitted-time uncertainty.
  TTS, regularized spectra and extrapolated Tv require scientific judgement.
- Project saving is explicit; no autosave or crash recovery. Projects recompute
  results with the running version; keep reports/CSV/JSON as fixed records.
- Upgrade tests preserve sentinel user files and exercise selected installers;
  they cannot cover every existing Windows configuration.
- Academic and Research License; commercial use requires permission.

## Candidate publication gates

Publish only the exact clean build whose project checks, frozen offline workflow,
clean installation/uninstallation and rc.1 upgrade checks pass. Attach installer,
SHA-256, source/build manifest, test reports, quick-start guide and validation
notes. The release remains a prerelease. Publisher signing and independent
scientific review remain work for a stable release.
