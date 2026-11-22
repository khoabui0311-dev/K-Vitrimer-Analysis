# Scientific foundations audit — Phase 0

Status: **verified bibliography and implementation plan**, not a claim of
completed literature-to-code validation. Updated 2026-11-22.

## Verified primary references

1. Ricarte, R. G.; Shanbhag, S. A tutorial review of linear rheology for polymer chemists: basics and best practices for covalent adaptable networks. *Polymer Chemistry* **2024**, *15*, 815–846. https://doi.org/10.1039/D3PY01367G
   - Publisher: https://pubs.rsc.org/en/content/articlehtml/2024/py/d3py01367g
   - Open-access CC BY 3.0; publisher lists two supplementary XLSX files.
   - Scope: stress relaxation, creep/recovery, SAOS, relaxation spectra,
     time–temperature superposition, experimental artifacts, CAN best practices.
   - First benchmark candidate: reproduce supplementary spreadsheet analyses
     with documented data transformations, tolerances and provenance.
2. Rubinstein, M.; Colby, R. H. *Polymer Physics*; Oxford University Press, 2003.
   https://doi.org/10.1093/oso/9780198520597.001.0001
   - Reference for polymer dynamics, entanglements, network elasticity.
   - Bibliography only; do not ingest copyrighted chapters without authorization.
3. *How to Characterize Covalent Adaptable Networks: A User Guide* (2025).
   https://doi.org/10.1021/acspolymersau.5c00004
   - Verify individual experimental characterization recommendations before
     turning them into software requirements.

## Additional books to catalog and check against publisher records

- Ferry, J. D., *Viscoelastic Properties of Polymers*, 3rd ed.
- Doi, M.; Edwards, S. F., *The Theory of Polymer Dynamics*.
- de Gennes, P.-G., *Scaling Concepts in Polymer Physics*.
- Macosko, C. W., *Rheology: Principles, Measurements, and Applications*.
- Tschoegl, N. W., *The Phenomenological Theory of Linear Viscoelastic Behavior*.
- Ward, I. M.; Sweeney, J., *Mechanical Properties of Solid Polymers*.
- Flory, P. J., *Principles of Polymer Chemistry*.
- Treloar, L. R. G., *The Physics of Rubber Elasticity*.
- Strobl, G., *The Physics of Polymers*.
- Larson, R. G., *The Structure and Rheology of Complex Fluids*.

## Literature-to-code validation matrix (to populate)

| Technique | Reference anchor | Verification targets | Status |
| --- | --- | --- | --- |
| Stress relaxation | Ricarte–Shanbhag; Ferry | Maxwell/KWW, tau definitions, residuals, plateaus | pending |
| Frequency sweep | Ricarte–Shanbhag; Macosko | G', G'', tan(delta), Hz/rad/s, crossover | pending |
| LVR/amplitude sweep | Ricarte–Shanbhag; Macosko | plateau selection, strain-mode matching, temperature dependence | pending |
| TTS/spectra | Ricarte–Shanbhag supplementary; Ferry | shifts, overlap, spectral inversion and regularization | pending |
| Network elasticity | Rubinstein–Colby; Treloar | plateau modulus, assumptions for nu_e | pending |
| DMA | Ferry; Ward–Sweeney | E', E'', Talpha definitions, frequency dependence | pending |
| DSC | appropriate thermal-analysis standards and reviews (to source) | Tg onset/midpoint/endset, DeltaCp, baseline, cycles | pending |
| Tensile | Ward–Sweeney | engineering vs true strain, modulus range, yield | pending |
| CAN mechanisms | CAN characterization reviews | limits of inference from macroscopic rheology | pending |

## Phase 0 gates

- Inventory existing papers in repository and user-authorized project database
  before claiming full coverage.
- Check bibliographic metadata against publisher/DOI records.
- Cite the exact reference and equation/section for each method.
- Implement independent synthetic and published-data benchmarks with explicit
  acceptance thresholds.
- Document limitations: time-window censoring, nonmonotonic LVR(T), frequency
  dependence, heterogeneous/serially correlated errors, non-unique fits,
  and invalid inference of molecular mechanisms from rheology alone.
- Keep this library and benchmark data legally redistributable.
- No claims of scientific validation until tests are run and recorded.
