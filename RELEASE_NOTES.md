# K Vitrimer Analysis v1.0 - PUBLICATION RELEASE NOTES

**Release Date**: December 7, 2025  
**Version**: 1.0 - Professional Edition  
**Status**: ✅ READY FOR PUBLICATION

---

## 🎯 What is K Vitrimer Analysis?

A comprehensive **kinetic analysis software** for vitrimer researchers and materials scientists. Analyze stress relaxation, temperature kinetics, and vitrimer exchange through mathematical modeling, parameter extraction, and publication-ready figure generation.

**Perfect for:**
- MSc & PhD vitrimer research
- Vitrimer development & screening
- Exchange kinetics characterization
- Arrhenius & VFT analysis
- Material relaxation studies

---

## ✨ Key Features

### 📊 **Analysis Tab**
- Import CSV/XLSX relaxation data
- Automatic model fitting (Maxwell, KWW, Dual-KWW)
- Temperature-dependent kinetics (Arrhenius/VFT)
- Outlier rejection with Include/Exclude editor
- Time-Temperature Superposition mastercurves
- Relaxation time spectrum analysis

### 🧪 **Virtual Lab Tab**
- Synthetic curve generation
- Three operation modes (Chemist, Engineering, Target)
- Parameter sensitivity exploration
- Recovered properties calculation
- Export to PNG/PDF/SVG with full control

### 📝 **Publish Tab**
- Publication-ready figure generation
- Normalized curves (G(t)/G₀)
- Arrhenius plots with Tv extrapolation
- R² metrics displayed
- Customizable DPI, format, dimensions
- Only uses approved data points

### 📚 **Education Tab** (5 Sub-sections)
1. **Relaxation Models** - Maxwell, KWW, Dual-KWW with equations
2. **Temperature Kinetics** - Arrhenius vs VFT theory
3. **Vitrimer Chemistry** - Exchange mechanisms explained
4. **Model Comparison** - Decision tree and examples
5. **References** - 16+ foundational papers

### ©️ **Credits Tab**
- Author attribution
- AI coding assistance credits
- Software stack
- Acknowledgments

---

## 🚀 Quick Start

### Installation
```bash
# Clone/download the project
cd CAN_Relax_Project

# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run can_relax/gui/app.py
```

### Usage Flow
1. **Upload** your CSV/XLSX file (Time, Temperature, Modulus columns)
2. **Configure** material properties and physics parameters
3. **Run Analysis** - automatic fitting across temperatures
4. **Review** kinetics and select data for publication
5. **Export** publication-quality figures

---

## 📋 System Requirements

- **Python**: 3.11+ (tested on 3.13)
- **OS**: Windows, macOS, Linux
- **RAM**: 2GB minimum, 4GB+ recommended
- **Disk**: 100MB for installation + data files

### Dependencies
- NumPy (numerical computing)
- Pandas (data handling)
- SciPy (optimization, signal processing)
- Matplotlib (static figures)
- Plotly (interactive visualization)
- Scikit-learn (machine learning, Ridge regression)
- Streamlit (web interface)

---

## 📊 Supported File Formats

### Input Files
- **CSV** (comma-separated values)
  - Wide format: Time | Temp1 | Temp2 | ...
  - Block format: Temp | Time | Modulus | Temp | Time | Modulus | ...

- **XLSX** (Excel spreadsheets)
  - Same format support as CSV
  - Automatic encoding detection

### Output Formats
- **PNG** - Raster image (universal compatibility)
- **PDF** - Vector format (best for printing)
- **SVG** - Scalable vector graphics (editable in Adobe Illustrator)

---

## 🔬 Physics Implemented

### Relaxation Models
```
G(t) = G₀ * exp(-t/τ)                           [Maxwell]
G(t) = G₀ * exp(-(t/τ)^β)                       [Single-KWW]
G(t) = G₀ * [f*exp(-(t/τ₁)^β₁) + (1-f)*exp(-(t/τ₂)^β₂)]  [Dual-KWW]
```

### Temperature Kinetics
```
ln(τ) = ln(τ₀) + Ea/(R*T)                       [Arrhenius]
ln(τ) = ln(τ₀) + B/(T - T₀)                     [Vogel-Fulcher-Tammann]
```

