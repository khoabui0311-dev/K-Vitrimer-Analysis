# Project audit — 9 September 2026

The application is materially stronger after this audit, but it is not certified
as error-free or experimentally validated. Three review passes covered project
source, numerical/data contracts, and integrated regression/export behavior.
Confirmed defects were corrected in the working tree. No commit, push or deployment
was made. The pre-existing point-selection changes and review notes were preserved.

## Scope and meaning of “every file”

The machine-readable [file inventory](audit_evidence/file_inventory.json) records
paths, byte sizes and SHA-256 fingerprints. The inventory includes **52 Python
files** after the additions, including package initializers, tests, examples,
developer scripts and reproduction scripts. Every Python file was syntax checked.
Application modules, tests, launchers, dependencies, README and historical review
notes were inspected; changes received a further diff/integration review.

The 17 reference PDFs and generated images were inventoried as supporting assets.
This audit did **not** reread every page of every reference paper. It used the
existing scientific review, focused primary-source checking, analytical
counterexamples and synthetic tests. Historical JSON archives were parsed as
structured data; they are not current validation results. The existing
`archive/patches/my_review_diff.patch` was preserved as a historical patch, not applied.

Git internals, the third-party virtual environment, bytecode and pytest caches were
excluded from first-party source review. The environment was instead checked with
`pip check` and recorded in [environment.json](audit_evidence/environment.json).
The empty `models/` directory contained no model implementation and was removed
during the subsequent folder cleanup.

These were three complementary passes, not a claim that every line was independently
reread by three reviewers. This audit used one agent.

## Pass 1 — architecture and existing behavior

Traced import → per-curve point/timing selection → preprocessing → nonlinear fits
→ kinetics → TTS/spectrum → publication/comparison/simulation exports. Inspected
all active UI modules as well as the unused publication backup and root scripts.
Reviewed previous findings to distinguish resolved behavior from outstanding
scientific issues. Checked the existing tests against what they actually establish.

The application has a useful separation between numerical engines and UI, good
tests for delayed-start normalization and plateau recovery, and explicit curve
identifiers. Weak areas were comparison-state invalidation, export implementation,
documentation accuracy, and the large amount of branching inside UI functions.

Initial sandboxed tests stalled/failed in Windows temporary-directory access.
The diagnostic log identifies `PermissionError` in pytest setup/cleanup. Running
with approved temporary-directory access completed **133 tests in 30.12 s** after
the first small input/renderer corrections. This is not claimed as an untouched
baseline. A later intermediate run also passed 133 tests in 33.92 s.

## Pass 2 — counterexamples and corrections

