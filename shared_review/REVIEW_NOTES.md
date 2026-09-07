# Independent review notes

Reviewer: review agent. Status: **final reviewed**, 2026-09-07.
Both findings below are resolved in current source; historical findings and
acceptance checks are retained for handoff. No outstanding finding from this review.

## Required checks

1. **KWW normalization:** preserve elapsed time and fit `f(t)/f(t_reference)` after
   normalizing by the measured reference modulus. Merely preserving time does not
   fix the normalization bias. Check noiseless tau=300 s, beta=0.5 at first
   observations 0.01, 1, 30, and 100 s, and after an explicit cutoff.
2. **Measured 1/e interval:** report crossing minus reference time. A late-start
   KWW interval is not its intrinsic fitted tau. Missing or ambiguous crossings
   must not enter ordinary kinetics regression.
3. **Fit validity:** forced optimizer exceptions and nonfinite returned parameters
   cannot produce a successful result or a fabricated curve copied from data.
4. **Spectrum scaling:** include t=0 safely in the input; define positive tau grid
   limits. Check plateau plus kernel times modal weights against original input
   units at relaxing amplitudes 0.006, 0.6, and 60. Avoid amplitude thresholds whose
   behavior changes when units change. State discrete modal-weight convention.
5. **Replicates:** preserve independent curve identities through all consumers;
   temperature-only dictionaries must not silently overwrite repeated temperatures.
6. **Application state:** different data with identical temperatures must invalidate
   spectrum, mastercurve, kinetics, and associated editor state. Curve selection
   and TTS reference changes must invalidate mastercurve results. A failed new
   parse must not leave old results presented as the newly requested analysis.
7. **Shared equations:** analysis, publication, and comparison Van 't Hoff plots
   must all call the engine predictor. Publication relaxation fits should use the
   exact normalized prediction used during fitting.
8. **Modulus interpretation:** recorded normalization modulus is the first retained
   observed modulus, not an inferred t=0 modulus. Label this distinction because
   changing cutoffs can change its value and therefore the modulus-temperature fit.

## Scope of independent review

Source inspection and regression-risk assessment, followed by integrated source
review and verification of both requested corrections.

## Integration review

Reviewed the working implementation after integration (2026-09-07). The root
agent reports 104 passing tests and is adding Streamlit workflow tests. This
review independently inspected source and test coverage; it did not repeat the
full test suite or visually inspect high-resolution publication downloads.

### Actionable finding

- **P2 — publication annotation confuses interval with crossing coordinate.**
  In `can_relax/gui/tabs/tab_pub_main.py`, Figure 1 uses `Crossing_Time` both for
  the marker position and the numeric `tau*` annotation. With a first retained
  time of 30 s and an exponential relaxation time of 50 s, the marker belongs at
  x=80 s but the measured interval is 50 s. Keep the marker coordinate and use
  `Tau_1e / x_factor` for an interval annotation, or rename the annotation to
  `t_cross`. Acceptance: nonzero-start data produces the correct position and
  a clearly distinguished interval label in seconds and minutes. Sent to the
  integrating agent for correction.

### Follow-up recommendation

- **P3 — replicate plot labels:** Curves, Spectrum, and publication legends
  retain temperature-only names. Replicate data are preserved, but a viewer
  cannot identify individual replicates from the legend. Add the Curve ID to
  these labels when duplicate temperatures are present.

### Confirmed by source inspection

- Conditional Maxwell/KWW/dual-KWW predictions retain the elapsed origin and
  reference normalization; publication uses the stored fitted prediction.
- Spectrum weights are returned in input units, with reconstruction diagnostics;
  zero-time observations receive a positive tau-grid lower bound.
- Fit failures no longer provide copied-data predictions or successful status.
- Active parser consumers use curve records. Selection, fit tables, kinetics,
  publication modulus lookups, and mastercurve shifts preserve Curve IDs.
- Empty selection and empty kinetics data have guards in the active application
  and publication paths. Insufficient distinct temperatures return no kinetics
  fit rather than raising a regression exception.
- Main, comparison, and publication Van 't Hoff predictions share the engine
  function. Data content/settings and reference changes invalidate derived state.

## Final resolution verification

- **P2 resolved:** `tab_pub_main.py:191` now annotates `Tau_1e / x_factor` while
  retaining `Crossing_Time / x_factor` for marker and text placement. This keeps
  the interval value separate from its absolute plot coordinate, including
  seconds/minutes conversion.
- **P3 resolved:** `app.py:328` and `app.py:338` include Curve IDs in measured and
  fitted curve traces; `app.py:672` includes them in spectrum traces;
  `tab_pub_main.py:161` includes them in publication legend labels.
- The integrating agent reports **20 passing expanded focused tests**, including
  Streamlit workflows for replicates, incomplete raw curves, dataset replacement
  at the same temperatures, empty selection, model/reference changes, and the
  main Van 't Hoff path. This reviewer verified the current corrections by source
  inspection; independent visual verification of exported figures remains outside
  this review's scope.