### Advanced Analysis
- Relaxation time spectrum: H(τ) via Ridge regression
- Shift factors: aT = τ(T) / τ(Tref)
- Activation energy: Ea extracted from kinetics
- Volkov temperature: Tv from Arrhenius extrapolation
- Goodness of fit: R², AIC metrics

---

## 📖 Included Documentation

1. **README.md** - Basic overview
2. **PROJECT_OVERVIEW.md** - Comprehensive project guide
3. **CODE_AUDIT_PUBLICATION_READY.md** - Technical audit
4. **Education Tab** - Theory explanations & references
5. **In-app tooltips** - Context-sensitive help

---

## 🎓 Educational Content

**For students and researchers:**
- Clear explanations of each model with LaTeX equations
- Physical interpretation of parameters
- Typical ranges for different materials
- Decision tree: when to use which model
- 16+ foundational literature references
- Vitrimer chemistry detailed explanation

---

## ✅ Quality Assurance

### Testing Performed
- ✅ File parsing (CSV, XLSX, multiple encodings)
- ✅ Model fitting (all three models)
- ✅ Numerical stability (edge cases handled)
- ✅ User interface (all tabs, all workflows)
- ✅ Export functionality (all formats)
- ✅ Data validation (Tg filtering, bounds checking)
- ✅ Error handling (user-friendly messages)

### Code Quality
- ✅ No static analysis errors
- ✅ Exception handling throughout
- ✅ Physics algorithms verified against literature
- ✅ Normalized consistently (G(t)/G₀)
- ✅ Units handled correctly (°C ↔ K conversion)

---

## 🐛 Known Limitations

1. **Batch processing**: Single file at a time (use loop for batch)
2. **Real-time DMA**: No direct oscillatory data import
3. **Advanced statistics**: No bootstrap confidence intervals
4. **Frequency response**: No conversion from relaxation to DMA
5. **3D data**: Single-temperature fits only

**Future enhancements** could address these.

---

## 📧 Author & Credits

**Software Designer & Developer**:
- **Vo Khoa Bui, PhD**
  - Postdoctoral Researcher
  - LPPY Laboratory
  - CY Cergy Paris University, France
  - 📧 Email: khoabui0311@gmail.com
  - 🔗 LinkedIn: https://www.linkedin.com/in/buivokhoa/

**Coding Assistance**:
- Microsoft Copilot (supervised implementation)
- OpenAI ChatGPT (algorithm verification)
- Google Gemini (documentation)

All AI-generated code was reviewed, tested, and validated by Vo Khoa Bui.

---

## 📚 Key References

### Foundational Theory
- Kohlrausch (1847) - Stretched exponential discovery
- Williams & Watts (1970) - KWW formulation
- Ferry (1980) - Polymer viscoelasticity

### Vitrimers & Dynamic Networks
- Denissen et al. (2016) - Vitrimer concept
- Montarnal et al. (2011) - Transesterification vitrimers
- Guerre et al. (2020) - Comprehensive vitrimer review

### Kinetics & Temperature Dependence
- Arrhenius (1889) - Classical equation
- Vogel (1921), Fulcher (1925) - VFT model
- Böhmer et al. (1992) - Fragility & kinetics

See **Education > References** tab for full citations.

---

## 🔒 License & Usage

**Academic & Research Use**: Free  
**Commercial Use**: Contact author

**Recommended Citation**:
```
Bui, V.K. (2025). CAN-Relax Supreme v21.0: 
Stress Relaxation Analysis Software. 
CY Cergy Paris University.
```

---

## 📞 Support & Feedback

For questions, issues, or feature requests:
- Check the **Education** tab for theory help
- See **PROJECT_OVERVIEW.md** for troubleshooting
- Review **CODE_AUDIT** for technical details

---

## 🎉 Ready to Use!

```bash
streamlit run can_relax/gui/app.py
```

**Then open**: `http://localhost:8501`

---

## 📈 Version History

| Version | Date | Changes |
|---------|------|---------|
| **v21.0** | Dec 2025 | 🎉 **RELEASE** - All features, education, credits |
| v20.0 | Dec 2025 | Publication tab, mastercurve, spectrum |
| v19.0 | Dec 2025 | Virtual Lab with export |
| v18.0 | Dec 2025 | Dual-KWW fitting |
| v17.0 | Dec 2025 | Full analysis workflow |

---

**Enjoy analyzing relaxation! 🚀**

*Made with ❤️ for Materials Science Research*
