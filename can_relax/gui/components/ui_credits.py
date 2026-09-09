import streamlit as st

def render_credits_tab(tab_credits):
    with tab_credits:
            st.header("©️ Credits & Copyright")

            st.markdown("""
            ---
            ### 🔬 K Vitrimer Analysis
            **Kinetic Analysis of Vitrimer Relaxation & Kinetics**

            v1.0 | Professional Edition

            ---

            ### 👨‍🔬 Developer

            **Vo Khoa Bui, PhD**
            Postdoctoral Researcher
            LPPY Laboratory, CY Cergy Paris University, France

            ---

            ### 💻 Software Design & Physics Implementation

            **Vo Khoa Bui**
            - Overall concept and physics implementation
            - Algorithm design and validation
            - User interface design
            - Documentation

            ---

            ### 🤖 Coding Assistance

            Development supported by AI-assisted coding tools:
            - **Antigravity** (Google DeepMind)
            - **Microsoft Copilot**
            - **OpenAI ChatGPT**
            - **Google Gemini**

            *(All AI-generated code supervised and validated by Vo Khoa Bui)*

            ---

            ### 📚 Physics & Theory

            This software implements established models for stress relaxation analysis:

            - **Maxwell Model**: Single exponential relaxation
            - **Kohlrausch-Williams-Watts (KWW)**: Stretched exponential for complex systems
            - **Arrhenius & Eyring Kinetics**: Temperature-dependent relaxation time and activation enthalpy/entropy analysis
            - **Temperature–modulus fit**: Empirical occupancy-form fit to observed reference moduli (in **MPa**); thermodynamic interpretation requires independent equilibrium evidence
            - **VFT & Coupled WLF-Arrhenius Kinetics**: Glass transition dynamics and dual glassy-to-chemical transition relaxation
            - **Time-Temperature Superposition (TTS)**: Mastercurve generation
            - **Tikhonov Relaxation Spectrum**: Discrete modal weights using nonnegative Ridge regression, a secant-distance L-curve heuristic and optional measured-tail subtraction
            - **Statistical Model Selection**: AICc and BIC diagnostics for relaxation fits; kinetics model is selected manually

            ---

            ### 🛠️ Technical Stack

            - **Frontend**: Streamlit
            - **Scientific Computing**: NumPy, SciPy, Pandas
            - **Visualization**: Plotly, Matplotlib
            - **Machine Learning**: Scikit-learn
            - **Data Processing**: Openpyxl
            - **Language**: Python 3.11+

            ---

            ### 📖 Application Features

            ✅ **Analysis Tab**: Import & fit relaxation curves with support for MPa and Pa modulus types
            ✅ **Virtual Lab**: Simulate synthetic curves with custom parameters
            ✅ **Publish**: Export TIFF/JPEG relaxation, Arrhenius/VFT, Eyring and modulus-temperature figures
            ✅ **Kinetics**: Temperature-dependent analysis with Arrhenius, Eyring, VFT, Van 't Hoff, and Coupled WLF-Arrhenius fitting
            ✅ **Mastercurve**: Time-Temperature Superposition for multi-temperature data
            ✅ **Spectrum**: Discrete relaxation weights with L-curve parameter selection and $G_{eq}$ subtraction

            ---

            ### 📝 License & Usage

            For academic and research use. Please cite this software if used in publications.

            ---

            ### 📬 Contact & Support

            **Email**: khoabui0311@gmail.com
            **LinkedIn**: https://www.linkedin.com/in/buivokhoa/

            **Institutional Affiliation**:
            CY Cergy Paris University
            Laboratoire de Physique et Polymères (LPPY)
            Cergy, France

            ---

            ### 🙏 Acknowledgments

            - CY Cergy Paris University for computational resources
            - LPPY Laboratory for research infrastructure
            - Open-source Python community for essential libraries

            """)

            st.markdown("---")
            st.caption("🚀 Made with ❤️ for Materials Science Research")
