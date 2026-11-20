# VitriFit 2.0 — implementation plan (foundation branch)

Status: in progress. This is a non-destructive development branch; v1 remains on main.

## Non-negotiable requirements

- Local-first browser workflow; locally stored raw data, analyses, figures, and backups.
- Preserve and regression-test all v1 scientific models and current Publication tab controls before replacing them.
- Original uploaded bytes and instrument timestamps are immutable.
- Project → sample → experiment → curve → processing revision → analysis run.
- Individual per-curve **keep/exclude region** editing, inspectable masks, autosaved undo/redo.
- Changing preparation must flag older fits as stale; never overwrite results automatically.
- Saved comparison sessions across samples/projects: (1) raw and fitted curve overlay,
  (2) ln(tau) vs 1000/T with per-sample fitting windows,
  (3) tau at measured common temperature. No hidden temperature interpolation.
- A relaxation-time definition (KWW characteristic tau, Maxwell tau, raw 1/e,
  alternative threshold, multi-mode component) accompanies each comparative value.
- Separate *publication style presets* from *saved figure compositions* referencing
  immutable analysis revisions; support per-figure overrides.
- Education panel removed from primary workspace; contextual help retained.

## Sequence, with completion gates

0. **Audit:** Inventory current Streamlit app, plotting/export code, tests,
   scientific conventions, and existing Comparison tab. Baseline current tests.
1. **Persistence:** Introduce standalone SQLite metadata + content-addressed raw
   blob storage; persist project/sample/experiment/curve, per-curve edits, analysis
   revisions, comparison sessions, figure presets/figure projects. Verify reopen.
2. **API and web shell:** FastAPI routes over the store; React/TypeScript navigation:
   Library, Preparation, Analysis, Comparison, Figure Studio. Localhost only.
3. **Curve editor:** Plotly.js range brush and draggable endpoints, keep/exclude,
   no destructive deletions, per-curve undo/redo, clear processing provenance,
   auto-trim proposal subject to manual acceptance.
4. **Scientific bridge:** Reuse and independently test the existing parser, model
   fitter, kinetics, and TTS; fit from a pinned processing revision; maintain units,
   loading-time origin, reference modulus and raw 1/e rules.
5. **Comparisons:** Cross-project analysis selection, measured common-temperature
   overlays, per-sample kinetic fits and temperature windows, missing-data flags,
   explicit time definitions, replicates and uncertainty.
6. **Figure Studio:** Preserve v1 tab and exact publication standards (see
   PUBLICATION_PARITY.md). Add persisted named presets, saved compositions, style
   overrides, multi-panel layouts, and reopening/editing.
7. **Qualification/release:** Golden-image comparison, numerical regressions,
   round-trip/backup tests, migration, browser/Windows packaging, performance.

## First executable vertical slice

Import project/sample and a multi-temperature dataset → persist original file and
curve arrays → individually keep/exclude a time interval → undo and redo that single
curve → reopen the application/store without losing edits → pin analysis results
to a curve revision → mark a superseded result stale → save a cross-sample
comparison session and publication preset.

## Architectural decision

Use Python numerical core (NumPy/SciPy), SQLite for records, hashed immutable files
for source uploads, FastAPI service, React/TypeScript UI, Plotly.js interactive
selection, Matplotlib publication rendering. Rust is **not** part of the initial
build; profile computational bottlenecks before considering targeted acceleration.

## Review gates

- Each phase includes unit/integration tests and file round-trip checks.
- Never mutate, rename or delete the existing v1 Publication module.
- The scientific engine must never depend on the browser or a GUI framework.
- A saved figure must reopen with its own exact plot configuration even after
  the global default style changes.
- Fitted results must carry data/revision/model provenance.
