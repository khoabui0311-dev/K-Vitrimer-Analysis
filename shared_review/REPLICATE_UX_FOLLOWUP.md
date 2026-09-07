# Replicate reference and spectrum UX follow-up

## Scope
User requested robust replicate mastercurve references, compact legends, and a
prominent spectrum warning indicator. On entry, another review had already changed
the working tree to average reference taus and conditionally label duplicates.
Those changes were preserved and extended, not overwritten with first-curve selection.

## Implementation
- Default reference uses the arithmetic mean of selected replicates at the reference
  temperature. Optional `ref_curve_id` selects one unambiguous curve; invalid IDs
  and temperature/ID mismatches are rejected. Returned metadata records tau, method,
  and contributing Curve IDs. This avoids silently choosing a replicate.
- UI offers a replicate selector only at duplicated reference temperatures. Changing
  the chosen reference invalidates an existing mastercurve.
- Shared label helper used by analysis, spectrum, and publication: IDs appear only
  for duplicate temperatures in the displayed selection. Selection controls retain
  identifiers when needed to distinguish available replicates.
- An orange badge at the top of Spectrum reports how many curves trigger the
  existing 80%-of-endpoint heuristic. It clears when no curve triggers the check.
  Warning wording now correctly says approaches/exceeds the window, instead of
  claiming every flagged value exceeds the endpoint itself.

## Checks
- Numerical tests cover averaged reference, reordered replicas, explicit anchor,
  unknown/mismatched reference IDs, and compact/duplicate labels.
- AppTest covers averaged vs explicit reference, invalidation, badge appearance and
  disappearance. The badge fixture controls the spectrum summary statistic to test
  UI state; this does not validate the scientific detection heuristic.
- Initial sandbox run blocked pytest temporary directories; reran with approved access.
- A fixture used integer temperature options; its selection was corrected from 100.0
  to 100 for AppTest's string-based option lookup.

Final verification: **110 tests passed in 19.15 seconds**; `git diff --check` passed
after removing one trailing-whitespace line. High-resolution export visual
QA, alternative replicate weighting, and TTS overlap validation remain out of scope.
