# Sample-centric database and multimodal experiment profile

Status: **product specification, not yet implemented**. The sample cards and
tabs in the design proposal are illustrative and must not be treated as
imported measurements.

## Core interaction

Opening Database shows a searchable sample list. Clicking a sample opens a
single Sample Profile with Overview, DMA, DSC, Rheology, Tensile, Figures,
Comparison and Notes. Missing experiments show an empty state and Upload
action, never an invented value. A sample can have multiple independent
runs, repeats, temperatures, frequencies and acquisition dates.

## Data model

- **Sample**: stable UUID, user-editable sample ID, formulation, chemistry,
  batch, preparation, curing/annealing history, operator, free-form notes.
- **Specimen**: UUID, parent sample UUID, dimensions, orientation, conditioning,
  replicate label; distinguish separately cut specimens from the same batch.
- **Measurement**: UUID, specimen UUID, technique enum (DMA/DSC/Rheology/Tensile),
  method, instrument, date, raw-file SHA256, immutable original file, unit
  definitions, original metadata, import warnings.
- **Run**: UUID, measurement UUID, cycle/segment, frequency, temperature,
  strain, geometry, heating rate and other technique-specific conditions.
- **Analysis**: UUID, run UUID(s), algorithm version, preprocessing and
  selection history, parameters, fit statistics, uncertainty, quality flags,
  provenance and derived outputs.
- **Figure**: UUID, analysis UUID(s), export format, rendering configuration,
  v1-compatible publication presets.

Do not use sample name as a unique key: names may change or collide.
Maintain a migration path from existing project records and preserve raw data.

## Technique-specific summaries

- **DMA**: E', E'', tan(delta), temperature/frequency, Talpha by E'' peak
  and tan(delta) peak as separate definitions, peak width, candidate
  rubbery plateau and its temperature/frequency, optional *conditional*
  apparent effective network-chain density. Never claim homogeneous
  network or chemical crosslink density from DMA alone.
- **DSC**: Tg onset/midpoint/endset, DeltaCp where reliable, thermal cycles,
  heating rate, crystallization/melting and possible liquid-crystal transition.
  Require explicit baseline selection and preserve instrument sign convention.
- **Rheology**: relaxation, creep, frequency/temperature sweeps, stress
  versus modulus, strain regime, sample geometry, Maxwell/KWW fits,
  kinetics, time-window/uncertainty flags and TTS validity.
- **Tensile**: engineering and true stress/strain (true measures only where
  geometrically justified), modulus and fit region, yield, maximum stress,
  strain at break, replicate aggregation and uncertainty.

## User workflow

1. Search/open sample; display provenance-aware overview of existing runs.
2. Upload files to an existing sample or create a sample; optionally
   identify specimen and replicate. Never silently join similarly named samples.
3. Parse/preview instrument formats, units and experimental conditions.
4. Preserve originals; offer per-curve trim and undo/redo with audit trail.
5. Analyze each run, showing method-specific warnings and manual overrides.
6. Compare across techniques and samples without conflating test conditions.
7. Export publication figures, machine-readable results and complete
   provenance manifest.

## Release acceptance criteria

- A sample with all four techniques opens and navigates without losing
  analysis state.
- Multiple specimens/runs remain distinct; adding new data never overwrites
  old raw files or prior analysis.
- Missing data remain visibly missing; sample overview never fabricates Tg,
  Talpha, modulus, plateau or tensile metrics.
- Same-temperature comparisons verify units and experimental settings.
- Imported v1 project data remain accessible and publication figure
  rendering matches v1 golden-image tolerances.
- End-to-end browser test covers create sample -> upload each technique ->
  inspect curves -> analyze -> compare -> export -> reopen.
