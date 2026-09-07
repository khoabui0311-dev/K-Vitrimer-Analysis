# Validation — correctness batch, 2026-09-07

Status: implemented, integrated, independently reviewed.

Follow-up: replicate/UX improvements subsequently passed **110 tests in 19.15 s**.
See REPLICATE_UX_FOLLOWUP.md for scope and checks; the original independent review
below predates that follow-up.

## Final checks

- `.venv/Scripts/python.exe -m pytest -q --tb=short`: **109 passed in 14.69 s**.
- `git diff --check`: passed. Git emitted only Windows line-ending conversion notices.
- Python AST parse of application modules: passed during integration.
- Independent source review: no outstanding findings from that review; see REVIEW_NOTES.md.

Pytest now discovers tests/ only. The root plotting experiments contain no test
functions and globally patch Matplotlib; importing them during collection stalled
the first whole-repository workflow run. That run was interrupted. Tests use the
Agg renderer and the final suite passed with discovery isolated. Windows temporary
directory access required approved execution outside the filesystem sandbox.

## Numerical evidence

Noiseless KWW, tau=300 s, beta=0.5; 200 samples through 3000 s:

| First retained time (s) | Previous fitted tau (s) | Corrected tau (s) | Corrected beta | R2 |
|---|---:|---:|---:|---:|
| 0.01 | 303.923 | 300.000 | 0.500 | 1.000 |
| 1 | 340.751 | 300.000 | 0.500 | 1.000 |
| 30 | 510.621 | 300.000 | 0.500 | 1.000 |
| 100 | 672.732 | 300.000 | 0.500 | 1.000 |

The zero-time case and a separated dual-KWW late-start case also pass parameter recovery.
The previous values are from the initial review; corrected values were rerun after integration.

Other regression coverage:
- An unobserved 1/e crossing yields not_reached/NaN, not the observation endpoint.
- Repeated noisy crossings are ambiguous; a 30 s start with 50 s interval places
  the crossing at 80 s while retaining a 50 s interval.
- Optimizer exceptions and nonfinite parameters cannot produce valid fits.
- Discrete spectra reconstruct inputs within 2.5% maximum reference-relative error
  for the selected synthetic benchmark at amplitudes 0.006, 0.6, and 60, with and
  without plateau subtraction; t=0 is supported.
- Van 't Hoff and coupled fit predictions agree with their shared prediction functions.
- CSV and XLSX documented formats, signed temperatures, units, malformed input,
  repeated temperatures, and duplicate headers have regression coverage.
- TTS retains three separate shift entries for three curves, including two replicates.

## Streamlit workflow evidence

AppTest exercises startup, example parsing, fit results, Van 't Hoff rendering,
mastercurve generation, reference changes, model changes/reanalysis, empty selection,
replicate preservation, missing raw crossings, and replacement data with unchanged
temperatures. Both workflow tests pass without application exceptions.

High-resolution publication download generation is stubbed in these integration tests
to avoid generating 1200-DPI images on each UI rerun. Publication rendering executes,
but exported TIFF/JPEG appearance and a manual browser session were not visually verified.

## Tested environment

Windows; Python 3.11.13. numpy 2.4.6, pandas 3.0.3, scipy 1.17.1,
scikit-learn 1.9.0, streamlit 1.58.0, matplotlib 3.11.0, plotly 6.8.0,
openpyxl 3.1.5, pytest 9.0.3. This records the tested environment; it is not a
claim that every version permitted by requirements.txt is compatible.

## Remaining scientific limitations / next reviewer recommendations

1. Assess nonlinear parameter identifiability and uncertainty using noisy simulations
   and independent experimental benchmarks. Successful recovery here is not full validation.
2. Assess sensitivity to trimming, positive-modulus filtering, normalization noise,
   and downsampling. Those heuristic choices still affect noisy experimental data.
3. Validate TTS overlap and shape compatibility; shifting by fitted tau alone is not
   evidence of thermorheological simplicity. Reference temperature with replicates
   now supports either the arithmetic mean at the selected temperature or an explicit
   reference curve (see subsequent replicate/UX follow-up).
4. Assess plateau estimation and regularization sensitivity. Tail subtraction does not
   prove equilibrium. Discrete modal weights are not a grid-independent density.
5. Van 't Hoff currently uses first-retained measured modulus. It is not an inferred
   plateau; differing acquisition starts/cutoffs can affect physical interpretation.
6. Visually inspect publication downloads and validate historical data formats against
   the now-explicit parser contract. Legacy dict parsing rejects replicate temperatures;
   callers needing replicates must migrate to parse_curve_records.
7. Lock a supported environment and validate additional platform/version combinations.

No source commit, deployment, network share, or external message was created.
