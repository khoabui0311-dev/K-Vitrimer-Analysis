# VitriFit independent benchmark protocol

The benchmark suite is **not** calibrated on PEDOT:PSS–VUEG, LCE2, VUGT,
or any semi-IPN. These remain downstream application and robustness examples.

## Tier A — mathematical ground truth

Use `vitrifit2.benchmark_suite` to generate reproducible, known-parameter
Maxwell, KWW, dual-Maxwell, Arrhenius and VFT cases. Compare recovered
parameters, residuals, confidence intervals and model selection. Run cases
both noise-free and with seeded Gaussian noise. Noise is intentionally not
clipped: negative instrument-like tails must trigger log-axis safeguards.

**Acceptance targets** (initial policy; tune only with documented evidence):

- Noise-free Maxwell/KWW parameters: relative error below 1% when identifiable.
- Noise-free Arrhenius apparent Ea: absolute error below 0.1 kJ/mol.
- Repeated seeded generation: exactly reproducible arrays.
- Noisy or incomplete curves: return uncertainty/quality warnings, not
  fabricated precision. Fit failures are reported rather than hidden.
- Model mismatch: residual and model diagnostics must identify that a
  single Maxwell model is inadequate for a sufficiently separated dual mode.

These are benchmark **requirements**, not claims that VitriFit currently passes.

## Tier B — published vitrimer comparison

**Dynamic Crosslinking: An Efficient Approach to Fabricate Epoxy Vitrimer**
(Materials 2021, 14, 919; DOI: 10.3390/ma14040919).
Published 1/e stress relaxation times, in seconds:

| T (°C) | EVS | EVD |
|---:|---:|---:|
| 140 | 9330 | 5706 |
| 160 | 2100 | 1206 |
| 180 | 930 | 450 |
| 200 | 336 | 198 |
| 220 | 132 | 60 |

Reported apparent Ea: EVS 92.29 kJ/mol; EVD 88.07 kJ/mol.
These are rounded **summary observations**, not independently acquired
instrument traces. Re-fitting rounded values need not reproduce the paper's
regression exactly. Do not create fictitious raw curves from these points.
Cite the DOI and retain the tau definition whenever displaying results.

## Tier C — experimental raw-data validation (pending)

Acquire open, license-compatible raw relaxation traces from an independent
vitrimer study or obtain author permission. Record sample chemistry,
instrument geometry, strain, temperature, acquisition delay, preprocessing,
tau definition, source URL, license, and any digitization uncertainty.
Until such data are available, this tier is **not passed**.

## Tier D — application testing

Only after Tiers A–C, use PEDOT:PSS–VUEG and LCE/VUGT to stress-test
complex relaxations and workflow usability. Label Ea as *apparent*;
do not infer bond-exchange kinetics, Tv, or microscopic mechanisms solely
from a macroscopic relaxation fit.

## Release gate

A Windows clean-install run, browser upload → per-curve trim/undo → fit →
compare → export, and v1 publication golden-image comparisons are separate
required checks. Passing synthetic tests alone does not constitute a release.


## Model discrimination diagnostics

`vitrifit2.benchmark_diagnostics.evaluate_relaxation_models` fits the same
observations using Maxwell, KWW and two-Maxwell models. It reports RMSE,
AICc and lag-one residual correlation. This is an **unweighted additive
Gaussian-error** comparison, not a universal likelihood model.

`rank_relaxation_models` orders successful fits by AICc, identifies
alternatives within delta AICc < 2, and always warns that statistical
preference is not proof of bond-exchange mechanism. Failed fits are excluded
rather than treated as arbitrarily poor models.

**Limitations:** AICc assumes an appropriate independent-error likelihood.
Serial correlation in relaxation data, heteroscedastic instrument noise,
different preprocessing, and parameter non-identifiability can invalidate
naive rankings. The benchmark must expose these limitations rather than
silently selecting a mechanistic explanation. In particular, a dual-mode
fit is not evidence of two distinct molecular exchange reactions.


## Local parameter identifiability

`assess_parameter_identifiability` evaluates the singular values of a
finite-difference prediction Jacobian at the fitted optimum. Positive
relaxation times are represented on a logarithmic parameter scale to
reduce arbitrary units-related conditioning artifacts. A high condition
number indicates weak local separation of parameter effects.

**Interpretation limitations:** This is a *local numerical diagnostic*, not
proof of global identifiability, valid confidence intervals, or a physical
mechanism. In particular, exchanging the two Maxwell arms can yield an
equivalent representation. Near-identical time constants, short measurement
windows, noisy plateaus and boundary-constrained fits require profile
likelihood or bootstrap checks before quantitative claims. Do not report
precise exchange-kinetic parameters solely from a well-conditioned fit.


## Bootstrap uncertainty (initial implementation)

`vitrifit2.benchmark_uncertainty.bootstrap_relaxation` performs fixed-seed
percentile residual bootstrap for Maxwell, KWW and two-Maxwell. It reports
point estimates, percentile limits, successful/failed refits and the seed
controlled by the caller. For two-Maxwell, exchangeable arms are canonicalized
in the bootstrap draws before marginal intervals are computed.

**Caveats:** Independent residual resampling assumes exchangeable errors.
DMA stress-relaxation traces may exhibit time-correlated and
heteroscedastic errors, so these intervals are preliminary, not validated
experimental confidence intervals. Parameter bounds, multimodal solutions
and poor identifiability can also compromise percentile intervals.
Do not interpret 95% confidence as guaranteed coverage for a single
synthetic realization. Assess empirical coverage over repeated independently
seeded datasets before claiming calibrated intervals.


## Measurement-window sensitivity

`vitrifit2.benchmark_windows.window_sensitivity` refits Maxwell or KWW
using progressively shorter prefixes of a trace. The default fractions
(100%, 75%, 50%, 25%) refer to the **number of observations** and must
not be described as the fraction of elapsed time. Each result records
the actual final time, point count, fitted parameters and relative
deviation from the full-window fit.

A stable estimate under truncation is useful evidence of numerical
robustness but is not proof of model validity. A short window that never
reaches a meaningful relaxation fraction can give weakly identified tau
even when the optimizer converges. Use this alongside Jacobian
conditioning, residual checks and independent replicates.


## Monte Carlo bootstrap coverage

`bootstrap_coverage_study` creates independent, fixed-seed noisy Maxwell
or KWW datasets and computes the fraction of nominal percentile bootstrap
intervals containing the known synthetic parameters. Dataset-level failures
are reported separately and excluded from the coverage denominator.
A small smoke test (2–3 datasets, 20 resamples) checks software behavior,
**not** whether a 95% interval is calibrated. A scientifically meaningful
coverage study requires substantially more independent datasets, noise
models and confidence-level diagnostics. This is conditional on the
correct synthetic model and does not establish performance on real
instrument data.


## Characteristic-time observability

`relaxation_observability` computes the fitted model's predicted 1/e
crossing and classifies it relative to the first and last measured times.
Maxwell and KWW have analytic crossing times; two-Maxwell uses numerical
root finding. For two-Maxwell, the overall 1/e crossing generally differs
from either individual mode time constant.

A crossing **inside** the acquisition window is not necessarily an
empirically observed crossing: the diagnostic only checks the model
prediction and time span. Real measurements should additionally verify
that the measured normalized curve brackets the threshold, and that
noise and uncertainty permit a reliable crossing estimate.
Crossings outside the window are extrapolations and must be labelled.
