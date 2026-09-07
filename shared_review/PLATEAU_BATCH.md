# Plateau and activation-energy batch — 2026-09-07

## Scope and usage

The main workflow remains import, plot, fit, analyse, export. In the sidebar select
Maxwell or Single_KWW and choose Long-time plateau: Zero (unchanged default), Fit,
or Fixed. Fixed values are in MPa and apply to each curve; a value at or above a
curve's retained reference modulus rejects that curve with an explicit reason.
Dual_KWW retains its existing zero-plateau model.

The physical model is G(t) = G_inf + (G_initial - G_inf) exp(-(t/tau)^beta).
The fitted normalized prediction is q + (1-q) exp[-(t/tau)^beta + (t_ref/tau)^beta],
where q = G_inf / G(t_ref). Maxwell uses beta=1. This is algebraically the same
physical model after reference normalization; the loading origin is preserved.
Fitted q is constrained to [0, 1), and G_inf is reported in MPa. Fit adds one
parameter to AICc/BIC; Fixed adds none. Base popt ordering is preserved for existing
consumers, with plateau fields stored separately. full_covariance includes q when
fitted; covariance remains the base parameter marginal block.

## Interface and downstream analysis

- Parameter table opens by default and includes plateau, local standard error,
  retained time range and fit flags. Residuals are available in an expander.
- Flags cover tau outside the window, large local tau uncertainty, a fitted
  plateau not yet approached, large plateau uncertainty and tiny dual components.
  Thresholds are screening heuristics: tau SE >50%, plateau fraction SE >0.05,
  final relaxing amplitude >5% of the reference relaxing amplitude, dual weight <5%.
- Flagged curves remain selectable for kinetics; included flags trigger a warning.
  Dual fits now allow selection of fast or slow tau. Component selection resets
  its kinetics editor state. Sorting modes does not establish physical identity.
- Arrhenius output shows apparent Ea, regression SE, R2, curve count and temperature
  range, with beta versus temperature for KWW fits. SE does not propagate each
  relaxation fit's uncertainty. The main Arrhenius plot no longer displays the
  Maxwell viscosity/Tv extrapolation; advanced publication calculations are unchanged.
- CSV downloads record fit results, kinetics inclusion choices and Arrhenius
  output. Provenance JSON records plateau settings, parameters and flags. Plateau
  configuration participates in cache/state identity.

## Limitations and review targets

A finite window cannot establish a permanent plateau; local covariance is not a
global identifiability test. Reference normalization and preprocessing can affect
uncertainty estimates. No profile likelihood or bootstrap was added in this batch.
No automatic inference of bond-exchange barriers or permanent crosslinks is made.
Raw 1/e keeps its original definition relative to the observed reference, rather
than the plateau-subtracted relaxing amplitude. Advanced spectrum, TTS and
viscosity/Tv conventions identified in scientific_review/REPORT.md remain separate
follow-up work. Publication relaxation plots use stored fitted curves, including
the plateau. Reviewers should focus on the normalization equation, parameter count,
fixed-value rejection, downstream component choice and uncertainty wording.

## Validation

tests/test_plateau_fitting.py covers delayed-start Maxwell/KWW recovery for fitted
and fixed plateaus, noisy and zero-plateau limits, truncation flags, invalid inputs,
known 65 kJ/mol recovery across temperatures, and Streamlit plateau configuration
and invalidation. Targeted run: 9 passed. Full-suite result is recorded in WORK_LOG.md.

Changes remain uncommitted in the existing working tree; earlier agent changes
were preserved. No deployment or experimental validation was performed.
