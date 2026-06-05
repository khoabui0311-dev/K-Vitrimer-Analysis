# CAN-Relax Supreme - Project Overview

## 📋 Project Summary
**CAN-Relax Supreme** is a scientific stress relaxation analysis software designed to analyze viscoelastic material behavior through relaxation curves. It combines physics-based modeling, machine learning predictions, and virtual experimentation to characterize material properties.

---

## 🏗️ Project Structure

### Root Directory
```
can_relax/                 # Main package
├── core/                  # Physics & mathematics core
├── gui/                   # Streamlit web interface
├── io/                    # File I/O & parsing
├── ml_engine/             # Machine learning models
├── sim/                   # Virtual laboratory simulator
├── data/                  # Data storage (empty)
├── __init__.py

tests/                     # Unit tests
examples/                  # Example data
models/                    # Trained ML models
publication_figures/       # Generated figures
.venv/                     # Python virtual environment
```

---

## 🔧 Core Modules

### 1. **can_relax/core** - Physics Engine
Core functionality for relaxation analysis:

#### `models.py`
- **Maxwell Model**: Single exponential decay `G(t) = G₀ * exp(-t/τ)`
- **SingleKWW**: Kohlrausch-Williams-Watts (stretched exponential) `G(t) = G₀ * exp(-(t/τ)^β)`
- **DualKWW**: Two-component KWW model for complex materials
- Each model includes:
  - `func()` - Mathematical function
  - `get_initial_guess()` - Parameter estimation
  - `get_bounds()` - Physical bounds for fitting

#### `analyzer.py` - CurveAnalyzer
Main orchestrator for fitting relaxation curves:
- `fit_one_temp()` - Fits all models to data at a single temperature
- Includes quality checking and metric calculation (R², AIC)
- Physics barrier: Skips fitting below glass transition (Tg)
- Handles data quality validation

#### `processing.py` - DataProcessor
Signal processing for experimental data:
- `trim_curve()` - Cleans raw data (removes NaNs, outliers)
- Smoothing via Savitzky-Golay filter
- Peak detection and artifact removal
- Drift detection to find true relaxation endpoint

#### `kinetics.py` - KineticsEngine
Temperature-dependent analysis:
- **Arrhenius fitting**: `ln(τ) = ln(τ₀) + Ea/(R*T)`
- **VFT (Vogel-Fulcher-Tammann) fitting**: Non-Arrhenius behavior
- Calculates activation energy (Ea) and temperature dependence
- Supports spectral analysis of relaxation mechanisms

#### `spectrum.py` - SpectrumAnalyzer
Continuous relaxation time spectrum analysis:
- Computes `H(τ)` (distribution of relaxation times)
- Uses Tikhonov regularization (Ridge regression) for inverse problem
- Outputs weighted average relaxation time
- Handles polydisperse materials

#### `auto_engine.py` - AutoEngine
Automated analysis and quality assessment:
- Signal quality metrics
- Automatic model selection recommendation
- Data validation checks

---

### 2. **can_relax/io** - File I/O

#### `parser.py` - parse_wide_format_data()
**Robust CSV/Excel parsing** with multiple fallbacks:
- Handles wide-format data: Time (Col 1) | Temp1 | Temp2 | Temp3...
- Handles block format: Temp | Time | Modulus | Temp | Time | Modulus...
- Multi-encoding support (UTF-8, Latin-1)
- Automatic column detection via regex
- Returns: `{temperature_float: DataFrame(Time, Modulus)}`

#### `report.py`
Export functionality (stub for PDF/Excel generation)

---

### 3. **can_relax/gui** - Streamlit Interface

#### `app.py` - Main Application
Comprehensive web interface with 5 tabs:

1. **🚀 Analysis Tab**
   - File upload (CSV/XLSX)
   - Material metadata input (class, type, composition)
   - Chemistry tags (Transesterification, Disulfide, Imine, etc.)
   - Fitting model selection (Maxwell, Single_KWW, Dual_KWW)
   - Live progress bar with results visualization
   - Interactive plots (Plotly)

2. **🗄️ Database Manager Tab**
   - Fetch experiment history from SQLite
   - Filter/search results
   - Delete/edit verdicts
   - Export to CSV

3. **🧪 Virtual Lab Tab**
   - Simulate synthetic curves with known parameters
   - Adjust Ea, Tv, Tg, G_plateau, beta
   - Compare with experimental data
   - Parameter sweep functionality

4. **🧠 AI Scientist Tab**
   - ML predictor for material classification
   - Feature extraction from curves
   - Model training on historical data
   - Automated recommendations

5. **📝 Publish Tab**
   - Generate publication figures
   - Statistical summaries
   - Kinetics analysis (Arrhenius/VFT fitting)

#### Database Schema (SQLite)
```sql
CREATE TABLE experiments (
  id INTEGER PRIMARY KEY,
  filename TEXT,
  material_class TEXT,
  material_type TEXT,
  composition TEXT,
  chemistry_tags TEXT,
  temperature FLOAT,
  best_model TEXT,
  r2 FLOAT,
  tau FLOAT,
  beta FLOAT,
  verdict TEXT
)
```

---

### 4. **can_relax/ml_engine** - Machine Learning

#### `classifier.py` - MLPredictor
Random Forest classifier for material behavior prediction:
- **Feature extraction** (9 features):
  - Initial modulus (f₀)
  - Final modulus (fend)
  - Drop (decay amplitude)
  - Time to 50% decay (t₅₀)
  - Derivative stats (mean, min, max)
  - Curvature (2nd derivative)
  - Tail noise (signal quality)

