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
