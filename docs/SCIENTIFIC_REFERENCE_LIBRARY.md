# Scientific reference library: CAN rheology and polymer physics

Curated on 2026-11-22. This is a bibliographic index and validation roadmap,
**not** a claim that full papers or book chapters have been ingested or tested.
Respect publishers' licenses: store citations, DOI links, original notes and
permitted supplementary data; do not redistribute copyrighted books or PDFs.

## Priority A: Ralm G. Ricarte and CAN rheology

1. Ricarte, R. G.; Shanbhag, S. **A tutorial review of linear rheology for polymer chemists: basics and best practices for covalent adaptable networks.** *Polymer Chemistry* **2024**, *15*, 815–846. DOI: [10.1039/D3PY01367G](https://doi.org/10.1039/D3PY01367G).
   - Audit: stress relaxation, creep, SAOS, relaxation spectra, TTS, rheological artifacts.
   - Validation candidate: open-access supplementary spreadsheets for TTS and spectra (check licenses, units and sheet formulas before importing).
2. Ricarte, R. G. **Network Topology and Linear Viscoelasticity of Vitrimers—A Polymer Physics Perspective.** *Macromolecules* **2026**, *59*, 6593–6619. DOI: [10.1021/acs.macromol.6c00582](https://doi.org/10.1021/acs.macromol.6c00582).
   - Audit: topology defects, plateau modulus, segmental vs exchange-driven relaxation, mechanism inference.
3. Hayashi, M.; Ricarte, R. G. **Towards the next development of vitrimers: Recent key topics for the practical application and understanding of the fundamental physics.** *Progress in Polymer Science* **2025**, *170*, 102026. DOI: [10.1016/j.progpolymsci.2025.102026](https://doi.org/10.1016/j.progpolymsci.2025.102026).
   - Audit: relaxation-time definitions, topology freezing temperature, processing–mechanics trade-offs.

## Priority A: recent CAN reviews and characterization

4. Berne, D.; et al. **How to Characterize Covalent Adaptable Networks: A User Guide.** *ACS Polymers Au* **2025**, *5*, 214–240. DOI: [10.1021/acspolymersau.5c00004](https://doi.org/10.1021/acspolymersau.5c00004).
   - Audit: specimen preparation, measurement validity, time window, appropriate model selection.
5. **Covalent Adaptable Networks: Reprocessable Cross-Linked Polymers.** *Chemical Reviews* **2026**, *126*, 1829–1948. DOI: [10.1021/acs.chemrev.4c00994](https://doi.org/10.1021/acs.chemrev.4c00994).
   - Audit: CAN terminology, associative vs dissociative mechanisms, characterization.
6. Karatrantos, A. V.; Couture, O.; Hesse, C.; Schmidt, D. F. **Molecular Simulation of Covalent Adaptable Networks and Vitrimers: A Review.** *Polymers* **2024**, *16*, 1373. DOI: [10.3390/polym16101373](https://doi.org/10.3390/polym16101373).
   - Audit: distinctions between molecular exchange, macroscopic stress relaxation and simulated rheology.

## Polymer physics and rheology books (bibliographic references only)

- Ferry, J. D. *Viscoelastic Properties of Polymers*, 3rd ed.; Wiley, 1980.
  - Linear viscoelasticity, relaxation/retardation spectra, time–temperature superposition.
- Rubinstein, M.; Colby, R. H. *Polymer Physics*; Oxford University Press, 2003.
  - Chain dynamics, entanglement, networks, rubber elasticity, glass transition.
- Doi, M.; Edwards, S. F. *The Theory of Polymer Dynamics*; Oxford University Press, 1986.
  - Rouse/reptation theory and the interpretation of polymer relaxation.
- de Gennes, P.-G. *Scaling Concepts in Polymer Physics*; Cornell University Press, 1979.
  - Scaling concepts, polymer conformations and dynamics.
- Macosko, C. W. *Rheology: Principles, Measurements, and Applications*; Wiley-VCH, 1994.
  - Rheometry, constitutive models, experimental artifacts.
- Tschoegl, N. W. *The Phenomenological Theory of Linear Viscoelastic Behavior: An Introduction*; Springer, 1989.
  - Constitutive equations, interconversion, relaxation spectra.
- Ward, I. M.; Sweeney, J. *Mechanical Properties of Solid Polymers*, 3rd ed.; Wiley, 2012.
  - Solid polymer mechanics, yielding, tensile and dynamic mechanical response.

## Validation traceability requirements

For each implemented method, add a machine-readable or tabular record:
`method_id | literature_reference | exact equation | parameter_definition |
assumptions | input_units | validity_window | independent_benchmark |
acceptance_tolerance | limitations | test_path | status`.

Initial high-priority audits:
1. Distinguish intrinsic KWW tau from observed first-retained-point 1/e crossing, especially with nonzero equilibrium plateau.
2. Check the Two-Maxwell arm ordering and align point estimates with bootstrap intervals.
3. Distinguish model-predicted crossing within the acquisition window from an empirical observed crossing.
4. Validate AICc against independent, identically preprocessed data and realistic residual structure.
5. Check whether Arrhenius/VFT fits justify mechanistic interpretations and whether Tv is identifiable.
6. Compare TTS and spectrum inversion to Ricarte–Shanbhag supplementary spreadsheets, after confirming permission and formula definitions.
7. Audit DMA tensile-vs-shear units and the scope of linear viscoelastic assumptions.

## Existing project materials

Cross-reference `docs/BENCHMARK_PROTOCOL.md` and existing repository
references. Any user-provided PDFs or internal database files must be
individually inventoried and reviewed before claiming they are included.
