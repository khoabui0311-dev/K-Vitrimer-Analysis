# VitriFit 2.0

Stress relaxation fitting and kinetics analysis for materials research.
This development branch contains **2.0.0-dev.2**, the new workspace preview.
The published Windows candidate remains **2.0.0-rc.1** and does not contain
these new workspace features. Previously named K Vitrimer Analysis.
See the [quick-start guide](docs/QUICK_START.md) and
[candidate release notes](docs/RELEASE_NOTES_2.0.md).

## New workspace preview

- Import data and choose the model in the main workspace, with dataset and fit-review summaries.
- Save a `.vfit` project containing the original CSV/XLSX, model settings, curve timing,
  point exclusions and selected curves. Reopening restores the recipe and recalculates
  an analysis that had been run. Kinetics selections, mastercurves and plot styling
  must be reviewed again; export those results separately.
- Compare Maxwell, single KWW and two-Maxwell for one curve using the same retained
  observations and plateau policy. Inspect fit overlays, residuals, AICc/BIC and warnings,
  then explicitly choose a model to refit all temperatures.

Run the preview from this branch using the source instructions below.
See [the workspace guide](docs/WORKSPACE_PREVIEW.md) for a complete walkthrough.

## Installable offline application (Windows)

Download the installer from the repository's
[Releases](https://github.com/khoabui0311-dev/K-Vitrimer-Analysis/releases) when published,
or use a supplied candidate build. Source ZIP downloads do not include installers.
Run `VitriFit_Setup_2.0.0-rc.1_x64.exe` to install the desktop edition.
Launch **VitriFit** from the desktop or Start menu.
The installer includes Python and the analysis libraries; no Python installation
or internet connection is needed to use it. Windows 10/11 x64 and a web browser
are required.

The small launcher opens the interface in your browser at a private localhost
address. Keep the launcher open while working; **Quit** stops its local server.
Uploaded files and calculations stay on your computer. Save downloads before
quitting, because analysis sessions are held in memory. Citation links still
require internet access when clicked.

Uninstall through Windows **Settings > Apps**. See [desktop/README.md](desktop/README.md)
for build instructions, package verification, and distribution limitations.

## Launch from source (Windows)

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

### 4. Two-Maxwell (Prony) fitting

For a two-term Prony series, select **Physics & Fitting > Model > Two-Maxwell (Prony)**,
choose a zero, fixed, or fitted long-time plateau, and click **Run Analysis**.
The model is `G(t) = G_inf + G1 exp(-t/tau1) + G2 exp(-t/tau2)`, with
mode 1 fast and mode 2 slow. **Download Fit Parameters CSV** includes both
times in seconds, both loading-time moduli in MPa, and each arm's fraction of
the relaxing modulus (excluding the plateau). Loading-time moduli are
extrapolations when the first measurement is later than zero. Use **Fitted
component** to choose the time used for fitted kinetics and mastercurve shifts.
Similar times or a weak arm can fit the curve well without resolving two processes.

### 5. Validation and shared review

Run `python -m pytest -q` after installing `requirements-dev.txt`.
The shared review entry point is [shared_review/README.md](shared_review/README.md).
Synthetic and workflow tests support software verification; they do not replace
independent experimental validation or parameter-identifiability assessment.

---

The BAT launchers install dependencies from the internet on first use. Use the
desktop installer for computers that need to remain offline.


## How to Cite

If this software supports your research, please cite the version you used:

**Recommended citation (current candidate):**
```
Bui, V.K. (2026). VitriFit 2.0.0-rc.1: Stress relaxation and kinetics analysis [Computer software]. https://github.com/khoabui0311-dev/K-Vitrimer-Analysis
```

**BibTeX:**
```
@software{bui_vitrifit_2_rc1,
	author  = {Bui, Vo Khoa},
	title   = {VitriFit: Stress relaxation and kinetics analysis},
	year    = {2026},
	url     = {https://github.com/khoabui0311-dev/K-Vitrimer-Analysis},
	version = {2.0.0-rc.1},
	note    = {Academic and research use license}
}
```

For commercial licensing, please contact khoabui0311@gmail.com.
Machine-readable citation metadata is in [CITATION.cff](CITATION.cff).

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

## September 2026 project audit

The current audit, reproducible checks and remaining validation gaps are in
[PROJECT_AUDIT.md](shared_review/PROJECT_AUDIT.md). Earlier review reports describe
historical versions and should be read with their dates in mind.

- Input columns must contain time-domain relaxation modulus. Stress, storage/loss
  modulus and frequency-labelled columns are rejected. Convert raw stress using
  the known imposed strain before importing. Legacy XLS must be converted to XLSX.
- Raw 1/e uses all retained observations before fitting downsampling, so short
  recrossings cannot disappear through downsampling. Automatic peak/drift trimming
  and duplicate-time averaging still occur first.
- TTS offers observed-reference, model-extrapolated zero-time and absolute-modulus
  conventions. The selected dual-KWW component also controls horizontal shifts.
  These are shifted curves; overlap and shape compatibility require assessment.
- Tv in publication/comparison/simulation is a **Maxwell-equivalent threshold**
  based on characteristic tau and the supplied modulus. It is not a KWW integral
  viscosity or a measured topology transition. Nonphysical roots are unavailable.
- Publication exports are prepared on request. TIFF and JPEG are rendered at their
  actual requested resolutions (TIFF defaults to 1200 DPI; JPEG uses 600 DPI).
  Raster exports over 40 megapixels are rejected
  with guidance to reduce dimensions or DPI. CMYK supports JPEG, TIFF and raster PDF;
  no printer-specific ICC profile is applied.
- Historical migration scripts in `archive/legacy_scripts/` are disabled, and the old publication import routes
  to the maintained implementation. They should not be used to update this version.

Install `requirements-audit.txt` to run the optional static checks. The added CI
workflow targets Windows/Linux and Python 3.11/3.13; those CI jobs must run before
claiming support for every combination. The locally tested environment is recorded
in `shared_review/audit_evidence/environment.json`.
