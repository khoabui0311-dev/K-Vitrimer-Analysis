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

*(Note: The parser is robust and will automatically clean "Pa", "MPa", "s", and string headers as long as the underlying data is numeric).*

### 2. Unit Conventions
The internal physics engine (Arrhenius, VFT, Mastercurve) relies on standard units. While the parser attempts to auto-detect and correct obvious deviations, for best results please ensure your data follows these conventions:

*   **Temperature**: **°C** (Celsius). The software internally converts to Kelvin (K) where required by physics models (e.g., Arrhenius 1000/T, Eyring).
*   **Time**: **Seconds (s)**. Relaxation times ($\tau$) extracted from the models will naturally be in seconds.
*   **Modulus**: **MPa** (Megapascals). While $G(t) / G_0$ normalization is used for fitting, absolute values in MPa are used for the continuous relaxation spectrum $H(\tau)$ and plateau modulus $G_p$.

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