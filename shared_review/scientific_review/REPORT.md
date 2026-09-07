# Further scientific review — K-Vitrimer Analysis

Date: 2026-09-07. Scope: scientific interpretation and numerical behavior of the
current working tree. This review adds evidence and recommendations; it does not
change application source or certify experimental validity.

**Assessment:** the recent corrections improve computational consistency, but several
remaining assumptions can still produce misleading physical parameters. The highest
priorities are distinguishing finite-window tails from equilibrium plateaus, separating
characteristic relaxation times from viscosity, and preventing apparent dissociation
parameters from being inferred solely from acquisition-dependent modulus values.

## Evidence and scope

All 17 local PDF files were indexed and screened for relevance. Six papers received
focused section-level reading; this is not a claim to have critically read every page
of the collection. The two copies of the Hayashi/Ricarte review have the same title
but different file hashes. See [reference inventory](REFERENCE_INVENTORY.md).

The close-reading sources are identified below. Page numbers are **PDF page numbers**,
with printed page numbers given where helpful. Three equation pages were rendered and
visually checked to avoid relying solely on imperfect mathematical text extraction.

| ID | Local source | Relevant sections read |
|---|---|---|
| S1 | [Wink et al., A Practical User Guide to Stress Relaxation Spectra of Dynamic Covalent Networks](../../../References/Vitrimer%20Rheology/a-practical-user-guide-to-stress-relaxation-spectra-of-dynamic-covalent-networks.pdf) | PDF pp. 2–3, 5–6, 8; inversion, truncation, equilibrium modulus, conclusions |
| S2 | [Ricarte & Shanbhag, A tutorial review of linear rheology for polymer chemists](../../../References/Vitrimer%20Rheology/d3py01367g.pdf) | PDF pp. 9, 25–26; viscosity integral, Box 6 KWW, TTS; printed pp. 823, 839–840 |
| S3 | [Berne et al., How to Characterize Covalent Adaptable Networks](../../../References/Vitrimer%20Review/how-to-characterize-covalent-adaptable-networks-a-user-guide.pdf) | PDF pp. 17, 19–20; apparent activation energies and molecular interpretation |
| S4 | [Van Lijsebetten et al., Characterising different molecular landscapes in dynamic covalent networks](../../../References/Vitrimer%20Rheology/d2sc05528g.pdf) | PDF pp. 4, 6; Eyring equation 2, network model equation 3, Van 't Hoff equation 4 |
| S5 | [Lin et al., Molecular Dynamics Simulation and Theoretical Analysis of Structural Relaxation, Bond Exchange Dynamics, and Glass Transition in Vitrimers](../../../References/Vitrimer%20Rheology/molecular-dynamics-simulation-and-theoretical-analysis-of-structural-relaxation-bond-exchange-dynamics-and-glass.pdf) | PDF pp. 5–6; SC-ECNLE model and additive exchange-time equation 11 |
| S6 | [Edera et al., Resolving the relaxation complexity of vitrimers](../../../References/Vitrimer%20Rheology/HAL20240115ManuscriptEDERA.pdf) | Local preprint, PDF pp. 2, 12, 14; distinction between TTS and time–temperature equivalence |

Five synthetic/analytical probes are reproducible with:

```powershell
.\.venv\Scripts\python.exe shared_review/scientific_review/reproduce.py
```

Results are in [numerical_evidence.json](numerical_evidence.json). The script writes
only review outputs. These probes are intentionally constructed counterexamples,
not experimental benchmarks or estimates of failure frequency. The prior 110-test
result remains historical; the full suite was not rerun for this read-only source review.

## Findings, in priority order

### F1 — High: tail subtraction can erase the very evidence used by the warning

**Code:** `can_relax/core/spectrum.py:36` and `can_relax/gui/app.py:676` vicinity.

S1 section 3.1.4 permits equilibrium-modulus subtraction with caution. It does not
establish the final 5% of any finite measurement as equilibrium. Section 3.1.3 and
the conclusions instead stress observing the relaxed plateau. The paper's approximate
five-characteristic-times recommendation pertains to its studied conditions and is
not a universal completeness threshold for every broad spectrum.

The app averages the final 5%, subtracts it, then checks whether a statistic of the
resulting spectrum approaches the observation endpoint. These steps are not independent:
removing a slow tail can move the spectrum away from the boundary and suppress the alert.