| Priority | Confirmed problem | Correction and evidence |
|---|---|---|
| High | Comparison kept old results after input edits or a failed analysis. | Hash the complete sample inputs, clear results on change and before reanalysis; malformed manual input returns no partial dataset. AppTest covers edits, failure and clearing a sample. |
| High | Stress and storage/loss modulus headers could be accepted as relaxation modulus. | Reject explicitly incompatible measurement types with conversion guidance. Five header counterexamples are tested. Unlabelled input remains subject to the documented modulus convention. |
| High | “Raw 1/e” was evaluated on downsampled points, potentially hiding a brief recrossing. | Preserve all retained observations and evaluate the crossing there. A 5,001-point example is ambiguous before downsampling but appears unambiguous afterward; the regression test preserves this distinction. |
| Medium | A 600-DPI JPEG contained the 1200-DPI pixel dimensions, doubling its physical print size. | Render each format at its actual DPI; validate dimensions and metadata with Pillow. |
| Medium | Large publication images were generated on every rerun. | Prepare downloads only on request, offer TIFF resolution, limit raster allocation to 40 megapixels and report each format's failure separately. An oversized TIFF no longer prevents a smaller JPEG download. |
| Medium | BMP export passed an unsupported format directly to Matplotlib; CMYK controls were ignored or silently changed formats. | Shared serializer uses Pillow where required, checks compatible color spaces, preserves requested formats and supplies correct MIME types. Tests cover raster/vector signatures, RGB/CMYK, DPI and allocation limits. |
| Medium | Comparison had nonfunctional manual-axis controls and no modulus-plot download despite export controls. | Apply bounds in both renderers; implement the missing export; close figures after use. Interactive legend visibility is respected. |
| Medium | Publication legend checkboxes for Eyring/modulus plots were ignored; fixed widget keys prevented preset dimensions updating. | Honor visibility and synchronize sizes when presets change. AppTest checks both legends, double-column dimensions and no leaked figures. Tick weight/style controls now apply. |
| Medium | Observed-reference-normalized TTS curves can fail to overlap solely because acquisition starts differ. | Offer observed, absolute and explicitly model-extrapolated zero-time normalization. An analytical delayed-start KWW test confirms the extrapolated convention superposes equal shapes. The selected dual component controls shifts and invalidates stale TTS output. |
| Medium | Tv formulas returned fabricated zero or nonphysical roots and implied integral viscosity from characteristic KWW tau. | Shared guarded Maxwell-equivalent threshold helper; unavailable nonphysical roots; narrower labels/captions, including the publication legend. Tests cover zero/negative slopes and a known physical root. |
| Medium | Simulations could produce infinities and exclude the slow dual-mode decay from their generated window. | Compute Arrhenius ratios in log space, use the shared gas constant, validate physical parameters and span both mode times. Test a 10,000-fold separation and invalid inputs. Clear stale simulation caches on reruns. |
| Medium | Bar upload invented value=1 when no Value column existed; nonnumeric/negative errors could crash plots. | Reject missing/ambiguous value columns and invalid measurement/error data; reject duplicate categories that would overlap; validate axes and allow negative linear values. Load a given upload once so edits persist. |
| Medium | Global Matplotlib monkey patches silently removed text when rendering failed. | Remove the patches; normal library behavior and actual export specimens verify the standard equations. |
| Medium | Inactive publication backup contained old factor-of-1000 Tv math and obsolete `G0_max` keys. | Replace it with a compatibility import of the maintained publication implementation. Historical code remains in Git. |
| Medium | Root migration/probe scripts performed work when imported. | Add entry-point guards; disable obsolete source-rewriting migrations with an explanatory error. Preserve their historical bodies for inspection. |
| Medium | Educational text claimed automated kinetic BIC selection and identified exchange chemistry from entropy sign. | Align descriptions with implemented AICc relaxation selection, manual kinetics selection, discrete Ridge weights, secant-distance alpha selection and apparent physical parameters. |
| Low | “Literature validation” used an uncited illustrative dataset. | Rename the test and remove experimental/literature-validation claims. It remains a numerical sanity check. |
| Low | Fractional point exclusions were silently truncated; minute conversion could overflow; legacy XLS was advertised without its reader dependency. | Require integer point numbers, check converted values for finiteness, normalize corrupt XLSX errors and require conversion of legacy XLS. |
| Low | Launchers could use another pip interpreter, start in the wrong directory, or continue after installation failure. | Bind pip/Streamlit to the chosen Python, set the project directory, and stop on setup failures. Source checked; no fresh-machine installer run was performed. |

Also made example generation deterministic without regenerating the supplied
example CSV, declared Pillow explicitly, raised the Streamlit requirement to the
tested API generation, corrected version/runtime claims in Credits, and added
optional audit dependencies and a CI workflow.

## Pass 3 — validation and export inspection

- Added **29 regression cases** in `tests/test_audit_regressions.py`.
- Full integrated suite: **162 passed in 40.69 s, without warnings** after cleanup
  of four Python string-escape deprecation warnings. The final rerun is saved in
  [final_test_run.txt](final_test_run.txt).
- Flake8 critical-error selection (`E9,F63,F7,F82`, one process): passed.
- Bandit on application source: **zero findings**; see
  [security_audit.json](security_audit.json). This is static screening, not a
  penetration test or dependency vulnerability audit.
- `pip check`: no broken requirements. `git diff --check`: passed after whitespace
  cleanup. Every Python module and historical JSON artifact parsed successfully.
