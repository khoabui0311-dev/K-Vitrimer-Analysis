# VitriFit 2.0 progress log — 20 November 2026

Development branch: feat/vitrifit2-foundation
Draft PR: https://github.com/khoabui0311-dev/K-Vitrimer-Analysis/pull/1
Primary v1 branch: main (not merged/replaced)

## Implemented and committed

- Reusable SQLite+content-addressed file store: projects, samples, experiments,
  curves, immutable raw instrument bytes, processing revisions, saved analyses,
  comparisons, figure presets and figure compositions.
- Original-file hash validation and complete ZIP backup with a SQLite snapshot.
- Import bridge uses the maintained v1 parser; supports multiple temperatures
  and replicates in canonical time seconds and modulus MPa.
- Per-curve masked keep/exclude regions, persisted undo/redo, reload/reopen.
- Preview-only v1 heuristic auto-trim proposal; explicit user application.
- Saved analyses pinned to processing revisions, stale-fit invalidation metadata.
- Numerical fitting through the existing v1 CurveAnalyzer with a no-autotrim
  selection processor, preserving observed reference modulus and original time.
  Supports Maxwell, single KWW, dual KWW, Two-Maxwell (Prony) with plateau modes.
- Existing v1 first-retained-reference raw 1/e crossing stored for provenance.
- Cross-project fixed-measured-temperature tau comparisons, curve overlays,
  Arrhenius/VFT sample-specific kinetics and independent temperature windows.
- FastAPI localhost service, host/origin guard, browser library endpoints.
- React+TypeScript browser workspace with project/sample experiment navigation,
  Plotly brush/two-click region selection, undo/redo, fitting and comparisons,
  saved analyses/comparison reopening, figure style editing, backup download.
- Windows development launch script, local run/restore guide.
- Publication parity contract and optional v1 Publication preset bridge that
  captures the current v1 widget settings without rewriting plots.
- Regression tests and browser-build CI workflow. Previous v1 AppTest paths
  were made robust to running from GitHub CI.

## Not yet done / acceptance blockers

1. **CI:** All new tests must pass on supported Python/OS versions; the
   branch may be ahead of the latest finished workflows. Do not claim green
   until checking the exact HEAD commit. Review failure logs and fix.
2. **Real experiment validation:** Test CSV/XLSX from VUGT 12/11, 13/11,
   03/11, LCE2 and IPN, including duplicates, missing values, replicates and
   non-ideal measurement curves.
3. **Publication parity:** Capture golden outputs for the four v1 scientific
   figures, all dimensions, font families, scales, legend and panel controls,
   CMYK/RGB export, physical DPI, then migrate UI/rendering without regression.
   The new Figure Studio currently persists styles/projects but DOES NOT yet
   reproduce the full publication figure/render/export experience.
4. **Scientific uncertainties:** Extend per-sample kinetics covariance
   propagation, replicates/error bars, sensitivity to trimming windows, and
   model identifiability. Multi-mode beta reporting and raw 1/e comparison
   selector should be added.
5. **Data platform:** Add schema migration tooling, backup-restore wizard and
   restore test on an independent installation.
6. **Additional experiments:** DMA, DSC and tensile inputs and analysis
   are designed for future modules, not yet implemented.
7. **Packaging:** Develop and clean-machine validate standalone Windows
   installer without needing Python or Node installed.
8. **UX:** Test very large datasets, zoom/drag behavior, keyboard undo/redo,
   per-curve manual point exclusion and multi-panel publication composition.

## Working rules for automated continuation

- Keep v1 main safe; use development branch and PR. Do not merge until parity.
- Prefer one tested increment at a time, with a clear commit and test evidence.
- Each saved analysis must refer to immutable raw data + a specific trim revision.
- Never silently interpolate missing fixed comparison temperatures.
- Never equate fitted KWW tau with raw observed 1/e interval.
- Preserve the current style/export controls in can_relax/gui/tabs/tab_pub_main.py.
- Only mark a milestone complete once tests and release acceptance evidence exist.
