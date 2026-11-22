# Fit reliability development preview

Source version **2.0.0-rc.3.dev.1**. This work follows the published rc.2 candidate;
it is not a newly verified Windows installer. Existing rc.2 installers are unchanged.

## What changed

Two-Maxwell fitting now tries 13 deterministic starting guesses per curve, or 25
when fitting a plateau. It keeps the successful solution with the smallest sum of
squared normalized-modulus residuals. The historical starting guess remains one
candidate. Each temperature remains independent: no Arrhenius constraint is imposed.
Other models retain their existing fitting method.

The **Fit reliability** tab shows residuals, adjacent-observation correlation,
converged/attempted starts and near-equivalent solutions. The start scatter plot
shows fast versus slow time on logarithmic axes; hover for residual sum of squares.
The full starting-guess table includes failures, rather than hiding them.

For two-Maxwell, **Check stability of selected curves** adds four scenarios:

1. The current fit, unchanged.
2. All retained observations before logarithmic downsampling.
3. The earliest 80% of the current time span, using current-fit observations.
4. The earliest 60% of the current time span, using current-fit observations.

These checks hold loading origin, first retained reference, modulus normalization,
manual exclusions and plateau policy fixed. Automatic peak/drift trimming is not
repeated. A fitted plateau is refitted in each scenario; a fixed plateau stays fixed.
The window percentage is of elapsed span, not of the number of points. Scenarios
with fewer than eight points are explicitly unavailable.

Checks do not replace the current fit, change kinetics selections or drop curves.
All times and moduli, signed percentage changes, point counts, reference information,
plateau estimates and warnings are available in the stability CSV. JSON also includes
optimizer trials and the analysis identity. The Report tab incorporates checks only
for its current analysis and selected curves, and names curves not yet checked.
Changing fitting inputs clears old checks. Selecting fewer curves filters exports.

Projects still save analysis recipes and recalculate fits when reopened. Run the
optional sensitivity checks again after reopening; retain CSV, HTML and JSON exports
as immutable records of previous calculations. Opening older projects in this
version can change numerical results because the optimizer now searches more starts.

## How to interpret it

- Near-best solutions have RSS within `max(0.001 × best RSS, 1e-12)` of the minimum.
  A fast or slow time range exceeding 25% of the winning time triggers review.
  This is an explicit numerical screening convention, not a likelihood interval.
- Absolute adjacent residual correlation of at least 0.5 triggers a review note.
  It describes neighboring observations, including unevenly spaced observations;
  it is not a significance test. Tiny residuals (RMSE at most 1e-8) and constant
  residual sequences have no reported correlation.
- A time change above 20% in a sensitivity scenario triggers review. This is a
  practical review threshold, not a universal scientific acceptance criterion.
- Multi-start agreement cannot establish identifiability. Local covariance errors
  still assume the fitted error model, and these checks do not propagate uncertainty
  into kinetics. Correlated residuals, incomplete observation windows, small mode
  amplitudes, similar times and plateau competition all need scientific judgment.
- These perturbations are not bootstrap confidence intervals. Removing the tail
  changes the observations; denser sampling changes their least-squares weighting.

## Beginner walkthrough

1. Import and review data, select **Two-Maxwell (Prony)** and the appropriate plateau.
2. Run Analysis, then open **Fit reliability**.
3. Choose a curve. Inspect residual patterns and the different starting solutions.
4. Click **Check stability of selected curves**. Compare the fast and slow changes,
   and read the warnings even when all changes are below 20%.
5. Download the tables or prepare a new report. Keep the project separately.

The published installer walkthrough remains in [QUICK_START.md](QUICK_START.md).

## Validation on 22 November 2026

The local suite passed **255 tests**. A further 29 focused checks passed after
the final table/chart presentation changes. Tests cover known fast/slow values
and loading-time moduli with zero, fixed and fitted plateaus; recovery after a
failed first start; explicit total failure; unresolved modes with equal RSS;
short-window insufficiency; fixed-reference preprocessing; report selection and
stale-result invalidation. The app workflow test also verifies the stability
calculation does not replace the primary fitted parameters.

The source desktop self-test also passed with non-loopback Python DNS and socket
connections blocked in the analysis and server processes. It exercised import,
bulk exclusion, fitting, stability, project save, a fresh-session reopen,
recomputed identical stability scenarios, reports and figure exports. This is
process-level offline verification, not an operating-system network isolation test
or verification of a newly built installer.

Experimental measurements and their derived results are kept local. Run the
parameter audit on your own dataset with:

```powershell
.venv\Scripts\python.exe validation/reliability_check.py "path\to\workbook.xlsx" --output .build-tools/validation-reliability
```

The output JSON records every scenario, reference, diagnostic and comparison;
the CSV contains the scenario table. Keep these outputs private unless you intend
to share the experimental information they contain. Numerical and workflow checks
do not replace independent physical validation across materials.