- Visually inspected default relaxation, Arrhenius, Eyring and empirical-modulus
  publication previews. Axes, units, legends and panel letters are visible without
  clipping in these specimens. Updated the Arrhenius legend to carry the
  Maxwell-equivalent qualifier into the exported figure.
- Actual single-column RGB TIFF: **4015 × 3543 pixels at 1200 DPI**; JPEG:
  **2007 × 1771 pixels at 600 DPI**. The pixel difference follows the requested DPI.
  CMYK TIFF/JPEG, BMP, PNG, PDF and SVG have format-level tests. No printer-specific
  ICC proofing or exhaustive visual review of every styling combination was done.

Reproduce with `python shared_review/audit_reproduce.py`. That script writes a fresh
inventory, environment snapshot, export metadata and image specimens in
`shared_review/audit_evidence/`. It does not overwrite the prior scientific review's
counterexamples or experimental files. Generated raster specimens are local outputs.

The CI configuration targets Windows/Linux with Python 3.11/3.13. **It has not run
on GitHub in this audit.** Local validation used Windows Python 3.11.13 and the
recorded installed packages. Broad dependency ranges are not a guarantee that every
permitted version combination works.

## Remaining work before scientific/release certification

1. **Experimental validation and parameter identifiability remain open.** Existing
   synthetic recovery does not establish reliable recovery from every noisy,
   truncated or multimodal experiment. Bootstrap/profile uncertainty, multiple
   initializations, held-out measurements and independent benchmarks remain needed.
   Fit covariance is local and kinetics SE does not propagate curve-fit uncertainty.
2. **Preprocessing remains heuristic.** Peak/drift selection, positive-modulus
   filtering, duplicate-time averaging and fitting downsampling can affect inferred
   parameters. Raw 1/e now precedes downsampling, but follows the other preprocessing.
   A systematic sensitivity study is still required.
3. **Spectrum baseline and regularization remain assumption dependent.** Tail
   subtraction can mistake an unresolved slow mode for equilibrium. The app now
   reports the measured tail fraction and explains why absence of a badge is not
   evidence of complete relaxation. It does not infer baseline uncertainty.
4. **TTS is still shifted data, not validated superposition.** The amplitude
   convention is explicit and testable, but there is no quantitative overlap test,
   thermorheological-simplicity test or physical continuity test for dual modes.
5. **Tv remains a stated proxy.** No new liquid-viscosity estimator was silently
   substituted. For zero-equilibrium KWW, the integral time includes a gamma factor;
   dual modes require amplitude-weighted contributions, and a permanent equilibrium
   modulus prevents finite liquid zero-shear viscosity. Independent modulus and
   model assumptions must be established before promoting the proxy to a physical Tv.
6. **Modulus/Eyring/coupled interpretation is limited.** Reference modulus is an
   observation, not equilibrium evidence. A fitted temperature trend or entropy
   sign alone does not identify bond chemistry. The coupled model is phenomenological.
7. **Maintainability needs another deliberate refactor.** Complexity screening still
   finds large branching functions in the analyzer, TTS and publication UI. Avoid
   changing physical behavior during that refactor; preserve the new counterexamples.
   The GUI still executes work for inactive tabs, and caching/upload performance on
   very large experimental datasets has not been benchmarked.
8. **Release coverage is incomplete.** Run the new CI matrix, perform real browser
   upload/download checks, test clean-machine BAT installation, and validate intended
   printer/color profiles. Compatibility with legacy instrument schemas, locales,
   worksheets beyond the first sheet and arbitrary metadata rows is not implied.

The scientific interpretation limits are consistent with the primary
[CAN characterization guide](https://pubs.acs.org/doi/10.1021/acspolymersau.5c00004)
and [linear viscoelasticity tutorial](https://doi.org/10.1039/D3PY01367G), and the
project's detailed [earlier scientific review](scientific_review/REPORT.md).
That earlier report retains its historical code references; this audit records
which issues were corrected and which were only clarified.

## Subsequent folder cleanup

Inactive root scripts, test images, intermediate logs and the historical patch
were relocated under `archive/`; see its README. Current source, tests, reference
papers, final test results and export evidence were retained. Python/pytest caches
were removed. The file inventory was refreshed to reflect the new locations.
