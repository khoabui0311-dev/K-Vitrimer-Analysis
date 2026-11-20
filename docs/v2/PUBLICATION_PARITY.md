# Publication tab v1 — feature parity contract for VitriFit 2.0

Current implementation:
- can_relax/gui/tabs/tab_pub_main.py
- can_relax/gui/components/ui_plotting.py (additional plotting workflow)
- can_relax/gui/exporting.py
- can_relax/gui/tabs/tab_comparison.py

**DO NOT replace, simplify or restyle the working v1 Publication tab before
capturing reference outputs and testing feature parity.** Retain in main branch.

## Presets and physical dimensions
- ACS/RSC single column 85 × 75 mm; double column 170 × 140 mm; custom cm dimensions.
- Global per-figure panel letter, position, family, font size, weight, style.
- Explicit RGB / CMYK color space.
- Matplotlib vector font settings (SVG text retained, PDF TrueType/Type42).
- Preserve the current color cycle unless the user explicitly selects a new palette.

## Figure types
1. Relaxation curves: G versus E choice; normalized and absolute modulus;
   linear/log time and modulus axes; time s/min/h; raw lines, markers or both;
   fitted overlays; raw 1/e threshold and tau* annotation; marker density and size.
2. Arrhenius kinetics: ln(tau) versus 1000/T, currently selected datasets,
   fit line, kinetic information and guarded Maxwell-equivalent Tv annotation.
3. Eyring figure: existing equations/controls/labels/legend behavior.
4. Observed-reference-modulus Van 't Hoff figure, clearly marked empirical.

## Per-figure controls that must remain
- Independent label and tick font family/size/weight/style.
- Tick mirror, minor/major tick style, line width, marker size.
- Custom axis limits and linear/log choices where supported.
- Legend show/hide, automatic/fixed/outside location, box, number of
  columns, font size.
- Per-panel letter coordinates and styles.
- Formatting must not change scientific fit parameters.

## Export parity
- Existing on-demand high-resolution TIFF (300, 600, 1200 DPI, default 1200)
  and JPEG (600 DPI); current RGB and CMYK support.
- Keep the existing image-size limit, correct physical DPI metadata, and error
  handling in can_relax/gui/exporting.py.
- Keep other currently available export controls in generic plotting/comparison
  modules, including PDF/SVG/PNG where supported.
- Export must be checked with golden-reference files and physical sizes.
- Exports must NOT silently substitute a format, resolution or color space.

## Improvements to add without removing features
- Named user presets and exact per-figure snapshots.
- Saved figure projects with sample/curve/analysis version references.
- Restore a prior figure, reuse layout on a new dataset, compare samples.
- Figure-template schema versioning and migration.
- Potential additional editable SVG/PDF export, implemented only after confirming
  it is compatible with current output quality.

## Verification
Capture visual references for all four figure types and compare labels,
ticks, legends, limits, panel lettering, font embedding and export bytes.
Audit date: 2026-11-20. No visual regression baselines captured yet.
