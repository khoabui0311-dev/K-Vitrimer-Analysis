# Rheology extensions: amplitude sweeps, LVR and frequency sweeps

Status: **scientific/product specification, not implemented**.
Integrate under Sample Profile -> Rheology. Preserve raw instrument files.

## Amplitude/strain sweep (LVR)

Import strain or stress amplitude, frequency (Hz or rad/s), temperature,
G', G'', tan(delta), torque/force, instrument geometry, normal force,
equilibration time, acquisition direction and repeat number. Distinguish
shear strain gamma from tensile strain epsilon; do not silently interchange
G' and E'. Record frequency and geometry for every sweep.

Compute a candidate initial plateau from a user-reviewable strain range.
Flag insufficient plateau points, noise floor, instrument limits, slippage,
nonmonotonicity, damage, and drift. Define configurable LVR departure
threshold (e.g. 5% deviation of G' from the low-amplitude reference);
this is a convention, not a universal physical boundary. Record threshold,
baseline selection, uncertainty and all user overrides. Optionally assess
G'' and tan(delta) changes.

Store LVR as a function of temperature **and frequency** and of the
specific specimen/geometry, not just a single scalar per sample.

## Temperature validation

If a relaxation or oscillatory experiment uses a specified strain, compare
it to LVR measured under compatible conditions. States:
- `verified_oscillatory_lvr`: matched temperature, frequency, strain mode,
  geometry and specimen/material state, with sufficient data quality.
- `outside_measured_lvr`: matched conditions and amplitude above boundary.
- `not_directly_verified`: missing/incompatible evidence, including
  unmeasured intermediate temperatures.

Two endpoint sweeps at 40 C and 180 C do **not** prove that the same
amplitude is in the LVR for all intermediate temperatures; boundaries can
be nonmonotonic near Tg, Talpha, Tni, physical transitions and exchange.
Interpolation can be displayed as exploratory only, with an explicit
unverified label. Step-strain stress relaxation is not identical to
oscillatory amplitude sweeps; report oscillatory LVR as supporting
evidence, not proof of linear step-strain response.

## Frequency sweep

Import angular frequency omega (rad/s) or f (Hz), convert using
omega=2*pi*f, temperature, strain/stress amplitude, G', G'', tan(delta),
complex viscosity, geometry and metadata. Preserve original units.
Compute tan(delta)=G''/G' only where physically/numerically valid.
Compute |eta*|=sqrt(G'^2+G''^2)/omega only for omega>0.
Detect G'=G'' crossover only within the observed domain; never
extrapolate an unseen crossover without explicit model and warning.

Provide log-frequency and log-modulus plots, temperature overlays,
replicate comparison, and publication figure presets. Cross-check
frequency-sweep strain against compatible LVR evidence.

## TTS and time-domain comparison

Offer horizontal/vertical shifting with user-reviewed reference
temperature, shift factors, overlap metrics, provenance and
thermorheological-simplicity warnings. CANs, LCEs and multiphase
systems may violate simple TTS. Compare frequency-domain moduli to
time-domain relaxation only with an explicitly defined linear
viscoelastic transform, consistent units, strain mode, and documented
regularization; never equate E(t) with G(t) without constitutive
assumptions.

## Required tests

1. Known-plateau synthetic strain sweep with 5% threshold and noise.
2. No plateau / noisy low-strain data -> indeterminate, not false LVR.
3. 40 C and 180 C pass but 100 C missing -> not directly verified.
4. Matched temperature but different oscillatory frequency -> not directly verified.
5. Step-strain relaxation -> advisory oscillatory LVR only.
6. Hz/rad/s conversion, Pa/kPa/MPa conversion and invalid zero omega.
7. Frequency-domain crossover interpolation only within observed bracket.
8. Round-trip raw files, preprocessing metadata, publication figure style.