- **Model operations**:
  - `extract_features()` - Compute 9D feature vector
  - `build_dataset()` - Prepare training data
  - `train()` - Train RandomForest with cross-validation
  - `predict()` - Classify new curves
  - `save_model()` / `load_model()` - Persistence

---

### 5. **can_relax/sim** - Virtual Simulator

#### `simulator.py` - MaterialSimulator
Synthetic curve generation for testing:
- Supports all three models (Maxwell, Single_KWW, Dual_KWW)
- Physics-based parameter: Viscosity-defined relaxation time
- **Key physics**:
  - Uses Arrhenius temperature dependence: `τ(T) = τ(Tv) * exp(Ea/R * (1/T - 1/Tv))`
  - `Tv`: Reference temperature (Volkov temperature)
  - `Tg`: Glass transition (freezes below)
  - `G_plateau`: Rubbery modulus
  - `Ea`: Activation energy

- Generates synthetic time-relaxation curves for validation

---

## 📦 Dependencies
```
numpy              # Numerical arrays
pandas             # Data manipulation
scipy              # Optimization, signal processing
matplotlib         # Static plots
plotly             # Interactive visualization
streamlit          # Web framework
openpyxl           # Excel I/O
scikit-learn       # ML models & utilities
sqlalchemy         # Database ORM
```

---

## 🚀 Running the Application

### Start the Streamlit App
```bash
cd c:\Users\khoab.000\OneDrive\CAN_Relax_Project
python -m streamlit run can_relax/gui/app.py
```

App will be available at: `http://localhost:8501`

### Workflow
1. **Upload file** (CSV/XLSX with relaxation curves)
2. **Enter material info** (class, type, composition)
3. **Select chemistry tags** (mechanism type)
4. **Configure physics** (Tg, G', model choice)
5. **Run Analysis** → Fits curves at each temperature
6. **View results** → R², fitted parameters (τ, β)
7. **Save to database** → Experiment stored in SQLite
8. **Export** → Download results as CSV

---

## 🔬 Physics Background

### Stress Relaxation
When a material is subjected to a constant strain, the stress decays over time:
$$G(t) = \frac{\sigma(t)}{\varepsilon_0}$$

### Relaxation Models
**Maxwell**: `G(t) = G₀ exp(-t/τ)`
- Single timescale τ
- Good for simple polymers

**KWW (Stretched Exponential)**: `G(t) = G₀ exp(-(t/τ)^β)`
- β ∈ (0,1): Broader distribution
- β=1: Recovers Maxwell
- Captures non-Fickian behavior

**Dual KWW**: Superposition of two KWW processes
- Fast relaxation (short τ₁)
- Slow relaxation (long τ₂)
- Better for vitrimers, block copolymers

### Temperature Dependence
**Arrhenius**: `τ(T) = τ₀ exp(Ea / (R*T))`
- Linear in 1/T plot
- Used at high T above Tg

**VFT (Vogel-Fulcher-Tammann)**: `τ(T) = τ₀ + B/(T - T₀)`
- Curved behavior near Tg
- Better for glassy materials

---

## 🎯 Key Features

✅ **Multi-format parsing** - CSV, XLSX with auto-detection  
✅ **Physics constraints** - Respects Tg, uses proper bounds  
✅ **Model comparison** - Automatic R² ranking  
✅ **Temperature kinetics** - Arrhenius & VFT fitting  
✅ **Spectrum analysis** - H(τ) distribution  
✅ **ML predictions** - Material classification  
✅ **Virtual lab** - Synthetic curve generation  
✅ **Database persistence** - SQLite storage  
✅ **Interactive UI** - Plotly + Streamlit  

---

## 📝 File Formats

### Input Format (CSV/XLSX)
**Wide Format**:
```
Time      | 140°C  | 180°C  | 220°C
0.1       | 1.2    | 1.5    | 1.8
0.5       | 1.1    | 1.3    | 1.6
1.0       | 1.0    | 1.2    | 1.4
...
```

**Block Format**:
```
Temperature | Step time | Modulus | Temperature | Step time | Modulus
50          | 0.1       | 1.2     | 90          | 0.1       | 1.5
50          | 0.5       | 1.1     | 90          | 0.5       | 1.3
...
```

---

## 🐛 Common Issues & Fixes

| Issue | Solution |
|-------|----------|
| "no such column: chemistry_tags" | Delete `vitrimer_app_v21.db` (auto-recreates) |
| "ModuleNotFoundError: sklearn" | Run `pip install scikit-learn` |
| "Failed to parse VU2.xlsx: UploadedFile" | Use `BytesIO()` wrapper for file objects |
| File not found parsing | Ensure columns contain "Temperature", "Time", "Modulus" |

---

## 📊 Example Analysis Workflow

1. **Upload** `VU2.xlsx` with data at 140°C, 180°C, 220°C
2. **Material**: Class=Vitrimer, Type=Epoxy, Composition=Bisphenol A
3. **Chemistry**: Select "Transesterification"
4. **Physics**: Tg=80°C, G'=1.0 MPa
5. **Model**: Single_KWW
6. **Results**:
   - 140°C: τ=5.2s, β=0.92, R²=0.998
   - 180°C: τ=1.1s, β=0.91, R²=0.997
   - 220°C: τ=0.18s, β=0.90, R²=0.996
7. **Kinetics**: Ea = 85 kJ/mol (from Arrhenius fit)

---

## 🔮 Future Enhancements

- [ ] Bayesian parameter uncertainty
- [ ] Automatic peak fitting for frequency response
- [ ] Export to ANSYS/Abaqus material cards
- [ ] Batch processing of 100+ files
- [ ] Real-time DMA integration
- [ ] Advanced chemistries database

---

Generated: December 7, 2025