**Reproduced:** noiseless G(t)=exp(-t/1000), 200 geometrically spaced observations from
0.01 to 300 s, true equilibrium modulus zero, automatic alpha:

| Setting | Estimated equilibrium | Weighted geometric mean tau | Window flag | Relative reconstruction RMSE |
|---|---:|---:|---|---:|
| No subtraction | 0 | 990.73 s | Yes | 0.317% |
| Tail subtraction | 0.7869 | 140.49 s | No | 1.134% |

The unsubtracted peak is at the upper grid boundary (1500 s), so its mean being close
to 1000 s should not be interpreted as proof of a uniquely recovered spectrum either.

**Recommendation:** independently assess the original tail and measurement window;
offer baseline off / user-specified / estimated modes; report baseline uncertainty and
show with/without-subtraction sensitivity. Never use the absence of the current badge
as evidence that complete relaxation was observed. Gate equilibrium claims on measured
plateau evidence, not a fixed sample fraction.

### F2 — High: a permanent plateau can masquerade as a second chemical relaxation

**Code:** `core/models.py` zero-asymptote models, `core/analyzer.py:80`,
`gui/app.py:407` slow-mode selection, and `core/tts.py:51`.

All relaxation-fit candidates tend to zero. A finite plateau is therefore represented
by failure to fit, stretching, or a second mode with an extremely long time. S1 explicitly
distinguishes a nonzero equilibrium contribution from a finite relaxation mode; its
conclusion also warns against assigning peaks to distinct chemistries without evidence.

**Reproduced:** G(t)=0.3+0.7 exp(-t/10), through 1000 s. Automatic curve-model selection
chooses Dual_KWW with R²=1.0, A≈0.7, tau1≈10 s and tau2≈8.26×10^11 s. There is no
second finite chemical time in the generating model. The current out-of-window caption
is helpful, but the parameter remains available to kinetics and TTS.

**Recommendation:** include an explicit equilibrium/offset model when physically
appropriate, expose unresolved slow modes as censored or unidentifiable, and prevent
them from silently feeding ordinary Arrhenius/Tv calculations. Compare competing
plateau and slow-mode explanations using extended measurements, not R² alone.

### F3 — High: characteristic KWW tau is not the viscosity-equivalent time

**Code:** `gui/app.py:462`, `core/simulator.py:8`, and related publication/comparison
Tv calculations use the Maxwell relation with the chosen characteristic tau.

S2 equation 12 defines liquid zero-shear viscosity as the area under G(t). Box 6
explicitly derives the first-moment KWW time. For a zero-equilibrium KWW model:

\[
\eta_0=\int_0^\infty G(t)\,dt
=G_0\tau\,\Gamma(1+1/\beta).
\]

For dual KWW, the corresponding integral is the sum of each mode's amplitude times
its gamma-corrected time. For a material with a true permanent equilibrium modulus,
the total integral diverges; reporting a finite liquid viscosity from it is inappropriate.

**Analytical check:** beta=0.5 gives eta0=2 G0 tau. With constant shape and modulus,
Ea=80 kJ/mol, a Maxwell-based threshold reported at 100°C would instead occur near
110.31°C after this factor is included. This isolates one assumption; it is not a
prediction for any particular sample. Beta varying with temperature also changes
the apparent activation slope, not merely the prefactor.

**Recommendation:** report characteristic tau, first-moment time, and viscosity as
different outputs. Label current Tv as a Maxwell-equivalent extrapolation until its
definition is corrected. Require a liquid/no-equilibrium model and appropriate modulus,
and propagate shape, modulus, and extrapolation uncertainty.

### F4 — High: observed reference modulus is not sufficient for dissociation thermodynamics

**Code:** `core/kinetics.py:106` and the observed G0 lookup in `gui/app.py:443`.

S4 does not simply fit a universal sigmoid to the first recorded modulus. It maps a
chemistry-specific statistical network model to plateau modulus, infers association
probability, then relates that probability to a dissociation equilibrium constant.
Only then does it apply the Van 't Hoff relation. Supporting derivations are in that
paper's ESI, which was not reproduced in this review.

The app's A*T/(1+exp(-dH/RT+dS/R)) is a simplified occupancy-style model, not a general
thermodynamic derivation for arbitrary vitrimer chemistry. Its input is also the
first-retained modulus, which can decrease with temperature because relaxation has
already occurred before that observation. This happens even with the same cutoff
at every temperature.

