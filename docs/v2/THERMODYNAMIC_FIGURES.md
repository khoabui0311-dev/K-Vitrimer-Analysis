# Eyring and empirical Van 't Hoff figures — VitriFit 2.0

## Current status

The browser Figure Studio can now select Eyring (v1 Figure 3) and observed-reference-modulus
Van 't Hoff (v1 Figure 4), save a figure project, reopen it, preview the saved SVG,
and export with the existing v1 serialization and DPI/colour-space constraints.

This is a feature-parity implementation **in progress**, not a claim of completed
visual equivalence with all original v1 Publication options. Keep the v1 tab
available as the reference until visual/typography comparison is complete.

## Scientific definitions — unchanged from v1

**Eyring:**
\`ln(tau * T_K) = ln(h / k_B) - DeltaS^‡ / R + DeltaH^‡ / (R*T_K)\`.
The x axis is \`1000/T_K\` in K^-1 and the y axis is \`ln(tau * T_K)\`.
The result is a fitted *apparent* enthalpy and entropy only if the measured
relaxation time is interpreted as proportional to an inverse rate. It does
**not** by itself identify exchange chemistry or establish a molecular mechanism.

**Empirical reference-modulus Van 't Hoff:**
\`G0(T_K) = A*T_K / (1 + exp(-DeltaH/(R*T_K) + DeltaS/R))\`.
The source is the measured reference modulus at the start of the selected
fitting interval, \`reference_modulus_mpa\` from the saved fit result. Legacy
saved analyses that predate that field use the first retained point of the
**pinned** preprocessing revision. Do not substitute long-time \`G∞\`.

This curve is labelled **empirical**. Evidence of network dissociation
thermodynamics requires independent equilibrium measurements. The apparent
temperature dependence of reference modulus may result from acquisition
delays, relaxation during instrument stabilization or other viscoelastic
effects.

## Data lineage and constraints

- Saved figure projects refer to analysis run IDs, and each run refers to
  a frozen preparation revision. Figure rendering does not silently track
  later per-curve edits.
- Eyring enforces a single relaxation-time definition across selected runs.
- Van 't Hoff rejects repeated analysis runs from the same measured curve
  to avoid pseudoreplicates.
- Eyring requires at least 2 distinct measured temperatures **per sample**.
- Van 't Hoff requires at least 4 distinct measured temperatures **per sample**.
- Cross-sample data are fit independently, with optional temperature windows
  keyed by sample ID. The displayed regression is limited to that sample's
  measured window. No model extrapolation fills absent experimental points.
- Publication Figure 3 uses the saved \`eyr_\` settings and panel key
  \`pl_3\`; Figure 4 uses \`vh_\` and \`pl_4\`.
- For single-sample figures the observed points use v1 steelblue and fitted
  lines are dashed red. Multi-sample figures use a consistent colour cycle.
- Uses the existing \`can_relax.core.kinetics.KineticsEngine\`, not a newly
  coded alternative for either equation.
- Uses the existing \`can_relax.gui.exporting.figure_bytes\` serializer.
  The default TIFF/ JPEG DPI choice remains unchanged.

## Qualification still required

- Side-by-side pixel/typographic comparison with all four original v1
  Publication plot types, at all journal size presets.
- Confirmation of local font availability and PDF Type42/SVG editable
  text behavior on clean Windows installations.
- Confirm saved figure projects retain independent per-figure styling across
  reopened workspaces and future schema migrations.
- Additional live-browser tests with user instrument measurements.
- Complete detailed adjustments for Figures 1 and 2; they are not fully
  migrated to the new UI.

Tests use synthetic datasets matching the existing equation definitions;
no private experimental readings are committed to the repository.
