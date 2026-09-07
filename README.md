# K Vitrimer Analysis

**Kinetic Analysis of Vitrimer Relaxation & Kinetics** - Professional stress relaxation analysis software for materials research.

## No-Code Launch (Windows)

**Easiest method:**
1) Install Python 3.11+ from https://www.python.org/downloads/windows/ (check "Add python.exe to PATH").
2) Download/unzip the release, then double-click `K_Vitrimer_Analysis.bat`.
3) Wait for dependencies to install (first run only), then your browser opens at `http://localhost:8501`.
4) Keep the terminal window open; press Ctrl+C to stop.

**Alternative (with virtual environment):**
Double-click `run_app.bat` to create a `.venv` and run in isolated environment.

For other platforms, run: `pip install -r requirements.txt; streamlit run can_relax/gui/app.py`

---

## 📊 Data Format & Unit Conventions

To ensure accurate physical interpretation (such as Arrhenius prefactors and mastercurve shifts), the software expects specific data formats and units.

### 1. File Format
Upload data as a single **Wide-Format CSV** or **XLSX** file. The first row must be the temperature headers, and each column pair underneath must be Time and Modulus.

| 120 | (blank) | 130 | (blank) | 140 | (blank) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Time** | **Modulus** | **Time** | **Modulus** | **Time** | **Modulus** |
| 0.01 | 1.50 | 0.01 | 1.45 | 0.01 | 1.30 |
| 0.05 | 1.45 | 0.05 | 1.30 | 0.05 | 1.10 |
| ... | ... | ... | ... | ... | ... |

Alternatively, use repeating triplets with headers `Temp_A,Time_A,Modulus_A`,
`Temp_B,Time_B,Modulus_B`, etc. Each temperature column must be constant within
its curve. Empty trailing rows are allowed; partially missing measurements are rejected.
Replicates at the same temperature remain separate curves with file-local identifiers.

### 2. Unit conventions

- Unlabelled values mean **Celsius, seconds, and MPa**.
- Labelled seconds/minutes and Pa/kPa/MPa are converted to seconds and MPa.
  Labels can occur in headers (e.g. `Time (min)`, `Modulus (Pa)`) or cells
  (e.g. `2 min`, `500000 Pa`). Conflicting or unsupported units are rejected.
- Temperature must be Celsius; Kelvin input is rejected rather than silently interpreted.
- Signed temperatures, including negative integers, are preserved.

### 3. Time origin, fitting, and interpretation

Times default to elapsed time since loading. For an instrument clock, set **Loading
 time origin (s)** to the clock reading at loading. The short-time cutoff applies to
elapsed time and does not reset this origin.

After trimming, curves are normalized by their **first retained measured modulus**,
called G0 in the existing tables/CSV format. This is a reference observation, not an
inferred zero-time plateau. Fits use `f(t) / f(t_reference)` so a cutoff does not
silently change the Maxwell/KWW equation. Physical parameter order is unchanged.
Van 't Hoff analysis uses these observed reference moduli; compare them cautiously
when acquisition starts or cutoffs differ between temperatures.

**Raw 1/e** is the interval from the first retained observation to an unambiguous
crossing of its modulus divided by e. Missing or repeated crossings are excluded
from raw kinetics. For truncated KWW data this interval is not intrinsic fitted tau.
Publication markers use the crossing's elapsed-time position; their tau annotation
shows the interval.

Spectrum outputs are **discrete modal weights**, with the same modulus units as
input: `G(t) = G_eq + sum(w_j * exp(-t/tau_j))`. They are not continuous density
per logarithmic bin. Changing the bin count changes individual weights. Tail
subtraction is an assumption about equilibrium, not proof that equilibrium was reached.
Reconstruction error is displayed, and amplitude scaling is restored after inversion.

Changing data or fitting settings clears previous analysis results. Re-run analysis;
changing curve selection or mastercurve reference invalidates derived results.
At a reference temperature with replicates, mastercurve shifting uses the arithmetic
mean of their fitted relaxation times by default. Select a specific **Reference
replicate** to anchor its shift factor to 1 instead. The resulting reference time,
method, and curve identifiers are displayed. Legends show identifiers only when
multiple visible curves share a temperature.

The Spectrum view displays an orange status badge when its weighted geometric
mean relaxation time exceeds 80% of the measurement endpoint for any curve.
This is a window-sensitivity heuristic, not proof of incomplete relaxation.
Download the provenance JSON alongside fit parameters to retain the data/configuration
hash, unit convention, reference observations, and preprocessing settings.

### 4. Validation and shared review

Run `python -m pytest -q` after installing `requirements-dev.txt`.
The shared review entry point is [shared_review/README.md](shared_review/README.md).
Synthetic and workflow tests support software verification; they do not replace
independent experimental validation or parameter-identifiability assessment.

---

**Note:** PyInstaller EXE builds are experimental due to Streamlit compatibility issues. For best results, use the BAT launchers above.


## How to Cite

If this software supports your research, please cite the version you used:

**Recommended citation (v1.0):**
```
Bui, V.K. (2025). K Vitrimer Analysis v1.0: Stress relaxation and kinetics software. CY Cergy Paris University. https://github.com/khoabui0311-dev/K-Vitrimer-Analysis
```

**BibTeX:**
```
@software{bui_k_vitrimer_analysis_v1_0,
	author  = {Bui, Vo Khoa},
	title   = {K Vitrimer Analysis v1.0: Stress relaxation and kinetics software},
	year    = {2025},
	url     = {https://github.com/khoabui0311-dev/K-Vitrimer-Analysis},
	version = {v1.0},
	note    = {Academic and research use license}
}
```

For commercial licensing, please contact khoabui0311@gmail.com.

### Optional long-time plateau and apparent activation energy

For Maxwell and Single_KWW, choose **Long-time plateau → Zero, Fit, or Fixed**.
Zero preserves the original model. Fit estimates the plateau jointly with tau
and beta; Fixed uses the supplied modulus in MPa. A fixed value must be below
each curve's first retained modulus. The model is
`G(t) = G_inf + (G_initial - G_inf) exp(-(t/tau)^beta)` (Maxwell: beta = 1).
Cutoffs preserve the loading time origin and predictions account for normalization
at the first retained observation.

Inspect the parameter table, fit flags and residuals before using tau in kinetics.
The fitted plateau describes the measurement window and does not establish
permanent crosslinks. The Arrhenius view reports **apparent Ea**, regression
standard error and the selected temperature range. Its uncertainty does not
include uncertainty in each fitted tau. Flagged curves remain selectable.
KWW beta is plotted against temperature, and dual KWW permits choosing the fast
or slow component. Download fit parameters, kinetics selection, Arrhenius results
and provenance to record the analysis. Further implementation details and known
advanced-analysis limitations are in `shared_review/PLATEAU_BATCH.md`.