**Reproduced:** a nondissociating Maxwell material has true initial modulus 0.01*T_K;
its relaxation times have Ea=80 kJ/mol and tau(120°C)=100 s. Observing modulus first at
30 s across 100–180°C gives an apparent dissociation fit of dH=140.70 kJ/mol,
dS=344.52 J/(mol K), R²=0.99663. The material in this construction has no dissociation
equilibrium to estimate. This probe feeds exact observed reference values directly to
the kinetics engine; it isolates the physical interpretation from preprocessing noise.

**Recommendation:** call this an empirical temperature–modulus fit unless the equilibrium
and network assumptions are supplied. Separate measured plateau modulus, extrapolated
zero-time modulus, and observed reference modulus. Require chemistry-specific mapping
and independent equilibrium evidence before presenting dH/dS as bond thermodynamics.

### F5 — Medium/high: conditional normalization needs a consistent TTS amplitude convention

**Code:** `core/tts.py:85–97` shifts time but concatenates each curve's own reference-normalized modulus.

The corrected fit uses f(t)/f(t_start), which preserves the intended KWW parameters.
However, the denominator differs with tau and acquisition start. Even two intrinsically
superposable curves need not overlap after shifting these ratios horizontally.

**Analytical counterexample:** beta=0.5, taus 50 and 200 s, both first observed at 30 s.
After the correct horizontal shifts, at reference time 100 s the plotted ratios are
0.52749 and 0.35811: a difference of 0.16938. Their underlying zero-time-normalized
KWW functions have identical shape and would superpose. This is a downstream amplitude
convention issue, not evidence that the conditional-fit correction should be reversed.

S2 section 4.3.2 and S6 further show why visual collapse alone cannot establish a
single physical response at all temperatures when mechanisms have different temperature
dependence. Averaging replicate reference times solves neither shape nor amplitude issues.

**Recommendation:** retain absolute moduli and explicit vertical shifts; distinguish
observed-reference and model-extrapolated normalization. Quantify overlap over actual
shared windows, examine beta and relative-mode changes, and label an unvalidated
concatenation as shifted curves rather than a validated mastercurve.

### F6 — Medium: the spectrum algorithm is defensible but its attribution is too specific

**Code:** `core/spectrum.py:66–116`, `gui/components/ui_credits.py:56`, and Education.

The implementation solves a nonnegative, zero-order Tikhonov/Ridge problem with an
identity penalty on discrete modal weights. It contains no explicit derivative
smoothness penalty or quadrature conversion into density. That is a legitimate model,
but not automatically equivalent to another paper's implementation.

S1 PDF p3 identifies maximum curvature as its L-curve corner rule. This code instead
maximizes distance to the secant joining scan endpoints. The selected value can depend
on the scan range. Calling this Hansen's exact corner detection is unsupported.

The main Spectrum panel now labels discrete weights correctly, but Education and Credits
still describe a continuous H(tau) distribution. Peak positions, weighted geometric mean,
first moment, and a longest resolved time should also remain distinct quantities.

**Recommendation:** name the implemented algorithm precisely, update educational text,
plot the L-curve and selected point, and benchmark alpha/grid/window sensitivity against
a trusted reference implementation before claiming equivalence. Do not apply the paper's
limitations on its particular spectral peak heights as a universal statement that
discrete Maxwell weights cannot be integrated to estimate viscosity under valid assumptions.

### F7 — High when encountered: stress and storage modulus are accepted as relaxation modulus

**Code:** `io/parser.py:32` recognizes `stress`, `storage`, and `g_prime` as modulus columns.

S2 PDF p9 defines stress-relaxation modulus as stress divided by imposed strain in
the linear regime. Stress shares pressure units with modulus but is not numerically
the same quantity. Storage modulus is a frequency-dependent response, also not G(t).

At imposed shear strain 0.01, accepting stress as modulus scales the inferred modulus
and spectrum weights down by 100. Normalized relaxation curves could still look correct,
making the problem easy to miss. This is a dimensional/semantic finding from code, not
an assertion that the user's uploaded files contain this mistake.

