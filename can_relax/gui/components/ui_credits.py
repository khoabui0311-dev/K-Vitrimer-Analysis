import streamlit as st

def render_credits_tab(tab_credits):
    with tab_credits:
            st.header("©️ Credits & Copyright")

            st.markdown("""
            ---
            ### 🔬 K Vitrimer Analysis
            **Kinetic Analysis of Vitrimer Relaxation & Kinetics**

            v1.0 | Professional Edition | December 2025

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
            - **Microsoft Copilot**
            - **OpenAI ChatGPT**
            - **Google Gemini**

            *(All AI-generated code supervised and validated by Vo Khoa Bui)*

            ---

            ### 📚 Physics & Theory

            This software implements established models for stress relaxation analysis:

            - **Maxwell Model**: Single exponential relaxation
            - **Kohlrausch-Williams-Watts (KWW)**: Stretched exponential for complex systems
            - **Arrhenius & VFT Kinetics**: Temperature-dependent relaxation time analysis
            - **Time-Temperature Superposition (TTS)**: Mastercurve generation
            - **Relaxation Spectrum**: Continuous distribution of relaxation times

            ---

            ### 🛠️ Technical Stack

            - **Frontend**: Streamlit
            - **Scientific Computing**: NumPy, SciPy, Pandas
            - **Visualization**: Plotly, Matplotlib
            - **Machine Learning**: Scikit-learn
            - **Data Processing**: Openpyxl
            - **Language**: Python 3.13+

            ---

            ### 📖 Application Features

            ✅ **Analysis Tab**: Import & fit relaxation curves with physics-based models  
            ✅ **Virtual Lab**: Simulate synthetic curves with custom parameters  
            ✅ **Publish**: Export publication-ready figures (PNG/PDF/SVG)  
            ✅ **Kinetics**: Temperature-dependent analysis with Arrhenius/VFT fitting  
            ✅ **Mastercurve**: Time-Temperature Superposition for multi-temperature data  
            ✅ **Spectrum**: Continuous relaxation time distribution analysis  

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