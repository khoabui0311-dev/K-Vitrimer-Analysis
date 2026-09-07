# Work log

## 2026-09-07 — started
- User authorized the correction batch and shared handoff folder.
- Working tree was clean at start. Previous review baseline: 31 tests passed.
- Created shared_review; dispatched independent review and bounded parser/kinetics work.
- Design: input times default to elapsed time since loading. A GUI origin offset will
  support instrument clocks explicitly; cutoffs will not silently reset the origin.
- Model predictions will be normalized at the actual retained reference observation,
  preserving existing physical parameter order for downstream consumers.

## Numerical and integration work
- Added conditional log-space relaxation predictions; all late-start synthetic KWW
  recovery cases now pass (starts 0, 0.01, 1, 30, 100 seconds).
- Explicit failed-fit state excludes optimizer failure from downstream results.
- Added 1/e crossing status and separate interval/plot-coordinate values.
- Spectrum returns input-unit discrete weights; added reconstruction diagnostics and
  tightened solver tolerance after reconstruction tests exposed early solver termination.
- Parser and kinetics agents completed bounded changes; see their separate logs.
- GUI now preserves replicate IDs, hashes data/settings, clears obsolete state, and
  shares kinetic prediction functions with the core. Removed manual spectrum cache.
- Numerical/parser suite reached 104 passing tests. Sandbox blocked Windows pytest
  temporary directories; approved escalation allowed the complete suite to pass.
- Streamlit workflow test in progress. Its initial model-change assertion selected the
  Virtual Lab's identically named Model widget; added an explicit analysis widget key.
- Independent review caught a publication annotation mixing crossing time and interval;
  corrected annotation while retaining the actual crossing x-coordinate.
- Expanded focused checks: 20 passed, including GUI replicate preservation, incomplete
  raw curves, same-temperature dataset replacement, empty selection, and Van 't Hoff.
- Full repository collection stalled after importing root-level plotting experiments
  (including a global MathText monkey patch). Interrupted that run; restricted discovery
  to the actual tests/ suite and configured a headless renderer. Root experiments contain
  no pytest test functions. Final full-suite verification follows this isolation change.

## Completed
- Final suite: **109 passed in 14.69 seconds**; git diff --check passed.
- Independent reviewer verified both recommendations resolved: crossing interval labels
  and Curve IDs in plot legends. See REVIEW_NOTES.md final resolution.
- Added requirements-dev.txt and pytest configuration, updated README input/time/spectrum
  semantics, and added downloadable analysis provenance JSON in the app.
- Final evidence, environment, compatibility changes, unverified export appearance, and
  next-review recommendations are documented in VALIDATION.md.
- Changes are in the shared working tree, ready for another agent to inspect. No commit
  or deployment performed; this local folder does not configure an external network share.

## Replicate / UX follow-up — 2026-09-07
- Preserved the other review's averaging and conditional-label changes; added explicit
  reference Curve ID selection, reference metadata, shared visible-replicate labels,
  and an orange Spectrum window-warning badge.
- Verified reference averaging/order invariance, explicit reference invalidation, label
  compactness, and badge appearance/clearing. **110 tests passed in 19.15 seconds**.
- Details and limitations: REPLICATE_UX_FOLLOWUP.md. No commit or deployment made.

## Further scientific review — 2026-09-07
- Indexed 17 local PDF files and performed focused section-level reading of six papers.
  Inspected rendered equation pages for KWW moments, network thermodynamics, and the
  Lin additive exchange-time model. Inventory distinguishes focused reading from screening.
- Reproduced five synthetic/analytical probes covering tail subtraction, a permanent
  plateau fitted as an artificial slow mode, TTS normalization, apparent dissociation
  caused by acquisition delay, and the KWW viscosity correction.
- Nine prioritized findings and a scientific follow-up plan are in
  scientific_review/REPORT.md. Source links, page references, code snapshot hashes,
  reproducible script, numerical output, and a diagnostic plot accompany the report.
- Application source hashes were unchanged during this review. No correction,
  deployment, or experimental-validation claim is implied. The 110-test result is
  historical; this review ran new counterexamples rather than repeating that suite.

## Plateau / core analysis batch — 2026-09-07
- Implemented Zero/Fit/Fixed plateau for Maxwell and single KWW with preserved
  physical time origin and reference normalization. Added fit flags and residuals.
- Improved apparent Ea reporting, beta inspection, optional dual component selection
  and CSV/provenance exports. Kept flagged curves selectable with visible warnings.
- Validation: 119 tests passed in 28.53 seconds, including nine new recovery and
  Streamlit checks. Earlier targeted plateau run: 9 passed in 12.70 seconds.
- Full handoff and limitations: PLATEAU_BATCH.md. Advanced scientific corrections
  remain separate work. No commit or deployment made.
- Final fit-warning propagation and UI cleanup recheck: 11 plateau/workflow tests
  passed in 28.23 seconds. `git diff --check` passed (line-ending notices only).

## Import compatibility fix — 2026-09-07
- Investigated the reported incomplete-observation error. Triplet temperature is
  now treated as constant curve metadata and may be entered once or sparsely.
  Nonblank temperature values must still agree. Rows with neither time nor modulus
  are treated as padding, including rows with a repeated temperature. Whitespace-only
  cells are treated as blank. No partially populated observations are discarded.
- A missing time or modulus now reports the original file row number and correction
  guidance; pair layouts no longer incorrectly demand a temperature on each row.
- Added CSV/XLSX sparse metadata and padding tests, plus conflicting/missing
  temperature and incomplete-pair diagnostics. Targeted parser tests: 19 passed.
- The user's specific input file was not available; these tests reproduce supported
  spreadsheet layouts that previously triggered the reported error.
- Full regression suite: 123 passed in 22.68 seconds. `git diff --check` passed.

## Supplied workbook follow-up — 2026-09-07
- Read VU2.xlsx and VUEG.xlsx without modifying either original. VU2 contains a
  leading time-only acquisition row in all seven triplets; VUEG parses directly.
- Parser now skips leading time-only rows when later measurements exist and
  returns Import_Warnings, displayed by the app and retained in provenance.
  Interior/trailing missing modulus, missing time, or wholly incomplete curves
  remain errors. Original times and column ordering are preserved.
- VUEG starts around 1020 seconds: loading origin requires experimental context;
  no assumption or automatic time reset was made. Headers have no explicit units,
  so existing canonical-unit defaults still apply.
- Added regression coverage for leading acquisition rows, reordered Step time /
  Modulus columns and continued rejection of other partial observations.
- Verified actual imports: VU2 has seven curves with 5399 observations each and
  one notice per curve; VUEG has four curves with 450 observations each and no
  import notices. Parser and Streamlit workflow tests: 25 passed in 18.59 seconds.