**Recommendation:** require explicit measurement type; convert stress using recorded
strain, reject frequency-domain data in the relaxation parser, and distinguish shear
from tensile modulus. Record linear-regime verification, loading duration and instrument
limits rather than assuming them from the file extension or column names.

### F8 — Medium: coupled-model and Eyring labels require narrower physical claims

**Code:** `core/kinetics.py:14`, `fit_coupled_kinetics` docstring and Tg−50 rule;
`fit_eyring`; `gui/components/ui_education.py`; `core/auto_engine.py`.

S5 equation 11 supports an additive exchange-time picture: a scaled segmental time
plus an elementary exchange time. Its segmental component is calculated through
SC-ECNLE theory, not the app's freely fitted VFT term. The app is a phenomenological
Arrhenius-plus-VFT approximation inspired by that picture; it does not implement Lin
et al.'s theory. The fixed T0=Tg−50 K value, also clamped to the data range, is an app
assumption rather than a parameter derived from the inspected Lin equations.

The Eyring algebra has the expected sign/unit convention for tau interpreted as an
inverse rate with transmission coefficient one. S4 and S3 nevertheless qualify the
mapping between rheological tau and a molecular rate. Multiplying that mapping by an
unknown factor c shifts inferred entropy by −R ln(c); a factor 10 changes it by about
−19.14 J/(mol K). An apparent entropy is not a uniquely measured molecular entropy.

**Recommendation:** use apparent activation parameters, disclose the rate mapping and
transmission assumption, report sensitivity to fixed/free T0, and label the coupled
fit phenomenological. Mathematical model preference should not automatically identify
a vitrimer or an exchange mechanism. Near/below Tg exclusion is an analysis policy,
not proof that no relaxation process exists there.

### F9 — Medium: optimization success is not an identifiability or uncertainty result

**Code:** `core/analyzer.py` fitting and information criteria; kinetics covariance
discarding; automatic quality/explanation rules.

Conditional normalization makes the first fitted observation exactly one and shares
its measurement noise across all ratios. Independent equal-variance residual assumptions
are therefore approximate. Peak selection, removing negative noisy values, drift trimming,
and downsampling add selection and weighting effects. Stored local covariance is useful
but cannot alone address these effects, active bounds, or multimodal solutions.

For dual KWW, a zero-amplitude mode has an unidentifiable tau and beta regardless of
R². Ordering tau1<tau2 only fixes labels at one temperature; it does not establish
chemical mode continuity across temperatures. A mode can change identity when branches
cross, and a tiny-amplitude slow mode can control the app's selected kinetics value.

**Recommendation:** profile or bootstrap parameters, use multiple starts, flag modes
with weak amplitudes/out-of-window times, propagate fit uncertainty into temperature
regressions, and examine residuals on original samples. Require held-out or independently
measured evidence for mechanistic assignments. Do not equate the current heuristic
quality percentage with a probability that an interpretation is correct.

## What the current code gets right

- Conditional model normalization preserves the loading-time origin for ideal data.
- Arrhenius and Eyring slope/unit conversions are internally consistent for their stated
  mathematical models; the caveat is the physical interpretation of the fitted observable.
- Logaddexp improves stability without changing the intended additive equation.
- Replicates and reference choices are explicit; failed optimization is not presented
  as a successful fitted curve.
- Spectrum weights now reconstruct in input modulus units, and current primary labels
  state the discrete-weight convention.

These are meaningful improvements. The new findings concern model scope, observability,
and downstream interpretation, which ordinary ideal-recovery tests cannot establish.

## Recommended next scientific batch

1. Add plateau/finite-window diagnostics independent of inversion, plus baseline sensitivity.
2. Gate unresolved modes from kinetics; add equilibrium-offset candidates and identifiability tests.
3. Implement explicit characteristic/first-moment/viscosity outputs and revise Tv accordingly.
4. Restrict thermodynamic claims and enforce measurement-type metadata.
5. Reconcile TTS normalization; add overlap and shape diagnostics.
6. Align Education/Credits with actual equations and benchmark the inversion method.

Acceptance benchmarks should vary noise, acquisition start, sample spacing, observation
duration, equilibrium fraction, mode separation/amplitude, and temperature-dependent shape.
Include raw stress with known strain and a nondissociating material whose reference modulus
changes with acquisition delay. Compare with independent creep/SAOS or chemical measurements
where available. No new physical defaults should be adopted solely because they pass one
constructed example.
