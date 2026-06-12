import sys
import os
# Add parent directory to path for Streamlit Cloud
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import io
import re
import json
from scipy.optimize import curve_fit
from scipy.stats import linregress
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

# Import proper modules from can_relax
from can_relax.io.parser import parse_wide_format_data as parser_module_func
from can_relax.core.simulator import MaterialSimulator
from can_relax.core.kinetics import KineticsEngine
from can_relax.core.tts import TTSEngine
from can_relax.core.analyzer import CurveAnalyzer
from can_relax.core.spectrum import SpectrumAnalyzer

# ==========================================
# 1. PREMIUM UI CSS INJECTION
# ==========================================
def inject_custom_css():
    st.markdown("""
    <style>
    /* Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    /* Subtle Glassmorphism for Metric Cards */
    [data-testid="stMetric"] {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        transition: transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out;
    }
    
    [data-testid="stMetric"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(0,0,0,0.15);
    }
    
    /* Buttons */
    .stButton > button {
        border-radius: 8px;
        transition: all 0.3s ease;
        font-weight: 500;
    }
    
    .stButton > button:hover {
        transform: scale(1.02);
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
    }
    
    /* Tabs styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    
    .stTabs [data-baseweb="tab"] {
        border-radius: 4px 4px 0 0;
        padding: 10px 20px;
        transition: background-color 0.2s;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: rgba(255, 255, 255, 0.1);
        border-bottom-color: #00CC96 !important;
    }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. CORE ENGINE (INTERNALIZED FROM can_relax)
# ==========================================

# --- A. ROBUST PARSER (The Fix) ---
# Helper wrapper for Streamlit UploadedFile
def parse_uploaded_file(uploaded_file):
    """Wrapper to handle Streamlit UploadedFile objects for parsing"""
    import tempfile
    import os
    
    if uploaded_file is None:
        return {}
    
    # Save to temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx' if 'xlsx' in uploaded_file.name else '.csv') as tmp:
        tmp.write(uploaded_file.getbuffer())
        tmp_path = tmp.name
    
    try:
        # Use the proper parser - it returns {temp: DataFrame with 'Time' and 'Modulus' columns}
        result = parser_module_func(tmp_path)
        return result
    finally:
        os.unlink(tmp_path)


# ==========================================
# 2. APP UI
# ==========================================
st.set_page_config(layout="wide", page_title="K Vitrimer Analysis", page_icon="🧪")
inject_custom_css()
st.sidebar.title("🧪 K Vitrimer Analysis")
st.sidebar.caption("v1.0 | Professional Edition")

# Init Modules
sim = MaterialSimulator()
tts_engine = TTSEngine()
analyzer = CurveAnalyzer()
spectrum_engine = SpectrumAnalyzer()

# Helper
def get_tau_1_over_e(t, g):
    target = 0.36788 * g[0] # Scale target by G0
    try:
        if g[0] > g[-1]: return np.interp(target, g[::-1], t[::-1])
    except: pass
    return np.nan

# TABS
tab_analysis, tab_sim, tab_pub, tab_comparison, tab_plotting, tab_education, tab_credits = st.tabs([
    "🚀 Analysis", "🧪 Virtual Lab", "📝 Publish", "📊 Compare", "📈 Plotting", "📚 Education", "©️ Credits"
])

# ------------------------------------------------------------------
# TAB 1: ANALYSIS (Exact Workflow)
# ------------------------------------------------------------------
with tab_analysis:
    # ── Data Input ──────────────────────────────────────────────
    with st.sidebar.expander("📁 Data Input", expanded=True):
        uploaded_file = st.file_uploader(
            "Upload CSV or XLSX",
            type=["csv", "xlsx"],
            label_visibility="collapsed",
            help="Wide-format CSV or XLSX: columns = Temperature, then Time/Modulus pairs"
        )

    # ── Material DNA ─────────────────────────────────────────────
    with st.sidebar.expander("🧬 Material DNA", expanded=False):
        mat_class = st.selectbox("Class", ["Neat Material", "Composite", "Blend"])
        if mat_class == "Neat Material":
            mat_type = st.selectbox("Type", ["Vitrimer", "Thermoplastic", "Thermoset", "Vitrimer-like"])
            composition = "Pure"
        elif mat_class == "Composite":
            mat_type = st.selectbox("Matrix", ["Vitrimer", "Thermoplastic", "Thermoset"])
            composition = st.text_input("Filler", "Silica")
        else:
            mat_type = "Blend"
            composition = st.text_input("Components", "Vitrimer/Epoxy")
        st.markdown("**Exchange Chemistry**")
        chem_tags = st.multiselect("Mechanism", ["Transesterification", "Disulfide", "Imine", "Boronic Ester", "Urethane"], default=["Transesterification"])

    # ── Physics & Fitting (merged) ────────────────────────────────
    with st.sidebar.expander("⚙️ Physics & Fitting", expanded=True):
        G_prime_input = st.number_input("Rubbery G' (MPa)", 0.01, 5000.0, 1.0, help="Used for Tv calculation")
        Tg_input = st.number_input("Tg (°C)", value=50.0, help="Curves below this temperature are skipped")
        st.markdown("---")
        fit_model = st.selectbox("Model", ["Maxwell", "Single_KWW", "Dual_KWW"])
        kinetics_mode = st.radio("Kinetics Base:", ["Fit Parameter", "Raw 1/e"])

    # ── Always-visible Run button ─────────────────────────────────
    st.sidebar.markdown("---")
    run_btn = st.sidebar.button("▶ Run Analysis", type="primary", width='stretch')

    # PROCESS
    if uploaded_file and run_btn:
        # Use the wrapper to parse Streamlit UploadedFile
        curves = parse_uploaded_file(uploaded_file)
        
        if not curves: st.error("Parsing failed. Data must be columns of Temp/Time/Modulus."); st.stop()
        
        res = []
        skipped = []
        bar = st.progress(0)
        meta = {'class': mat_class, 'type': mat_type, 'composition': composition, 'chemistry': json.dumps(chem_tags)}

        idx = 0
        for temp, df in curves.items():
            # Pass Tg for filtering
            out = analyzer.fit_one_temp(temp, df, Tg=Tg_input)
            if out.get('Valid', False):
                out['Best_Model'] = fit_model 
                out['Tau_1e'] = get_tau_1_over_e(out['Raw']['t'], out['Raw']['g'])
                res.append(out)
            else:
                skipped.append(f"{temp}C")
            idx += 1
            bar.progress(idx/len(curves))
            
        st.session_state.results = res
        if res: st.success(f"Processed {len(res)} curves.")
        if skipped: st.warning(f"Skipped (Below Tg): {', '.join(skipped)}")

    # DISPLAY
    if 'results' in st.session_state and st.session_state.results:
        all_results = st.session_state.results
        
        # Live Filter
        all_temps = sorted([r['Temp'] for r in all_results])
        col_sel, _ = st.columns([2, 1])
        with col_sel:
            selected_temps = st.multiselect("Select Curves:", all_temps, default=all_temps)
        active_results = [r for r in all_results if r['Temp'] in selected_temps]
        st.session_state.active_results = active_results 

        t1, t2, t3, t4 = st.tabs(["Curves", "Kinetics", "Mastercurve", "\U0001f308 Spectrum"])
        
        # 1. CURVES
        with t1:
            # ── Compact control row above chart ──
            ctl1, ctl2, ctl3, ctl4, _ctl5 = st.columns([1.2, 1.2, 1.2, 1.0, 2.4])
            with ctl1:
                time_axis_type = st.radio("Time Scale", ["Log", "Linear"], horizontal=True, key="time_axis_type")
            with ctl2:
                curves_y_axis_scale = st.radio("Y Scale", ["Linear", "Log"], horizontal=True, key="curves_y_axis_scale")
            with ctl3:
                mod_plot_type = st.radio("Modulus Type", ["Normalized", "Absolute"], horizontal=True, key="mod_plot_type")
            with ctl4:
                show_fits = st.checkbox("Show Fits", True, key="show_fits")

            fig = go.Figure()
            for r in active_results:
                t_raw = r['Raw']['t']
                g_raw = r['Raw']['g']
                G0 = r['Raw'].get('G0', 1.0)
                g_plot = g_raw if mod_plot_type == "Normalized" else g_raw * G0
                step = max(1, len(t_raw)//300)
                fig.add_trace(go.Scatter(
                    x=t_raw[::step],
                    y=g_plot[::step],
                    mode='markers',
                    name=f"{r['Temp']}C",
                    marker=dict(size=6, opacity=0.8)
                ))
                if show_fits and fit_model in r['Fits']:
                    g_fit_raw = r['Fits'][fit_model].get('curve', r['Raw']['g'])
                    g_fit_plot = g_fit_raw if mod_plot_type == "Normalized" else g_fit_raw * G0
                    fig.add_trace(go.Scatter(
                        x=t_raw,
                        y=g_fit_plot,
                        mode='lines',
                        name=f"Fit",
                        line=dict(width=2, dash='dash', color='black')
                    ))

            t_type = "log" if time_axis_type == "Log" else "linear"
            y_type = "log" if curves_y_axis_scale == "Log" else "linear"
            y_title = "G(t)/G₀" if mod_plot_type == "Normalized" else "G(t) (MPa)"
            fig.update_xaxes(type=t_type, title="Time (s)")
            fig.update_yaxes(type=y_type, title=y_title)
            fig.update_layout(height=500, margin=dict(l=20,r=20,t=20,b=20))
            st.plotly_chart(fig, width='stretch')

            # ── Fitting parameters: collapsible ──
            with st.expander("\U0001f4ca Fitting Parameters", expanded=False):
                fit_details = []
                for r in active_results:
                    temp = r['Temp']
                    if fit_model in r['Fits']:
                        p = r['Fits'][fit_model]['popt']
                        r2 = r['Fits'][fit_model]['r2']
                        aic = r['Fits'][fit_model].get('aic', np.inf)
                        bic = r['Fits'][fit_model].get('bic', np.inf)
                        if fit_model == "Maxwell":
                            fit_details.append({"Temperature (\u00b0C)": temp, "Tau (s)": p[0], "R\u00b2": r2, "AICc": aic, "BIC": bic})
                        elif fit_model == "Single_KWW":
                            fit_details.append({"Temperature (\u00b0C)": temp, "Tau (s)": p[0], "Beta (\u03b2)": p[1], "R\u00b2": r2, "AICc": aic, "BIC": bic})
                        elif fit_model == "Dual_KWW":
                            fit_details.append({"Temperature (\u00b0C)": temp, "Fraction A": p[0], "Tau 1 (s)": p[1], "Beta 1 (\u03b21)": p[2], "Tau 2 (s)": p[3], "Beta 2 (\u03b22)": p[4], "R\u00b2": r2, "AICc": aic, "BIC": bic})
                if fit_details:
                    df_details = pd.DataFrame(fit_details)
                    col_config = {
                        "Temperature (\u00b0C)": st.column_config.NumberColumn(format="%.1f"),
                        "R\u00b2": st.column_config.NumberColumn(format="%.4f"),
                        "AICc": st.column_config.NumberColumn(format="%.2f"),
                        "BIC": st.column_config.NumberColumn(format="%.2f")
                    }
                    if fit_model == "Maxwell":
                        col_config["Tau (s)"] = st.column_config.NumberColumn(format="%.3e")
                    elif fit_model == "Single_KWW":
                        col_config["Tau (s)"] = st.column_config.NumberColumn(format="%.3e")
                        col_config["Beta (\u03b2)"] = st.column_config.NumberColumn(format="%.3f")
                    elif fit_model == "Dual_KWW":
                        col_config["Fraction A"] = st.column_config.NumberColumn(format="%.3f")
                        col_config["Tau 1 (s)"] = st.column_config.NumberColumn(format="%.3e")
                        col_config["Beta 1 (\u03b21)"] = st.column_config.NumberColumn(format="%.3f")
                        col_config["Tau 2 (s)"] = st.column_config.NumberColumn(format="%.3e")
                        col_config["Beta 2 (\u03b22)"] = st.column_config.NumberColumn(format="%.3f")
                    st.dataframe(df_details, column_config=col_config, hide_index=True, width='stretch')
                    csv_details = df_details.to_csv(index=False)
                    st.download_button("\U0001f4e5 Download Fit Parameters CSV", csv_details, "fit_parameters.csv", key="dl_fit_params")

        # 2. KINETICS
        with t2:
            k_data = []
            for r in active_results:
                t_val = np.nan
                if kinetics_mode == "Raw 1/e": t_val = r.get('Tau_1e', np.nan)
                elif fit_model in r['Fits']:
                    p = r['Fits'][fit_model]['popt']
                    if fit_model == "Maxwell": idx = 0
                    elif fit_model == "Single_KWW": idx = 0
                    elif fit_model == "Dual_KWW": idx = 3
                    else: idx = 0
                    t_val = p[idx]
                if t_val > 0:
                    k_data.append({"Include": True, "Temp": r['Temp'], "1000/T": 1000.0/(r['Temp']+273.15), "Tau": t_val, "ln(Tau)": np.log(t_val), "Type": "Main"})

            if k_data:
                df_k = pd.DataFrame(k_data)
                col_edit, col_chart = st.columns([1, 2])
                with col_edit:
                    st.markdown("##### Outlier Rejection")
                    st.caption("Uncheck rows to exclude them from the fit.")
                    edited_df = st.data_editor(df_k, column_config={"Include": st.column_config.CheckboxColumn("Fit?", default=True)}, hide_index=True, height=280, width='stretch')
                    st.session_state.kinetics_df = edited_df
                    
                    st.markdown("---")
                    kinetics_model_type = st.selectbox(
                        "Kinetics Model", 
                        ["Arrhenius", "VFT", "Eyring (Transition State)", "Van 't Hoff (Decrosslinking)", "Coupled WLF-Arrhenius"],
                        key="kinetics_model_type"
                    )

                with col_chart:
                    active = edited_df[edited_df["Include"] == True]
                    if len(active) >= 2:
                        k_engine = KineticsEngine()
                        fit_res = None
                        
                        if kinetics_model_type == "Arrhenius":
                            fit_res = k_engine.fit_arrhenius(active["Temp"].tolist(), active["Tau"].tolist())
                        elif kinetics_model_type == "VFT":
                            fit_res = k_engine.fit_vft(active["Temp"].tolist(), active["Tau"].tolist())
                        elif kinetics_model_type == "Eyring (Transition State)":
                            fit_res = k_engine.fit_eyring(active["Temp"].tolist(), active["Tau"].tolist())
                        elif kinetics_model_type == "Van 't Hoff (Decrosslinking)":
                            g0_map = {r['Temp']: r['Raw']['G0'] for r in active_results}
                            active_G0s = [g0_map[t_val] for t_val in active["Temp"].tolist()]
                            fit_res = k_engine.fit_van_t_hoff(active["Temp"].tolist(), active_G0s)
                        elif kinetics_model_type == "Coupled WLF-Arrhenius":
                            fit_res = k_engine.fit_coupled_kinetics(active["Temp"].tolist(), active["Tau"].tolist(), Tg=Tg_input)
                            
                        if fit_res:
                            r_sq = fit_res.get("R2", 0.0)
                            
                            if fit_res["Type"] == "Arrhenius":
                                Ea = fit_res["Ea"]
                                Ea_std = fit_res["Ea_std"]
                                slope = fit_res["Params"]["slope"]
                                intercept = fit_res["Params"]["intercept"]
                                
                                G_Pa = G_prime_input * 1e6
                                tau_target = 1e12 / G_Pa
                                ln_tau_target = np.log(tau_target)
                                Tv_val = (1.0 / ((ln_tau_target - intercept)/slope)) - 273.15 if slope != 0 else 0.0
                                
                                mc1, mc2, mc3 = st.columns(3)
                                mc1.metric("E\u2090", f"{Ea:.1f} \u00b1 {Ea_std:.1f} kJ/mol")
                                mc2.metric("T\u1d65", f"{Tv_val:.1f} \u00b0C")
                                mc3.metric("R\u00b2", f"{r_sq:.4f}")
                                
                            elif fit_res["Type"] == "VFT":
                                B = fit_res["Params"]["B"]
                                T0_C = fit_res["Params"]["T0"] - 273.15
                                
                                mc1, mc2, mc3 = st.columns(3)
                                mc1.metric("VFT B", f"{B:.1f} K")
                                mc2.metric("T\u2080 (VFT)", f"{T0_C:.1f} \u00b0C")
                                mc3.metric("R\u00b2", f"{r_sq:.4f}")
                                
                            elif fit_res["Type"] == "Eyring":
                                dH = fit_res["dH"]
                                dH_std = fit_res["dH_std"]
                                dS = fit_res["dS"]
                                
                                mc1, mc2, mc3 = st.columns(3)
                                mc1.metric("\u0394H\u2021 (Enthalpy)", f"{dH:.1f} \u00b1 {dH_std:.1f} kJ/mol")
                                mc2.metric("\u0394S\u2021 (Entropy)", f"{dS:.1f} J/mol\u00b7K")
                                mc3.metric("R\u00b2", f"{r_sq:.4f}")
                                
                            elif fit_res["Type"] == "Van_t_Hoff":
                                dH_diss = fit_res["dH_diss"]
                                dS_diss = fit_res["dS_diss"]
                                G0_max = fit_res["G0_max"]
                                
                                mc1, mc2, mc3 = st.columns(3)
                                mc1.metric("\u0394H_diss", f"{dH_diss:.1f} kJ/mol")
                                mc2.metric("\u0394S_diss", f"{dS_diss:.1f} J/mol\u00b7K")
                                mc3.metric("R\u00b2", f"{r_sq:.4f}")
                                st.caption(f"Estimated G₀,max: {G0_max:.3f} MPa")
                                
                            elif fit_res["Type"] == "Coupled":
                                Ea_chem = fit_res["Ea_chem"]
                                B_glass = fit_res["B_glass"]
                                T0_glass = fit_res["T0_glass"]
                                
                                mc1, mc2, mc3 = st.columns(3)
                                mc1.metric("Ea_chem", f"{Ea_chem:.1f} kJ/mol")
                                mc2.metric("T\u2080 (Glass)", f"{T0_glass:.1f} \u00b0C")
                                mc3.metric("R\u00b2", f"{r_sq:.4f}")

                            fig_k = go.Figure()
                            
                            if fit_res["Type"] == "Arrhenius":
                                fig_k.add_trace(go.Scatter(x=fit_res["Plot"]["x"], y=fit_res["Plot"]["y"], mode='markers', name="Data"))
                                xr = np.linspace(fit_res["Plot"]["x"].min()*0.95, fit_res["Plot"]["x"].max()*1.05, 50)
                                yr = fit_res["Params"]["slope"] * xr + fit_res["Params"]["intercept"]
                                fig_k.add_trace(go.Scatter(x=xr, y=yr, mode='lines', name=f"Ea={Ea:.1f} kJ/mol", line=dict(dash='dash', color='red')))
                                Tv_invT = 1.0 / (Tv_val + 273.15)
                                fig_k.add_trace(go.Scatter(x=[Tv_invT], y=[ln_tau_target], mode='markers', marker=dict(symbol='star', size=14, color='gold'), name=f"Tv={Tv_val:.1f}C"))
                                fig_k.update_layout(xaxis_title="1/T (K\u207b\u00b9)", yaxis_title="ln(\u03c4)")
                                
                            elif fit_res["Type"] == "VFT":
                                fig_k.add_trace(go.Scatter(x=fit_res["Plot"]["x"], y=fit_res["Plot"]["y"], mode='markers', name="Data"))
                                T_K_grid = np.linspace(273.15 + min(active["Temp"]), 273.15 + max(active["Temp"]), 50)
                                pred_grid = fit_res["Params"]["A"] + fit_res["Params"]["B"] / (T_K_grid - fit_res["Params"]["T0"])
                                fig_k.add_trace(go.Scatter(x=1.0/T_K_grid, y=pred_grid, mode='lines', name="VFT Fit", line=dict(dash='dash', color='red')))
                                fig_k.update_layout(xaxis_title="1/T (K\u207b\u00b9)", yaxis_title="ln(\u03c4)")
                                
                            elif fit_res["Type"] == "Eyring":
                                fig_k.add_trace(go.Scatter(x=fit_res["Plot"]["x"], y=fit_res["Plot"]["y"], mode='markers', name="Data"))
                                xr = np.linspace(fit_res["Plot"]["x"].min()*0.95, fit_res["Plot"]["x"].max()*1.05, 50)
                                yr = fit_res["Params"]["slope"] * xr + fit_res["Params"]["intercept"]
                                fig_k.add_trace(go.Scatter(x=xr, y=yr, mode='lines', name=f"\u0394H\u2021={dH:.1f} kJ/mol", line=dict(dash='dash', color='red')))
                                fig_k.update_layout(xaxis_title="1/T (K\u207b\u00b9)", yaxis_title="ln(\u03c4 \u00b7 T)")
                                
                            elif fit_res["Type"] == "Van_t_Hoff":
                                fig_k.add_trace(go.Scatter(x=fit_res["Plot"]["x"], y=fit_res["Plot"]["y"], mode='markers', name="Data"))
                                T_K_grid = np.linspace(273.15 + min(active["Temp"]), 273.15 + max(active["Temp"]), 50)
                                R_GAS_VAL = 8.314462
                                pred_grid = fit_res["Params"]["G0_max"] / (1.0 + np.exp(np.clip(-fit_res["Params"]["dH_diss"] / (R_GAS_VAL * T_K_grid) + fit_res["Params"]["dS_diss"] / R_GAS_VAL, -50.0, 50.0)))
                                fig_k.add_trace(go.Scatter(x=1000.0/T_K_grid, y=pred_grid, mode='lines', name="Van 't Hoff Fit", line=dict(dash='dash', color='red')))
                                fig_k.update_layout(xaxis_title="1000/T (K\u207b\u00b9)", yaxis_title="G\u2080 (MPa)")
                                
                            elif fit_res["Type"] == "Coupled":
                                fig_k.add_trace(go.Scatter(x=fit_res["Plot"]["x"], y=fit_res["Plot"]["y"], mode='markers', name="Data"))
                                T_K_grid = np.linspace(273.15 + min(active["Temp"]), 273.15 + max(active["Temp"]), 50)
                                T0_val = fit_res["Params"]["T0"]
                                R_GAS_VAL = 8.314462
                                term1 = np.exp(fit_res["Params"]["ln_A"] + fit_res["Params"]["Ea"] / (R_GAS_VAL * T_K_grid))
                                term2 = np.exp(np.clip(fit_res["Params"]["ln_C"] + fit_res["Params"]["B"] / (T_K_grid - T0_val), -50, 50))
                                pred_grid = np.log(term1 + term2)
                                fig_k.add_trace(go.Scatter(x=1.0/T_K_grid, y=pred_grid, mode='lines', name="Coupled Fit", line=dict(dash='dash', color='red')))
                                fig_k.update_layout(xaxis_title="1/T (K\u207b\u00b9)", yaxis_title="ln(\u03c4)")
                                
                            fig_k.update_layout(height=420, margin=dict(l=10, r=10, t=20, b=20))
                            st.plotly_chart(fig_k, width='stretch')
                        else:
                            st.error("Kinetics fitting failed.")
                    else:
                        st.warning("Need at least 2 data points with Include checked.")


        # 3. MASTERCURVE (TTS)
        with t3:
            if len(active_results) >= 2:
                col_tts_ctrl, col_tts_plot = st.columns([1, 3])
                with col_tts_ctrl:
                    st.markdown("##### TTS Settings")
                    # Reference temperature selection
                    temps_available = [r['Temp'] for r in active_results]
                    mid_idx = len(temps_available) // 2
                    ref_temp_sel = st.selectbox("Reference T (°C)", temps_available, index=mid_idx)
                    
                    # Generate mastercurve
                    if st.button("Generate Mastercurve"):
                        try:
                            master_data = tts_engine.generate_mastercurve(active_results, ref_temp=ref_temp_sel)
                            st.session_state.master_data = master_data
                            st.success(f"✅ Mastercurve at Tref = {master_data['T_ref']}°C")
                        except Exception as e:
                            st.error(f"Error: {e}")
                
                with col_tts_plot:
                    if 'master_data' in st.session_state:
                        master = st.session_state.master_data
                        
                        # Plot mastercurve
                        fig_mc = go.Figure()
                        
                        # Add shifted data
                        fig_mc.add_trace(go.Scatter(
                            x=master['Master_t'],
                            y=master['Master_g'],
                            mode='markers',
                            marker=dict(size=4, opacity=0.6, color='steelblue'),
                            name='Shifted Data'
                        ))
                        
                        fig_mc.update_xaxes(type="log", title=f"Shifted Time (s) @ Tref={master['T_ref']}°C")
                        fig_mc.update_yaxes(title="G(t) (MPa)")
                        fig_mc.update_layout(height=500, title="Time-Temperature Superposition Mastercurve")
                        st.plotly_chart(fig_mc, width='stretch')
                        
                        # Display shift factors
                        st.markdown("##### Shift Factors (aT)")
                        shifts_df = pd.DataFrame([
                            {"Temperature (°C)": T, "log(aT)": np.log10(aT), "aT": f"{aT:.2e}"}
                            for T, aT in master['Shifts'].items()
                        ])
                        st.dataframe(shifts_df, hide_index=True, width='stretch')
                    else:
                        st.info("👈 Click 'Generate Mastercurve' to create TTS plot")
            else:
                st.warning("⚠️ Need at least 2 temperatures for TTS mastercurve")

        # 4. SPECTRUM
        with t4:
            c_spec, c_ctrl = st.columns([3, 1])
            with c_ctrl:
                opt_alpha = st.checkbox("Auto-optimize Smoothness (L-curve)", value=True, key="opt_alpha")
                if not opt_alpha:
                    alpha_reg = st.slider("Smoothness (\u03b1)", 1e-5, 10.0, 0.1, step=0.01, format="%.5f", key="alpha_reg")
                else:
                    alpha_reg = 0.1  # ignored
                sub_G_eq = st.checkbox("Subtract G_eq (Tail Modulus)", value=True, key="sub_G_eq")
                n_modes = st.slider("Bins", 20, 200, 50, key="n_modes")
                
                # We will display the L-curve details below the settings
                st.markdown("---")
                st.markdown("**Optimized Fit Details:**")
                
            with c_spec:
                fig_h = go.Figure()
                for i, r in enumerate(active_results):
                    t = r['Raw']['t']
                    g = r['Raw']['g']
                    if mod_plot_type == "Absolute":
                        g = g * r['Raw']['G0']
                    
                    tau_grid, H = spectrum_engine.compute_continuous_spectrum(
                        t, g, num_modes=n_modes, alpha=alpha_reg, 
                        optimize_alpha=opt_alpha, subtract_G_eq=sub_G_eq
                    )
                    
                    # Display L-curve corner alpha and G_eq details
                    with c_ctrl:
                        st.caption(f"{r['Temp']}\u00b0C: \u03b1={spectrum_engine.last_alpha:.2e} (G_eq: {spectrum_engine.last_G_eq:.2e})")
                        
                    fig_h.add_trace(go.Scatter(x=tau_grid, y=H, mode='lines', name=f"{r['Temp']}C", fill='tozeroy'))
                fig_h.update_xaxes(type="log", title="Tau (s)"); fig_h.update_yaxes(title="H(τ)")
                st.plotly_chart(fig_h, width="stretch")



# ------------------------------------------------------------------
# TAB 3: VIRTUAL LAB
# ------------------------------------------------------------------
with tab_sim:
    st.subheader("🧪 Virtual Lab")
    col_ctrl, col_dash = st.columns([0.3, 0.7])
    with col_ctrl:
        with st.container(border=True):
            mode = st.radio("Mode", ["⚗️ Chemist", "📐 Engineering", "🎯 Target"], label_visibility="collapsed")
            st.markdown("---")
            disable_G = (mode.startswith("📐"))
            G_modulus = st.number_input("Modulus G (MPa)", 0.01, 2000.0, 1.0, 0.1, disabled=disable_G)
            log_tau0 = st.slider("log(tau0)", -18, -3, -12)
            tau0 = 10**log_tau0
            disable_Ea = (mode.startswith("🎯"))
            Ea_sim = st.number_input("Ea (kJ/mol)", 10.0, 300.0, 90.0, disabled=disable_Ea)
            disable_Tv = (mode.startswith("⚗️"))
            Tv_sim = st.number_input("Tv (°C)", -100.0, 400.0, 120.0, disabled=disable_Tv)
            st.markdown("---")
            sim_model = st.selectbox("Model", ["Single_KWW", "Maxwell", "Dual_KWW"])
            beta_sim = st.slider("Beta", 0.2, 1.0, 0.8)
            Tg_sim = st.number_input("Tg", value=50.0)
            
            frac_val = 0.5; factor_val = 50.0; Ea2_sim = Ea_sim; beta2_sim = beta_sim
            if sim_model == "Dual_KWW":
                Ea2_sim = st.number_input("Ea2", value=Ea_sim)
                frac_val = st.slider("Frac", 0.1, 0.9, 0.5)
                factor_val = st.number_input("Separation", value=50.0)
            st.markdown("---")
            temp_input = st.text_input("Temps", "130, 140, 150, 160, 170")

    with col_dash:
        c_res1, c_res2 = st.columns([1, 1])
        R_GAS = 8.314462
        with c_res1:
            if mode.startswith("⚗️"): 
                try:
                    term = np.log(1e6 / (G_modulus * tau0))
                    Tv_res = ((Ea_sim * 1000.0) / (R_GAS * term)) - 273.15 if term > 0 else 999
                except: Tv_res = 999
                st.metric("Result Tv", f"{Tv_res:.1f} °C")
                if Tv_res < 900: Tv_sim = Tv_res
            elif mode.startswith("📐"):
                try: G_res = 1e6 / (tau0 * np.exp((Ea_sim * 1000.0) / (R_GAS * (Tv_sim + 273.15))))
                except: G_res = 0.0
                st.metric("Required G", f"{G_res:.2f} MPa")
                if G_res > 0: G_modulus = G_res
            elif mode.startswith("🎯"):
                try: Ea_res = (R_GAS * (Tv_sim + 273.15) * np.log(1e6 / (G_modulus * tau0))) / 1000.0
                except: Ea_res = 0.0
                st.metric("Required Ea", f"{Ea_res:.1f} kJ/mol")
                if Ea_res > 0: Ea_sim = Ea_res

        try: exp_temps = sorted([float(x.strip()) for x in temp_input.split(',') if x.strip()])
        except: exp_temps = []

        if exp_temps:
            params = {'Ea': Ea_sim, 'Tv': Tv_sim, 'Tg': Tg_sim, 'G_plateau': G_modulus, 'beta': beta_sim, 'fraction_fast': frac_val, 'tau_factor': factor_val, 'Ea_2': Ea2_sim, 'beta_2': beta2_sim}
            sim_results = []; fitted_taus = []; valid_temps = []
            
            for T in exp_temps:
                t, g_true, _ = sim.simulate_curve(T, sim_model, params)
                sim_results.append((T, t, g_true))
                if T > Tg_sim:
                    try:
                        # Simple tau extraction from simulated curve
                        target = 0.36788 * g_true[0]
                        t_fit = np.interp(target, g_true[::-1], t[::-1])
                        if 1e-5 < t_fit < 1e12: fitted_taus.append(t_fit); valid_temps.append(T)
                    except: pass

            c_p1, c_p2 = st.columns(2)
            with c_p1:
                fig = go.Figure()
                colors = ['#EF553B', '#636EFA', '#00CC96', '#AB63FA', '#FFA15A']
                for i, (T, t, g) in enumerate(sim_results):
                    fig.add_trace(go.Scatter(x=t, y=g, mode='lines', name=f"{T}°C", line=dict(color=colors[i%5])))
                fig.update_xaxes(type="log", title="Time"); fig.update_yaxes(title="G(t)")
                fig.update_layout(margin=dict(l=20,r=20,t=0,b=20), height=300, showlegend=False)
                st.plotly_chart(fig, width="stretch")
                st.session_state.sim_fig_relax = fig

            with c_p2:
                if len(valid_temps) >= 3:
                    inv_T = 1000.0 / (np.array(valid_temps) + 273.15)
                    ln_tau = np.log(np.array(fitted_taus))
                    k_engine = KineticsEngine()
                    fit_res = k_engine.fit_arrhenius(valid_temps, fitted_taus)
                    if fit_res:
                        slope = fit_res['Params']['slope'] / 1000.0
                        intercept = fit_res['Params']['intercept']
                        
                        G_Pa = G_modulus * 1e6; tau_Tv = 1e12 / G_Pa; ln_tau_target = np.log(tau_Tv)
                        Tv_rec = (1000.0 / ((ln_tau_target - intercept)/slope)) - 273.15 if slope!=0 else 0
                    
                    fig_k = go.Figure()
                    fig_k.add_trace(go.Scatter(x=inv_T, y=ln_tau, mode='markers'))
                    xr = np.linspace(min(inv_T)*0.9, max(inv_T)*1.1, 10)
                    fig_k.add_trace(go.Scatter(x=xr, y=slope*xr+intercept, mode='lines', line=dict(dash='dash', color='red')))
                    fig_k.add_trace(go.Scatter(x=[(1000.0/(Tv_rec+273.15))], y=[ln_tau_target], mode='markers', marker=dict(size=12, color='gold', symbol='star')))
                    fig_k.update_layout(xaxis_title="1000/T", yaxis_title="ln(tau)", margin=dict(l=20,r=20,t=0,b=20), height=300, showlegend=False)
                    st.plotly_chart(fig_k, width="stretch")
                    st.caption(f"✅ Recovered Tv: {Tv_rec:.1f} °C")
                    st.session_state.sim_fig_kinetics = fig_k
            
            # Export Settings
            st.markdown("---")
            st.subheader("📥 Export Simulation Plots")
            exp_c1, exp_c2, exp_c3, exp_c4 = st.columns(4)
            with exp_c1:
                sim_fig_fmt = st.selectbox("Format", ["png", "bmp", "tiff", "pdf", "svg"], key="sim_fmt")
                sim_fig_dpi = st.number_input("DPI", 72, 1200, 300, 50, key="sim_dpi")
            with exp_c2:
                sim_fig_width = st.number_input("Width (in)", 2.0, 10.0, 3.5, 0.1, key="sim_width")
                sim_fig_height = st.number_input("Height (in)", 2.0, 10.0, 3.0, 0.1, key="sim_height")
            
            # Export Buttons
            exp_col1, exp_col2 = st.columns(2)
            with exp_col1:
                if st.button("📥 Export Relaxation Curves", key="export_sim_relax"):
                    if 'sim_fig_relax' in st.session_state:
                        fig_export = go.Figure(st.session_state.sim_fig_relax)
                        # Convert Plotly to matplotlib for better control
                        fig_mpl, ax_mpl = plt.subplots(figsize=(sim_fig_width, sim_fig_height))
                        colors = plt.cm.tab10(np.linspace(0, 1, len(sim_results)))
                        for i, (T, t, g) in enumerate(sim_results):
                            # Normalize
                            g_norm = g / g[0] if g[0] > 0 else g
                            ax_mpl.plot(t, g_norm, linewidth=2, label=f"{T}°C", color=colors[i])
                        ax_mpl.set_xscale('log')
                        ax_mpl.set_xlabel("Time (s)", fontsize=11, fontweight='bold')
                        ax_mpl.set_ylabel("G(t) / G₀", fontsize=11, fontweight='bold')
                        ax_mpl.grid(True, alpha=0.3, linestyle='--')
                        ax_mpl.legend(frameon=True, fontsize=10)
                        ax_mpl.tick_params(labelsize=10)
                        plt.tight_layout()
                        
                        buf = io.BytesIO()
                        if sim_fig_fmt.lower() in ['bmp', 'tiff']:
                            buf_tmp = io.BytesIO()
                            fig_mpl.savefig(buf_tmp, format='png', dpi=sim_fig_dpi, bbox_inches='tight')
                            buf_tmp.seek(0)
                            from PIL import Image
                            Image.open(buf_tmp).save(buf, format=sim_fig_fmt.upper())
                        else:
                            fig_mpl.savefig(buf, format=sim_fig_fmt, dpi=sim_fig_dpi, bbox_inches='tight')
                        buf.seek(0)
                        st.download_button("⬇️ Download Relaxation", buf, f"Simulation_Relaxation.{sim_fig_fmt}", key="dl_sim_relax")
                        plt.close(fig_mpl)
                    else:
                        st.warning("Generate simulation first")
            
            with exp_col2:
                if st.button("📥 Export Arrhenius Plot", key="export_sim_arr"):
                    if 'sim_fig_kinetics' in st.session_state and len(valid_temps) >= 3:
                        inv_T = 1000.0 / (np.array(valid_temps) + 273.15)
                        ln_tau = np.log(np.array(fitted_taus))
                        k_engine = KineticsEngine()
                        fit_res = k_engine.fit_arrhenius(valid_temps, fitted_taus)
                        if fit_res:
                            slope = fit_res['Params']['slope'] / 1000.0
                            intercept = fit_res['Params']['intercept']
                            r_sq = fit_res['R2']
                            Ea_rec = fit_res['Ea']
                            
                            G_Pa = G_modulus * 1e6; tau_Tv = 1e12 / G_Pa; ln_tau_target = np.log(tau_Tv)
                            Tv_rec = (1000.0 / ((ln_tau_target - intercept)/slope)) - 273.15 if slope!=0 else 0
                        
                        fig_arr = plt.figure(figsize=(sim_fig_width, sim_fig_height))
                        ax_arr = fig_arr.add_subplot(111)
                        
                        # Plot data
                        ax_arr.scatter(inv_T, ln_tau, s=80, alpha=0.8, edgecolors='black', linewidth=1.5, color='steelblue', zorder=3)
                        
                        # Plot fit line
                        x_range = np.linspace(min(inv_T)*0.9, max(inv_T)*1.1, 100)
                        y_fit = slope * x_range + intercept
                        ax_arr.plot(x_range, y_fit, '--', color='red', linewidth=2, label=f'Eₐ = {Ea_rec:.1f} kJ/mol\nR² = {r_sq:.4f}', zorder=2)
                        
                        # Plot Tv
                        Tv_x = (ln_tau_target - intercept) / slope
                        ax_arr.plot([Tv_x], [ln_tau_target], marker='*', markersize=18, color='gold', markeredgecolor='black', markeredgewidth=1.5, label=f'Tᵥ = {Tv_rec:.1f}°C', zorder=4)
                        
                        ax_arr.set_xlabel("1000/T (K⁻¹)", fontsize=11, fontweight='bold')
                        ax_arr.set_ylabel("ln(τ)", fontsize=11, fontweight='bold')
                        ax_arr.grid(True, alpha=0.3, linestyle='--')
                        ax_arr.legend(frameon=True, fontsize=10)
                        ax_arr.tick_params(labelsize=10)
                        plt.tight_layout()
                        
                        buf = io.BytesIO()
                        if sim_fig_fmt.lower() in ['bmp', 'tiff']:
                            buf_tmp = io.BytesIO()
                            fig_arr.savefig(buf_tmp, format='png', dpi=sim_fig_dpi, bbox_inches='tight')
                            buf_tmp.seek(0)
                            from PIL import Image
                            Image.open(buf_tmp).save(buf, format=sim_fig_fmt.upper())
                        else:
                            fig_arr.savefig(buf, format=sim_fig_fmt, dpi=sim_fig_dpi, bbox_inches='tight')
                        buf.seek(0)
                        st.download_button("⬇️ Download Arrhenius", buf, f"Simulation_Arrhenius.{sim_fig_fmt}", key="dl_sim_arr")
                        plt.close(fig_arr)
                    else:
                        st.warning("Need at least 3 temperatures for Arrhenius")



# ==========================
# TAB 4: COMPARISON
# ==========================
with tab_comparison:
    st.header("📊 Multi-Sample Kinetic Comparison")
    st.markdown("Compare Arrhenius kinetics across up to 6 different samples")
    
    # Initialize comparison session state
    if 'comparison_samples' not in st.session_state:
        st.session_state.comparison_samples = {}
    
    # Sample input interface
    st.subheader("Sample Input")
    col_help = st.info("💡 Add up to 6 samples with their own temperature-τ data. We'll calculate Ea, Tv, and R² for each.")
    
    # Create tabs for sample input
    sample_results = {}
    num_samples = min(6, len(st.session_state.comparison_samples) + 1)
    
    sample_tabs = st.tabs(["📌 Sample 1", "📌 Sample 2", "📌 Sample 3", "📌 Sample 4", "📌 Sample 5", "📌 Sample 6"])
    for sample_idx, sample_tab in enumerate(sample_tabs, start=1):
        sample_key = f"sample_{sample_idx}"
        
        with sample_tab:
            col_info, col_delete = st.columns([4, 1])
            
            with col_info:
                # Basic info
                col_name, col_tg, col_gp = st.columns(3)
                with col_name:
                    sample_name = st.text_input(f"Sample Name", value=st.session_state.comparison_samples.get(sample_key, {}).get('name', f'Sample {sample_idx}'), key=f"name_{sample_idx}", placeholder="e.g., Vitrimer_A")
                with col_tg:
                    tg_val = st.number_input(f"Tg (°C)", value=st.session_state.comparison_samples.get(sample_key, {}).get('tg', 50.0), key=f"tg_{sample_idx}")
                with col_gp:
                    gp_val = st.number_input(f"G' (MPa)", value=st.session_state.comparison_samples.get(sample_key, {}).get('g_prime', 1.0), key=f"gp_{sample_idx}")
                
                # Temperature-Tau data - SIMPLIFIED TEXT INPUT
                st.markdown("**Temperature (°C) vs τ (s)** - Enter as pairs, one per line:")
                st.caption("Example: `100, 1.5` (Temperature, Tau)")
                
                # Get existing data as text
                existing_data = st.session_state.comparison_samples.get(sample_key, {}).get('data', [])
                text_data = '\n'.join([f"{row.get('Temperature (°C)', 0)}, {row.get('τ (s)', 0)}" for row in existing_data]) if existing_data else ""
                
                data_input = st.text_area(
                    "Data pairs",
                    value=text_data,
                    height=100,
                    key=f"data_{sample_idx}",
                    label_visibility="collapsed",
                    placeholder="100, 1.5\n110, 0.5\n120, 0.2"
                )
                
                # Parse data from text input
                parsed_data = []
                try:
                    for line in data_input.strip().split('\n'):
                        if line.strip():
                            parts = line.split(',')
                            if len(parts) >= 2:
                                temp = float(parts[0].strip())
                                tau = float(parts[1].strip())
                                parsed_data.append({"Temperature (°C)": temp, "τ (s)": tau})
                except:
                    st.error(f"❌ Parse error in Sample {sample_idx}. Use format: temp, tau")
                
                # Store data in session state
                st.session_state.comparison_samples[sample_key] = {
                    'name': sample_name,
                    'tg': tg_val,
                    'g_prime': gp_val,
                    'data': parsed_data
                }
            
            with col_delete:
                if st.button("🗑️", key=f"delete_{sample_idx}", help="Clear sample"):
                    if sample_key in st.session_state.comparison_samples:
                        del st.session_state.comparison_samples[sample_key]
                    for k in [f"name_{sample_idx}", f"tg_{sample_idx}", f"gp_{sample_idx}", f"data_{sample_idx}"]:
                        if k in st.session_state:
                            del st.session_state[k]
                    if 'comparison_results' in st.session_state:
                        del st.session_state['comparison_results']
                    st.rerun()
    
    # Analysis button
    st.markdown("---")
    if st.button("🔍 Analyze All Samples", type="primary", width='stretch'):
        # Collect non-empty samples
        valid_samples = []
        for key, sample_data in st.session_state.comparison_samples.items():
            if sample_data.get('data') and len(sample_data['data']) >= 2:
                sd_copy = dict(sample_data)
                sd_copy['key'] = key
                valid_samples.append(sd_copy)
        
        if valid_samples:
            # Calculate Arrhenius for each sample
            results_list = []
            
            for sample in valid_samples:
                name = sample['name']
                tg = sample['tg']
                g_prime = sample['g_prime']
                data = sample['data']
                
                # Prepare data for fitting
                temps = []
                taus = []
                
                for row in data:
                    t_temp = row.get('Temperature (°C)', 0)
                    tau_val = row.get('τ (s)', 0)
                    
                    # Only include data above Tg
                    if t_temp > tg and tau_val > 0:
                        temps.append(t_temp)
                        taus.append(tau_val)
                
                if len(temps) >= 2:
                    # Convert to arrays
                    temps_arr = np.array(temps)
                    taus_arr = np.array(taus)
                    
                    # Prepare Arrhenius data
                    inv_T = 1000.0 / (temps_arr + 273.15)
                    ln_tau = np.log(taus_arr)
                    
                    # Fit Arrhenius
                    k_engine = KineticsEngine()
                    fit_res = k_engine.fit_arrhenius(temps, taus)
                    if fit_res:
                        slope = fit_res['Params']['slope'] / 1000.0
                        intercept = fit_res['Params']['intercept']
                        r_sq = fit_res['R2']
                        Ea = fit_res['Ea']
                    
                    # Validate: Ea should be positive (tau decreases with increasing T)
                    warning_msg = ""
                    if Ea < 0:
                        warning_msg = f"⚠️ {name}: Negative Ea ({Ea:.1f} kJ/mol) - Check data! τ should decrease with increasing T"
                    elif Ea < 10:
                        warning_msg = f"⚠️ {name}: Very low Ea ({Ea:.1f} kJ/mol) - Verify data quality"
                    
                    # Calculate Tv
                    G_Pa = g_prime * 1e6
                    tau_target = 1e12 / G_Pa
                    ln_tau_t = np.log(tau_target)
                    if slope != 0:
                        Tv_val = (1000.0 / ((ln_tau_t - intercept)/slope)) - 273.15
                    else:
                        Tv_val = 0
                    
                    results_list.append({
                        'Sample Name': name,
                        'sample_key': sample['key'],
                        'Tg (°C)': tg,
                        "G' (MPa)": g_prime,
                        'Ea (kJ/mol)': Ea,
                        'Ea_std (kJ/mol)': fit_res.get('Ea_std', 0),
                        'Tv (°C)': Tv_val,
                        'R²': r_sq,
                        'N_points': len(temps),
                        'inv_T': inv_T,
                        'warning': warning_msg,
                        'ln_tau': ln_tau,
                        'slope': slope,
                        'intercept': intercept,
                        'tau_target': tau_target,
                        'ln_tau_target': ln_tau_t
                    })
            
            if results_list:
                st.session_state.comparison_results = results_list
                st.success(f"✅ Analyzed {len(results_list)} samples")
            else:
                st.error("❌ No valid samples (need ≥2 points above Tg for each)")
        else:
            st.error("❌ Add samples with at least 2 data points each")
    
    # Display results
    if 'comparison_results' in st.session_state and st.session_state.comparison_results:
        results = st.session_state.comparison_results
        
        # Show warnings first
        for r in results:
            if r.get('warning'):
                orig_name = r['Sample Name']
                live_name = st.session_state.comparison_samples.get(r.get('sample_key'), {}).get('name', orig_name)
                warning_text = r['warning'].replace(orig_name, live_name)
                st.warning(warning_text)
        
        # Results table
        st.subheader("📊 Results Summary")
        gp_key = "G' (MPa)"
        results_df = pd.DataFrame([
            {
                'Sample Name': st.session_state.comparison_samples.get(r.get('sample_key'), {}).get('name', r['Sample Name']),
                "Tg (°C)": f"{r['Tg (°C)']:.1f}",
                "G' (MPa)": f"{r.get(gp_key, 0):.2f}",
                'Ea (kJ/mol)': f"{r['Ea (kJ/mol)']:.1f}",
                'Tv (°C)': f"{r['Tv (°C)']:.1f}",
                'R²': f"{r['R²']:.4f}",
                'Points': r['N_points']
            }
            for r in results
        ])
        
        st.dataframe(results_df, hide_index=True, width='stretch')
        
        # Download table
        csv_data = results_df.to_csv(index=False)
        st.download_button("📥 Download Results Table", csv_data, "comparison_results.csv", key="dl_comp_table")
        
        # Comparison plots
        st.subheader("📈 Arrhenius Comparison Plot")
        
        col_plot, col_settings = st.columns([3, 1])
        
        with col_settings:
            st.markdown("**Export Settings:**")
            comp_fmt = st.selectbox("Format", ["png", "jpeg", "bmp", "tiff", "pdf", "svg"], key="comp_fmt")
            comp_dpi = st.number_input("DPI", 72, 1200, 300, 50, key="comp_dpi")
            comp_colorspace = st.selectbox("Color Space Mode", ["RGB", "CMYK (for Print/Publication)"], key="comp_colorspace")
            
            with st.expander("📝 Legend Settings", expanded=False):
                show_comp_legend = st.checkbox("Show Legend", value=True, key="comp_legend")
                comp_leg_pos = st.selectbox("Position", ["best", "upper right", "upper left", "lower left", "lower right", "right (outside)"], key="comp_leg_pos")
                comp_leg_fontsize = st.slider("Font Size", 4, 20, 10, key="comp_leg_fontsize")
                comp_leg_box = st.checkbox("Box Border", value=True, key="comp_leg_box")
                comp_show_ea = st.checkbox("Show Ea ± std", value=False, key="comp_show_ea")

            with st.expander("📐 Figure Dimensions", expanded=True):
                comp_preset = st.selectbox("Journal Preset", [
                    "ACS/RSC Single-Column (85 x 75 mm)",
                    "ACS/RSC Double-Column (170 x 140 mm)",
                    "Custom"
                ], key="comp_preset")
                
                # Convert mm presets directly to cm
                if comp_preset == "ACS/RSC Single-Column (85 x 75 mm)":
                    default_width_cm, default_height_cm, disable_comp_size = 8.5, 7.5, True
                elif comp_preset == "ACS/RSC Double-Column (170 x 140 mm)":
                    default_width_cm, default_height_cm, disable_comp_size = 17.0, 14.0, True
                else:
                    default_width_cm, default_height_cm, disable_comp_size = 12.7, 10.0, False

                sz1, sz2 = st.columns(2)
                with sz1:
                    comp_width = st.number_input("Width (cm)", 1.0, 40.0, float(default_width_cm), 0.1, disabled=disable_comp_size, key="comp_w")
                with sz2:
                    comp_height = st.number_input("Height (cm)", 1.0, 40.0, float(default_height_cm), 0.1, disabled=disable_comp_size, key="comp_h")
                
                comp_panel_letter = st.text_input("Panel Letter", "", key="comp_panel")
                
                comp_panel_font_family = "Arial"
                comp_panel_font_size = 12
                comp_panel_font_weight = "bold"
                comp_panel_font_style = "normal"
                
                if comp_panel_letter:
                    st.markdown("**Panel Letter Font**")
                    pl1, pl2 = st.columns(2)
                    with pl1:
                        comp_panel_font_family = st.selectbox("Panel Font Family", ["Arial", "Times New Roman", "Courier New", "DejaVu Sans", "serif", "sans-serif", "monospace"], key="comp_panel_font_family")
                        comp_panel_font_weight = st.selectbox("Panel Font Weight", ["bold", "normal"], key="comp_panel_weight")
                    with pl2:
                        comp_panel_font_size = st.number_input("Panel Font Size", 4, 30, 12, key="comp_panel_size")
                        comp_panel_font_style = st.selectbox("Panel Font Style", ["normal", "italic"], key="comp_panel_style")

            # Style & Axes Settings
            with st.expander("🎨 Marker & Line Style", expanded=False):
                comp_lw = st.slider("Fit Line Width", 0.5, 6.0, 1.5, 0.5, key="comp_lw")
                comp_ms = st.slider("Data Marker Size", 1, 15, 6, 1, key="comp_ms")
                comp_show_tv = st.checkbox("Show Tv Star", value=True, key="comp_show_tv")
            
            with st.expander("🔤 Axis Typography", expanded=False):
                comp_font_family = st.selectbox("Font Family", ["Arial", "Times New Roman", "Courier New", "DejaVu Sans", "serif", "sans-serif", "monospace"], key="comp_font_family")
                
                st.markdown("**Axis Label Font**")
                comp_lbl_sz = st.number_input("Label Size", 4, 30, 10, key="comp_lbl_sz")
                comp_lbl_wt = st.selectbox("Label Weight", ["bold", "normal"], key="comp_lbl_wt")
                comp_lbl_sty = st.selectbox("Label Style", ["normal", "italic"], key="comp_lbl_sty")
                
                st.markdown("**Axis Number Font**")
                comp_tick_font = st.selectbox("Number Font", ["Same as Label", "Arial", "Times New Roman", "Courier New", "DejaVu Sans", "serif", "sans-serif", "monospace"], key="comp_tick_font")
                comp_tick_size = st.number_input("Number Size", 4, 30, 8, key="comp_tick_sz")
                comp_tick_weight = st.selectbox("Number Weight", ["normal", "bold"], key="comp_tick_wt")
                comp_tick_style = st.selectbox("Number Style", ["normal", "italic"], key="comp_tick_sty")

            with st.expander("📌 Tick Settings", expanded=False):
                comp_mirror = st.checkbox("Mirror Ticks to Top/Right", value=False, key="comp_mirror")
                comp_x_major = st.selectbox("X-Axis Major Ticks", ["Auto", "3", "4", "5", "6", "8", "10", "12", "15"], key="comp_x_major")
                comp_x_minor = st.selectbox("X-Axis Minor Ticks", ["Auto", "0", "1", "2", "3", "4", "5", "9"], key="comp_x_minor")
                comp_y_major = st.selectbox("Y-Axis Major Ticks", ["Auto", "3", "4", "5", "6", "8", "10", "12", "15"], key="comp_y_major")
                comp_y_minor = st.selectbox("Y-Axis Minor Ticks", ["Auto", "0", "1", "2", "3", "4", "5", "9"], key="comp_y_minor")

            with st.expander("📐 Axis Limits", expanded=False):
                comp_custom_lims = st.checkbox("Manual Axis Bounding", value=False, key="comp_custom_lims")
                all_inv_T = np.concatenate([r['inv_T'] for r in results])
                all_ln_tau = np.concatenate([r['ln_tau'] for r in results])
                comp_auto_xmin = float(all_inv_T.min() * 0.95)
                comp_auto_xmax = float(all_inv_T.max() * 1.05)
                comp_auto_ymin = float(all_ln_tau.min() - 0.5)
                comp_auto_ymax = float(all_ln_tau.max() + 0.5)
                
                if comp_custom_lims:
                    comp_xmin = st.number_input("X Min (1000/T)", value=comp_auto_xmin, format="%.4f", key="comp_xmin")
                    comp_xmax = st.number_input("X Max (1000/T)", value=comp_auto_xmax, format="%.4f", key="comp_xmax")
                    comp_ymin = st.number_input("Y Min (ln(\u03c4))", value=comp_auto_ymin, format="%.4f", key="comp_ymin")
                    comp_ymax = st.number_input("Y Max (ln(\u03c4))", value=comp_auto_ymax, format="%.4f", key="comp_ymax")
        
        # --- Pre-generate Matplotlib comparison figure ---
        fig_mpl = plt.figure(figsize=(comp_width / 2.54, comp_height / 2.54), facecolor='white')
        ax_mpl = fig_mpl.add_subplot(111)
        ax_mpl.set_facecolor('white')
        ax_mpl.grid(False)
        for spine in ['top', 'bottom', 'left', 'right']:
            ax_mpl.spines[spine].set_linewidth(1.0)
            ax_mpl.spines[spine].set_color('black')
        
        ax_mpl.tick_params(axis='both', which='major', labelsize=comp_tick_size, width=1.0, length=4, direction='in', color='black', top=comp_mirror, right=comp_mirror)
        ax_mpl.tick_params(axis='both', which='minor', width=0.8, length=2.5, direction='in', color='black', top=comp_mirror, right=comp_mirror)
        
        # Apply tick locator settings
        import matplotlib.ticker as ticker
        # X-Axis Ticks
        if comp_x_major != "Auto":
            ax_mpl.xaxis.set_major_locator(ticker.MaxNLocator(nbins=int(comp_x_major)))
        if comp_x_minor != "Auto":
            if int(comp_x_minor) == 0:
                ax_mpl.xaxis.set_minor_locator(ticker.NullLocator())
            else:
                ax_mpl.xaxis.set_minor_locator(ticker.AutoMinorLocator(n=int(comp_x_minor)+1))
        else:
            ax_mpl.xaxis.set_minor_locator(ticker.AutoMinorLocator())
        
        # Y-Axis Ticks
        if comp_y_major != "Auto":
            ax_mpl.yaxis.set_major_locator(ticker.MaxNLocator(nbins=int(comp_y_major)))
        if comp_y_minor != "Auto":
            if int(comp_y_minor) == 0:
                ax_mpl.yaxis.set_minor_locator(ticker.NullLocator())
            else:
                ax_mpl.yaxis.set_minor_locator(ticker.AutoMinorLocator(n=int(comp_y_minor)+1))
        else:
            ax_mpl.yaxis.set_minor_locator(ticker.AutoMinorLocator())
        
        colors_mpl = ['#EF553B', '#636EFA', '#00CC96', '#AB63FA', '#FFA15A', '#25D098']
        
        for idx, r in enumerate(results):
            inv_T = r['inv_T']
            ln_tau = r['ln_tau']
            name = st.session_state.comparison_samples.get(r.get('sample_key'), {}).get('name', r['Sample Name'])
            slope = r['slope']
            intercept = r['intercept']
            Ea = r['Ea (kJ/mol)']
            tau_target = r['tau_target']
            ln_tau_target = r['ln_tau_target']
            
            if comp_show_ea:
                ea_std = r.get('Ea_std (kJ/mol)', 0)
                name = f"{name} ({Ea:.1f} +/- {ea_std:.1f} kJ/mol)"
            
            color = colors_mpl[idx % len(colors_mpl)]
            
            # Plot data
            ax_mpl.scatter(inv_T, ln_tau, s=comp_ms**2, alpha=0.7, edgecolors='black', linewidth=0.8,
                         label=name, color=color, zorder=3)
            
            # Plot fit line
            x_range = np.linspace(inv_T.min() * 0.9, inv_T.max() * 1.1, 50)
            y_fit = slope * x_range + intercept
            ax_mpl.plot(x_range, y_fit, '--', color=color, linewidth=comp_lw, alpha=0.8, zorder=2)
            
            # Plot Tv marker
            if comp_show_tv:
                tv_x = (ln_tau_target - intercept) / slope
                ax_mpl.plot([tv_x], [ln_tau_target], marker='*', markersize=comp_ms*2, color=color,
                          markeredgecolor='black', markeredgewidth=1.0, zorder=4)
        
        # Label font dictionary
        font_label_comp = {
            'family': comp_font_family,
            'size': comp_lbl_sz,
            'weight': comp_lbl_wt,
            'style': comp_lbl_sty
        }
        ax_mpl.set_xlabel(r"$1000/T$ ($\mathrm{K}^{-1}$)", fontdict=font_label_comp, labelpad=8)
        ax_mpl.set_ylabel(r"$\ln(\tau)$", fontdict=font_label_comp, labelpad=8)
        
        # Apply axis limits
        if comp_custom_lims:
            ax_mpl.set_xlim(comp_xmin, comp_xmax)
            ax_mpl.set_ylim(comp_ymin, comp_ymax)
        else:
            all_inv_T = np.concatenate([r['inv_T'] for r in results])
            all_ln_tau = np.concatenate([r['ln_tau'] for r in results])
            ax_mpl.set_xlim(all_inv_T.min() * 0.95, all_inv_T.max() * 1.05)
            ax_mpl.set_ylim(all_ln_tau.min() - 0.5, all_ln_tau.max() + 0.5)

        # Apply tick number fonts
        comp_num_family = comp_font_family if comp_tick_font == "Same as Label" else comp_tick_font
        for label in ax_mpl.get_xticklabels():
            label.set_family(comp_num_family)
            label.set_size(comp_tick_size)
            label.set_weight(comp_tick_weight)
            label.set_style(comp_tick_style)
        for label in ax_mpl.get_yticklabels():
            label.set_family(comp_num_family)
            label.set_size(comp_tick_size)
            label.set_weight(comp_tick_weight)
            label.set_style(comp_tick_style)
        
        if show_comp_legend:
            if comp_leg_pos == "right (outside)":
                ax_mpl.legend(frameon=comp_leg_box, fontsize=comp_leg_fontsize, bbox_to_anchor=(1.05, 1), loc='upper left')
            else:
                ax_mpl.legend(frameon=comp_leg_box, fontsize=comp_leg_fontsize, loc=comp_leg_pos)

        if comp_panel_letter:
            ax_mpl.text(-0.12, 1.02, f"({comp_panel_letter})", transform=ax_mpl.transAxes,
                     fontfamily=comp_panel_font_family, fontsize=comp_panel_font_size,
                     fontweight=comp_panel_font_weight, fontstyle=comp_panel_font_style,
                     va='bottom', ha='right')
        
        mpl_success = False
        try:
            plt.tight_layout()
            
            # Save figure to memory bytes for download
            if comp_colorspace.startswith("CMYK"):
                buf_rgb_png = io.BytesIO()
                fig_mpl.savefig(buf_rgb_png, format='png', dpi=1200, bbox_inches='tight')
                buf_rgb_png.seek(0)
                from PIL import Image
                img = Image.open(buf_rgb_png)
                img_cmyk = img.convert('CMYK')
                buf_export = io.BytesIO()
                img_cmyk.save(buf_export, format='pdf')
                buf_export.seek(0)
                dl_filename = "Arrhenius_Comparison_CMYK.pdf"
                dl_mime = "application/pdf"
                btn_label = "⬇️ Download Comparison Figure (CMYK PDF)"
            else:
                buf_export = io.BytesIO()
                fmt_lower = comp_fmt.lower()
                if fmt_lower in ['bmp', 'tiff']:
                    buf_tmp = io.BytesIO()
                    fig_mpl.savefig(buf_tmp, format='png', dpi=comp_dpi, bbox_inches='tight')
                    buf_tmp.seek(0)
                    from PIL import Image
                    Image.open(buf_tmp).save(buf_export, format=fmt_lower.upper())
                else:
                    fig_mpl.savefig(buf_export, format=fmt_lower, dpi=comp_dpi, bbox_inches='tight')
                buf_export.seek(0)
                dl_filename = f"Arrhenius_Comparison.{fmt_lower}"
                dl_mime = f"image/{fmt_lower}" if fmt_lower != "pdf" else "application/pdf"
                btn_label = f"⬇️ Download Comparison Figure ({comp_fmt})"
            
            # Add the download button to col_settings
            with col_settings:
                st.download_button(btn_label, buf_export, dl_filename, mime=dl_mime, key="dl_comp_plot")
            
            mpl_success = True
        except Exception as e:
            with col_settings:
                st.error(f"⚠️ Matplotlib export failed. Check for invalid MathText in Sample Names (e.g. unclosed '$').")

        # Render the plot in col_plot
        with col_plot:
            comp_plot_mode = st.radio("Plot Type", ["Interactive Plot (Plotly)", "Publication Figure Preview (Matplotlib)"], horizontal=True, key="comp_plot_mode")
            if comp_plot_mode == "Interactive Plot (Plotly)":
                fig_comp = go.Figure()
                
                # Color palette for up to 6 samples
                colors = ['#EF553B', '#636EFA', '#00CC96', '#AB63FA', '#FFA15A', '#25D098']
                
                for idx, r in enumerate(results):
                    inv_T = r['inv_T']
                    ln_tau = r['ln_tau']
                    name = st.session_state.comparison_samples.get(r.get('sample_key'), {}).get('name', r['Sample Name'])
                    Ea = r['Ea (kJ/mol)']
                    slope = r['slope']
                    intercept = r['intercept']
                    tau_target = r['tau_target']
                    ln_tau_target = r['ln_tau_target']
                    
                    color = colors[idx % 6]
                    
                    # Data points
                    fig_comp.add_trace(go.Scatter(
                        x=inv_T,
                        y=ln_tau,
                        mode='markers',
                        name=name,
                        marker=dict(size=8, color=color, opacity=0.8, line=dict(width=1, color='rgba(0,0,0,0.5)')),
                        hovertemplate=f"<b>{name}</b><br>1000/T: %{{x:.3f}}<br>ln(τ): %{{y:.2f}}<extra></extra>"
                    ))
                    
                    # Fit line
                    x_range = np.linspace(inv_T.min() * 0.9, inv_T.max() * 1.1, 50)
                    y_fit = slope * x_range + intercept
                    fig_comp.add_trace(go.Scatter(
                        x=x_range,
                        y=y_fit,
                        mode='lines',
                        name=f"{name} fit",
                        line=dict(color=color, dash='dash', width=2),
                        showlegend=False,
                        hoverinfo='skip'
                    ))
                    
                    # Tv marker (star)
                    tv_x = (ln_tau_target - intercept) / slope
                    fig_comp.add_trace(go.Scatter(
                        x=[tv_x],
                        y=[ln_tau_target],
                        mode='markers',
                        marker=dict(size=14, symbol='star', color=color, line=dict(width=2, color='black')),
                        name=f"{name} Tv",
                        showlegend=False,
                        hovertemplate=f"<b>{name} Tv</b><br>1000/T: %{{x:.3f}}<br>ln(τ): %{{y:.2f}}<extra></extra>"
                    ))
                
                pos_map = {
                    "upper right": dict(x=0.98, y=0.98, xanchor="right", yanchor="top"),
                    "upper left": dict(x=0.02, y=0.98, xanchor="left", yanchor="top"),
                    "lower left": dict(x=0.02, y=0.02, xanchor="left", yanchor="bottom"),
                    "lower right": dict(x=0.98, y=0.02, xanchor="right", yanchor="bottom"),
                    "right (outside)": dict(x=1.05, y=1, xanchor="left", yanchor="top"),
                    "best": dict(x=0.02, y=0.98, xanchor="left", yanchor="top")
                }
                plotly_leg = dict(
                    bgcolor='rgba(255,255,255,0.8)' if comp_leg_box else 'rgba(0,0,0,0)',
                    borderwidth=1 if comp_leg_box else 0,
                    font=dict(size=comp_leg_fontsize)
                )
                plotly_leg.update(pos_map.get(comp_leg_pos, pos_map["best"]))
                
                fig_comp.update_layout(
                    title="Arrhenius Comparison: Multiple Samples",
                    xaxis_title="1000/T (K<sup>-1</sup>)",
                    yaxis_title="ln(τ)",
                    height=500,
                    hovermode='closest',
                    showlegend=show_comp_legend,
                    legend=plotly_leg,
                    margin=dict(l=60, r=20, t=50, b=50)
                )
                
                if comp_panel_letter:
                    p_text = f"({comp_panel_letter})"
                    if comp_panel_font_weight == "bold": p_text = f"<b>{p_text}</b>"
                    if comp_panel_font_style == "italic": p_text = f"<i>{p_text}</i>"
                    fig_comp.add_annotation(
                        x=-0.12, y=1.02,
                        xref="paper", yref="paper",
                        text=p_text,
                        showarrow=False,
                        font=dict(
                            family=comp_panel_font_family,
                            size=comp_panel_font_size,
                            color="black"
                        ),
                        xanchor="right", yanchor="bottom"
                    )
                
                st.plotly_chart(fig_comp, width='stretch')
            else:
                if mpl_success:
                    try:
                        st.pyplot(fig_mpl, dpi=300, bbox_inches='tight')
                    except Exception as e:
                        st.error(f"⚠️ Matplotlib render failed. Check Sample Names for invalid MathText. Error: {e}")
                else:
                    st.error("⚠️ Matplotlib preview unavailable due to invalid MathText in labels.")
        
        plt.close(fig_mpl)
    else:
        st.info("👈 Fill in samples and click 'Analyze All Samples' to start comparison")

# ==========================
# TAB 5: PUBLICATION
# ==========================
with tab_pub:
    st.header("\U0001f4dd Publication Figures")
    if 'active_results' in st.session_state and st.session_state.active_results:
        active_res = st.session_state.active_results
        kinetics_df = st.session_state.get('kinetics_df', pd.DataFrame())

        # Pre-calculate auto bounds for default input values
        x_unit_sel_temp = st.session_state.get('pub_xunit', 'Seconds (s)')
        y_norm_sel_temp = st.session_state.get('pub_ynorm', 'Normalized (G/G\u2080 or E/E\u2080)')

        if x_unit_sel_temp == "Minutes (min)":
            x_factor_temp = 60.0
        elif x_unit_sel_temp == "Hours (h)":
            x_factor_temp = 3600.0
        else:
            x_factor_temp = 1.0

        all_times_temp = np.concatenate([r['Raw']['t'] / x_factor_temp for r in active_res])
        auto_rel_xmin = float(all_times_temp.min() * 0.8)
        auto_rel_xmax = float(all_times_temp.max() * 1.2)

        is_norm_temp = y_norm_sel_temp.startswith("Normal")
        if is_norm_temp:
            auto_rel_ymin = 0.0
            auto_rel_ymax = 1.05
        else:
            max_y_temp = max([np.max(r['Raw']['g'] * r['Raw'].get('G0', 1.0)) for r in active_res])
            auto_rel_ymin = 0.0
            auto_rel_ymax = float(max_y_temp * 1.05)

        # Pre-calculate auto bounds for Kinetics Plot
        # These are model-agnostic (always derived from 1000/T, updated per-model below)
        if not kinetics_df.empty:
            active_k_temp = kinetics_df[kinetics_df['Include']==True]
            if not active_k_temp.empty and len(active_k_temp) >= 2:
                auto_kin_xmin = float(active_k_temp['1000/T'].min() * 0.95)
                auto_kin_xmax = float(active_k_temp['1000/T'].max() * 1.05)
                auto_kin_ymin = float(active_k_temp['ln(Tau)'].min() - 0.5)
                auto_kin_ymax = float(active_k_temp['ln(Tau)'].max() + 0.5)
            else:
                auto_kin_xmin, auto_kin_xmax, auto_kin_ymin, auto_kin_ymax = 2.0, 3.5, -2.0, 10.0
        else:
            auto_kin_xmin, auto_kin_xmax, auto_kin_ymin, auto_kin_ymax = 2.0, 3.5, -2.0, 10.0

        # ── Two-panel: Settings LEFT | Previews RIGHT ──────────────────
        pan_settings, pan_preview = st.columns([1, 2], gap="large")

        with pan_settings:
            st.markdown("### \u2699\ufe0f Settings")

            # ── 1. Figure Dimensions & Panel ─────────────────────────
            with st.expander("📐 Figure Dimensions & Panel", expanded=True):
                fig_preset = st.selectbox("Journal Preset", [
                    "ACS/RSC Single-Column (85 x 75 mm)",
                    "ACS/RSC Double-Column (170 x 140 mm)",
                    "Custom"
                ], key="pub_preset")
                if fig_preset == "ACS/RSC Single-Column (85 x 75 mm)":
                    default_width, default_height, disable_size = 8.5, 7.5, True
                elif fig_preset == "ACS/RSC Double-Column (170 x 140 mm)":
                    default_width, default_height, disable_size = 17.0, 14.0, True
                else:
                    default_width, default_height, disable_size = 12.7, 10.0, False

                sz1, sz2 = st.columns(2)
                with sz1:
                    fig_width = st.number_input("Width (cm)", 1.0, 40.0, float(default_width), 0.1, disabled=disable_size, key="pub_w")
                with sz2:
                    fig_height = st.number_input("Height (cm)", 1.0, 40.0, float(default_height), 0.1, disabled=disable_size, key="pub_h")
                panel_letter = st.text_input("First Panel Letter", "a", key="pub_panel")
                
                # Panel Letter Font Settings
                panel_font_family = "Arial"
                panel_font_size = 12
                panel_font_weight = "bold"
                panel_font_style = "normal"
                
                if panel_letter:
                    st.markdown("**Panel Letter Font**")
                    pl1, pl2 = st.columns(2)
                    with pl1:
                        panel_font_family = st.selectbox("Panel Font Family", ["Arial", "Times New Roman", "Courier New", "DejaVu Sans", "serif", "sans-serif", "monospace"], key="pub_panel_font_family")
                        panel_font_weight = st.selectbox("Panel Font Weight", ["bold", "normal"], key="pub_panel_weight")
                    with pl2:
                        panel_font_size = st.number_input("Panel Font Size", 4, 30, 12, key="pub_panel_size")
                        panel_font_style = st.selectbox("Panel Font Style", ["normal", "italic"], key="pub_panel_style")
                
                pub_colorspace = st.selectbox("Color Space Mode", ["RGB", "CMYK (for Print/Publication)"], key="pub_colorspace")

            # ── 2. Relaxation Plot: Style & Axes ─────────────────────────
            with st.expander("📈 Relaxation Plot: Style & Axes", expanded=False):
                y_label_select = st.selectbox("Modulus Notation", ["G (Shear Modulus)", "E (Tensile Modulus)"], key="pub_ylabel")
                y_norm_select = st.selectbox("Normalization", ["Normalized (G/G₀ or E/E₀)", "Non-Normalized (G or E)"], key="pub_ynorm")
                curve_style = st.selectbox("Data Style", ["Continuous Lines (Raw)", "Markers Only", "Lines + Markers"], key="pub_style")

                st.markdown("---")
                ax1c, ax2c, ax3c = st.columns(3)
                with ax1c:
                    pub_time_axis = st.selectbox("Time Scale", ["Log", "Linear"], key="pub_xscale")
                with ax2c:
                    pub_y_scale = st.selectbox("Y-Axis Scale", ["Linear", "Log"], key="pub_yscale")
                with ax3c:
                    x_unit_select = st.selectbox("Time Unit", ["Seconds (s)", "Minutes (min)", "Hours (h)"], key="pub_xunit")

                st.markdown("---")
                chk1, chk2, chk3 = st.columns(3)
                with chk1:
                    show_fit_pub = st.checkbox("Fits", value=False, key="pub_showfit")
                with chk2:
                    show_tau_star = st.checkbox("\u03c4* mark", value=True, key="pub_taustar")
                with chk3:
                    annotate_tau_star = st.checkbox("\u03c4* label", value=False, key="pub_taulabel")

                st.markdown("##### 🎨 Marker & Line Style")
                rc1, rc2, rc3 = st.columns(3)
                with rc1:
                    rel_line_width = st.slider("Line Width", 0.5, 6.0, 1.5, 0.5, key="pub_rel_lw")
                with rc2:
                    rel_marker_size = st.slider("Marker Size", 1, 15, 4, 1, key="pub_rel_ms")
                with rc3:
                    rel_marker_density = st.slider("Marker Density (%)", 0, 100, 20, 5, key="pub_rel_md")

                st.markdown("##### 🔤 Axis Typography")
                rel_font_family = st.selectbox("Font Family", ["Arial", "Times New Roman", "Courier New", "DejaVu Sans", "serif", "sans-serif", "monospace"], key="pub_relfont_family")
                
                st.markdown("**Axis Label Font**")
                rls1, rls2, rls3 = st.columns(3)
                with rls1:
                    rel_label_size = st.number_input("Label Size", 4, 30, 10, key="pub_rel_lbl_sz")
                with rls2:
                    rel_label_weight = st.selectbox("Label Weight", ["bold", "normal"], key="pub_rel_lbl_wt")
                with rls3:
                    rel_label_style = st.selectbox("Label Style", ["normal", "italic"], key="pub_rel_lbl_sty")
                
                st.markdown("**Axis Number Font**")
                rns1, rns2, rns3, rns4 = st.columns(4)
                with rns1:
                    rel_tick_font = st.selectbox("Number Font", ["Same as Label", "Arial", "Times New Roman", "Courier New", "DejaVu Sans", "serif", "sans-serif", "monospace"], key="pub_rel_num_font")
                with rns2:
                    rel_tick_size = st.number_input("Number Size", 4, 30, 8, key="pub_rel_num_sz")
                with rns3:
                    rel_tick_weight = st.selectbox("Number Weight", ["normal", "bold"], key="pub_rel_num_wt")
                with rns4:
                    rel_tick_style = st.selectbox("Number Style", ["normal", "italic"], key="pub_rel_num_sty")

                st.markdown("##### 📌 Tick Settings")
                rel_mirror = st.checkbox("Mirror Ticks to Top/Right", value=False, key="pub_rel_mirror")

                st.markdown("##### 📐 Axis Limits")
                rel_custom_lims = st.checkbox("Manual Axis Bounding", value=False, key="pub_rel_cust_lims")
                if rel_custom_lims:
                    xlim_col1, xlim_col2 = st.columns(2)
                    ylim_col1, ylim_col2 = st.columns(2)
                    with xlim_col1:
                        rel_xmin = st.number_input("X Min (Time)", value=auto_rel_xmin, format="%.3e", key="pub_rel_xmin")
                    with xlim_col2:
                        rel_xmax = st.number_input("X Max (Time)", value=auto_rel_xmax, format="%.3e", key="pub_rel_xmax")
                    with ylim_col1:
                        rel_ymin = st.number_input("Y Min (Modulus)", value=auto_rel_ymin, format="%.3e", key="pub_rel_ymin")
                    with ylim_col2:
                        rel_ymax = st.number_input("Y Max (Modulus)", value=auto_rel_ymax, format="%.3e", key="pub_rel_ymax")

            # ── 3. Kinetics Plot: Style & Axes ───────────────────────────
            with st.expander("🔥 Kinetics Plot: Style & Axes", expanded=False):
                # Model selector — mirrors the Analysis tab choice
                default_kin_model = st.session_state.get('kinetics_model_type', 'Arrhenius')
                pub_kin_model = st.selectbox(
                    "Kinetics Model",
                    ["Arrhenius", "VFT", "Eyring (Transition State)",
                     "Van 't Hoff (Decrosslinking)", "Coupled WLF-Arrhenius"],
                    index=["Arrhenius", "VFT", "Eyring (Transition State)",
                           "Van 't Hoff (Decrosslinking)", "Coupled WLF-Arrhenius"].index(default_kin_model)
                    if default_kin_model in ["Arrhenius", "VFT", "Eyring (Transition State)",
                                             "Van 't Hoff (Decrosslinking)", "Coupled WLF-Arrhenius"]
                    else 0,
                    key="pub_kin_model"
                )

                chk4, chk5 = st.columns(2)
                with chk4:
                    show_tv = st.checkbox("Show T\u1d65", value=True, key="pub_showtv",
                                         disabled=(pub_kin_model != "Arrhenius"))
                with chk5:
                    show_ea_std = st.checkbox("Ea \u00b1 std", value=True, key="pub_eastd",
                                             disabled=(pub_kin_model not in ["Arrhenius", "Eyring (Transition State)"]))
                
                st.markdown("##### 🎨 Marker & Line Style")
                kc1, kc2 = st.columns(2)
                with kc1:
                    kin_line_width = st.slider("Fit Line Width", 0.5, 6.0, 1.5, 0.5, key="pub_kin_lw")
                with kc2:
                    kin_marker_size = st.slider("Data Marker Size", 1, 15, 6, 1, key="pub_kin_ms")
                
                st.markdown("##### 🔤 Axis Typography")
                kin_font_family = st.selectbox("Font Family ", ["Arial", "Times New Roman", "Courier New", "DejaVu Sans", "serif", "sans-serif", "monospace"], key="pub_kinfont_family")
                
                st.markdown("**Axis Label Font**")
                kls1, kls2, kls3 = st.columns(3)
                with kls1:
                    kin_label_size = st.number_input("Label Size ", 4, 30, 10, key="pub_kin_lbl_sz")
                with kls2:
                    kin_label_weight = st.selectbox("Label Weight ", ["bold", "normal"], key="pub_kin_lbl_wt")
                with kls3:
                    kin_label_style = st.selectbox("Label Style ", ["normal", "italic"], key="pub_kin_lbl_sty")
                
                st.markdown("**Axis Number Font**")
                kns1, kns2, kns3, kns4 = st.columns(4)
                with kns1:
                    kin_tick_font = st.selectbox("Number Font ", ["Same as Label", "Arial", "Times New Roman", "Courier New", "DejaVu Sans", "serif", "sans-serif", "monospace"], key="pub_kin_num_font")
                with kns2:
                    kin_tick_size = st.number_input("Number Size ", 4, 30, 8, key="pub_kin_num_sz")
                with kns3:
                    kin_tick_weight = st.selectbox("Number Weight ", ["normal", "bold"], key="pub_kin_num_wt")
                with kns4:
                    kin_tick_style = st.selectbox("Number Style ", ["normal", "italic"], key="pub_kin_num_sty")

                st.markdown("##### 📌 Tick Settings")
                kin_mirror = st.checkbox("Mirror Ticks to Top/Right", value=False, key="pub_kin_mirror")
                ktc1, ktc2 = st.columns(2)
                with ktc1:
                    kin_x_major = st.selectbox("X-Axis Major Ticks ", ["Auto", "3", "4", "5", "6", "8", "10", "12", "15"], key="pub_kin_x_major")
                    kin_x_minor = st.selectbox("X-Axis Minor Ticks ", ["Auto", "0", "1", "2", "3", "4", "5", "9"], key="pub_kin_x_minor")
                with ktc2:
                    kin_y_major = st.selectbox("Y-Axis Major Ticks ", ["Auto", "3", "4", "5", "6", "8", "10", "12", "15"], key="pub_kin_y_major")
                    kin_y_minor = st.selectbox("Y-Axis Minor Ticks ", ["Auto", "0", "1", "2", "3", "4", "5", "9"], key="pub_kin_y_minor")

                st.markdown("##### 📐 Axis Limits")
                kin_custom_lims = st.checkbox("Manual Axis Bounding ", value=False, key="pub_kin_cust_lims")
                if kin_custom_lims:
                    kxlim_col1, kxlim_col2 = st.columns(2)
                    kylim_col1, kylim_col2 = st.columns(2)
                    with kxlim_col1:
                        kin_xmin = st.number_input("X Min (1000/T)", value=auto_kin_xmin, format="%.4f", key="pub_kin_xmin")
                    with kxlim_col2:
                        kin_xmax = st.number_input("X Max (1000/T)", value=auto_kin_xmax, format="%.4f", key="pub_kin_xmax")
                    with kylim_col1:
                        kin_ymin = st.number_input("Y Min (ln(\u03c4))", value=auto_kin_ymin, format="%.4f", key="pub_kin_ymin")
                    with kylim_col2:
                        kin_ymax = st.number_input("Y Max (ln(\u03c4))", value=auto_kin_ymax, format="%.4f", key="pub_kin_ymax")

            # ── 2. Relaxation Legend ──────────────────────────────────
            with st.expander("\U0001f5fa Relaxation Legend", expanded=False):
                show_rel_leg = st.checkbox("Show Legend", value=True, key="pub_relleg")
                if show_rel_leg:
                    rel_leg_pos = st.selectbox("Position", [
                        "Best (Auto)", "Upper Right", "Upper Left", "Lower Left", "Lower Right",
                        "Right (Outside)", "Above the Plot (Horizontal)", "Below the Plot (Horizontal)", "Custom (Coords)"
                    ], key="pub_relpos")
                    if rel_leg_pos == "Custom (Coords)":
                        rlc1, rlc2 = st.columns(2)
                        with rlc1:
                            rel_leg_x = st.slider("X", -0.5, 1.5, 1.0, 0.02, key="pub_relx")
                        with rlc2:
                            rel_leg_y = st.slider("Y", -0.5, 1.5, 1.0, 0.02, key="pub_rely")
                        rel_leg_anchor = st.selectbox("Anchor", ["upper left", "upper center", "upper right", "lower left", "lower center", "lower right", "center"], key="pub_relanch")
                    else:
                        rel_leg_x, rel_leg_y, rel_leg_anchor = 1.0, 1.0, "upper left"
                    default_rel_ncol = len(active_res) if "Horizontal" in rel_leg_pos else 1
                    rnc1, rnc2 = st.columns(2)
                    with rnc1:
                        rel_leg_ncol = st.number_input("Columns", 1, 10, default_rel_ncol, key="pub_relncol")
                    with rnc2:
                        rel_leg_font_size = st.slider("Font Size", 4, 16, 8, key="pub_relfont")
                    rel_leg_box = st.checkbox("Box Border", value=False, key="pub_relbox")
                else:
                    rel_leg_pos, rel_leg_font_size, rel_leg_box = "Best (Auto)", 8, False
                    rel_leg_x, rel_leg_y, rel_leg_ncol, rel_leg_anchor = 1.0, 1.0, 1, "upper left"

            # ── 3. Kinetics Legend ────────────────────────────────────
            with st.expander("\U0001f5fa Kinetics Legend", expanded=False):
                show_kin_leg = st.checkbox("Show Legend ", value=True, key="pub_kinleg")
                if show_kin_leg:
                    kin_leg_pos = st.selectbox("Position ", [
                        "Best (Auto)", "Upper Right", "Upper Left", "Lower Left", "Lower Right",
                        "Right (Outside)", "Above the Plot (Horizontal)", "Below the Plot (Horizontal)", "Custom (Coords)"
                    ], key="pub_kinpos")
                    if kin_leg_pos == "Custom (Coords)":
                        klc1, klc2 = st.columns(2)
                        with klc1:
                            kin_leg_x = st.slider("X ", -0.5, 1.5, 1.0, 0.02, key="pub_kinx")
                        with klc2:
                            kin_leg_y = st.slider("Y ", -0.5, 1.5, 1.0, 0.02, key="pub_kiny")
                        kin_leg_anchor = st.selectbox("Anchor ", ["upper left", "upper center", "upper right", "lower left", "lower center", "lower right", "center"], key="pub_kinanch")
                    else:
                        kin_leg_x, kin_leg_y, kin_leg_anchor = 1.0, 1.0, "upper left"
                    default_kin_ncol = 3 if "Horizontal" in kin_leg_pos else 1
                    knc1, knc2 = st.columns(2)
                    with knc1:
                        kin_leg_ncol = st.number_input("Columns ", 1, 10, default_kin_ncol, key="pub_kinncol")
                    with knc2:
                        kin_leg_font_size = st.slider("Font Size ", 4, 16, 8, key="pub_kinfont")
                    kin_leg_box = st.checkbox("Box Border ", value=False, key="pub_kinbox")
                else:
                    kin_leg_pos, kin_leg_font_size, kin_leg_box = "Best (Auto)", 8, False
                    kin_leg_x, kin_leg_y, kin_leg_ncol, kin_leg_anchor = 1.0, 1.0, 1, "upper left"

        # ── Right panel: figure previews ──────────────────────────────
        with pan_preview:
            color_palette = ['#1b9e77', '#d95f02', '#7570b3', '#e7298a', '#66a61e', '#e6ab02', '#a6761d', '#666666']

            # ════ FIGURE 1: RELAXATION CURVES ════
            st.subheader("\U0001f4ca Relaxation Curves")
            fig1, ax1 = plt.subplots(figsize=(fig_width / 2.54, fig_height / 2.54), facecolor='white')
            ax1.set_facecolor('white')
            ax1.grid(False)
            for spine in ['top', 'bottom', 'left', 'right']:
                ax1.spines[spine].set_linewidth(1.0)
                ax1.spines[spine].set_color('black')
            ax1.tick_params(axis='both', which='major', labelsize=rel_tick_size, width=1.0, length=4, direction='in', color='black', top=rel_mirror, right=rel_mirror)
            ax1.tick_params(axis='both', which='minor', width=0.8, length=2.5, direction='in', color='black', top=rel_mirror, right=rel_mirror)

            # Apply tick locator settings
            # X-Axis Ticks
            if pub_time_axis != "Log":
                ax1.xaxis.set_minor_locator(ticker.AutoMinorLocator())
            else: # Log scale
                ax1.xaxis.set_major_locator(ticker.LogLocator(base=10.0))
                ax1.xaxis.set_minor_locator(ticker.LogLocator(base=10.0, subs=(2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0)))
            
            # Y-Axis Ticks
            if pub_y_scale != "Log":
                ax1.yaxis.set_minor_locator(ticker.AutoMinorLocator())
            else: # Log scale
                ax1.yaxis.set_major_locator(ticker.LogLocator(base=10.0))
                ax1.yaxis.set_minor_locator(ticker.LogLocator(base=10.0, subs=(2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0)))


            font_label_rel = {
                'family': rel_font_family,
                'size': rel_label_size,
                'weight': rel_label_weight,
                'style': rel_label_style
            }

            if x_unit_select == "Minutes (min)":
                x_factor, x_label = 60.0, "min"
            elif x_unit_select == "Hours (h)":
                x_factor, x_label = 3600.0, "h"
            else:
                x_factor, x_label = 1.0, "s"

            is_normalized = y_norm_select.startswith("Normal")
            if is_normalized:
                y_label_text = r"$G(t) / G_0$" if y_label_select.startswith("G") else r"$E(t) / E_0$"
            else:
                y_label_text = r"$G(t)$ (MPa)" if y_label_select.startswith("G") else r"$E(t)$ (MPa)"

            for idx, r in enumerate(active_res):
                t_raw = r['Raw']['t']
                g_norm = r['Raw']['g']
                G0 = r['Raw'].get('G0', 1.0)
                t_plot = t_raw / x_factor
                g_plot = g_norm if is_normalized else g_norm * G0
                color = color_palette[idx % len(color_palette)]
                label_name = f"{r['Temp']}\u00b0C"

                if curve_style == "Continuous Lines (Raw)":
                    ax1.plot(t_plot, g_plot, '-', linewidth=rel_line_width, color=color, label=label_name)
                elif curve_style == "Markers Only":
                    if rel_marker_density > 0:
                        step = max(1, int(100 / rel_marker_density))
                        ax1.plot(t_plot[::step], g_plot[::step], 'o', color=color, markersize=rel_marker_size, alpha=0.8, label=label_name)
                elif curve_style == "Lines + Markers":
                    ax1.plot(t_plot, g_plot, '-', linewidth=rel_line_width, color=color)
                    if rel_marker_density > 0:
                        step = max(1, int(100 / rel_marker_density))
                        ax1.plot(t_plot[::step], g_plot[::step], 'o', color=color, markersize=rel_marker_size, alpha=0.8, label=label_name)

                if show_fit_pub and 'Best_Model' in r:
                    fit_model_pub = r['Best_Model']
                    if fit_model_pub in r['Fits']:
                        g_fit_norm = r['Fits'][fit_model_pub].get('curve', r['Raw']['g'])
                        g_fit_plot = g_fit_norm if is_normalized else g_fit_norm * G0
                        ax1.plot(t_plot, g_fit_plot, ':', color='black', linewidth=1.0, alpha=0.7)

                if show_tau_star:
                    tau_star = r.get('Tau_1e', np.nan)
                    if not np.isnan(tau_star):
                        tau_star_plot = tau_star / x_factor
                        intersection_level = 1/np.e if is_normalized else G0/np.e
                        ax1.plot(tau_star_plot, intersection_level, 'o', color=color, markersize=rel_marker_size + 1, markeredgecolor='black', markeredgewidth=0.8, zorder=5)
                        if not is_normalized:
                            ax1.hlines(intersection_level, xmin=t_plot.min() * 0.8, xmax=tau_star_plot, colors=color, linestyles='--', linewidths=0.8, alpha=0.5)
                        if annotate_tau_star:
                            ax1.text(tau_star_plot * 1.15, intersection_level + (0.02 if is_normalized else intersection_level * 0.02), r"$\tau^* = %.1f\ \mathrm{%s}$" % (tau_star_plot, x_label), fontsize=7, color=color)

            if show_tau_star and is_normalized:
                ax1.axhline(1/np.e, color='gray', linestyle='--', linewidth=1.0)
            if pub_time_axis == "Log":
                ax1.set_xscale('log')
            if pub_y_scale == "Log":
                ax1.set_yscale('log')

            ax1.set_xlabel(r"Time, $t$ ({})".format(x_label), fontdict=font_label_rel, labelpad=8)
            ax1.set_ylabel(y_label_text, fontdict=font_label_rel, labelpad=8)

            if rel_custom_lims:
                ax1.set_xlim(rel_xmin, rel_xmax)
                ax1.set_ylim(rel_ymin, rel_ymax)
            else:
                if is_normalized:
                    if pub_y_scale == "Log":
                        ax1.set_ylim(1e-3, 1.05)
                    else:
                        ax1.set_ylim(0, 1.05)
                else:
                    max_y = max([np.max(r['Raw']['g'] * r['Raw'].get('G0', 1.0)) for r in active_res])
                    if pub_y_scale == "Log":
                        min_y = min([np.min(r['Raw']['g'] * r['Raw'].get('G0', 1.0)) for r in active_res])
                        if min_y <= 0:
                            min_y = max_y * 1e-4
                        ax1.set_ylim(min_y * 0.8, max_y * 1.2)
                    else:
                        ax1.set_ylim(0, max_y * 1.05)

                all_times = np.concatenate([r['Raw']['t'] / x_factor for r in active_res])
                ax1.set_xlim(all_times.min() * 0.8, all_times.max() * 1.2)

            if show_rel_leg:
                l_pos = 'best'; l_anchor = None
                if rel_leg_pos == "Upper Right": l_pos = 'upper right'
                elif rel_leg_pos == "Upper Left": l_pos = 'upper left'
                elif rel_leg_pos == "Lower Left": l_pos = 'lower left'
                elif rel_leg_pos == "Lower Right": l_pos = 'lower right'
                elif rel_leg_pos == "Right (Outside)": l_pos = 'upper left'; l_anchor = (1.02, 1.0)
                elif rel_leg_pos == "Above the Plot (Horizontal)": l_pos = 'lower center'; l_anchor = (0.5, 1.05)
                elif rel_leg_pos == "Below the Plot (Horizontal)": l_pos = 'upper center'; l_anchor = (0.5, -0.22)
                elif rel_leg_pos == "Custom (Coords)": l_pos = rel_leg_anchor; l_anchor = (rel_leg_x, rel_leg_y)
                ax1.legend(frameon=rel_leg_box, loc=l_pos, bbox_to_anchor=l_anchor, fontsize=rel_leg_font_size, ncol=rel_leg_ncol, columnspacing=1.0, handletextpad=0.5)

            if panel_letter:
                ax1.text(-0.12, 1.02, f"({panel_letter})", transform=ax1.transAxes,
                         fontfamily=panel_font_family, fontsize=panel_font_size,
                         fontweight=panel_font_weight, fontstyle=panel_font_style,
                         va='bottom', ha='right')

            try:
                fig1.canvas.draw()
            except Exception as e:
                st.error(f"Matplotlib canvas draw failed for Figure 1! Error: {e}")
                st.write("**X-Axis Label:**", ax1.get_xlabel())
                st.write("**Y-Axis Label:**", ax1.get_ylabel())
                st.write("**Text Elements:**")
                for txt in ax1.texts:
                    st.write(f"- Text: `{txt.get_text()}` | Family: {txt.get_fontfamily()} | Size: {txt.get_fontsize()} | Weight: {txt.get_fontweight()} | Style: {txt.get_fontstyle()}")
                raise e
            rel_num_family = rel_font_family if rel_tick_font == "Same as Label" else rel_tick_font
            for label in ax1.get_xticklabels():
                label.set_family(rel_num_family)
                label.set_size(rel_tick_size)
                label.set_weight(rel_tick_weight)
                label.set_style(rel_tick_style)
            for label in ax1.get_yticklabels():
                label.set_family(rel_num_family)
                label.set_size(rel_tick_size)
                label.set_weight(rel_tick_weight)
                label.set_style(rel_tick_style)

            plt.tight_layout()
            st.pyplot(fig1, dpi=300, bbox_inches='tight')

            if pub_colorspace.startswith("CMYK"):
                # Save figure as RGB PNG bytes first
                buf_rgb_png = io.BytesIO()
                fig1.savefig(buf_rgb_png, format='png', dpi=1200, bbox_inches='tight')
                buf_rgb_png.seek(0)
                
                # Convert to CMYK using Pillow
                from PIL import Image
                img = Image.open(buf_rgb_png)
                img_cmyk = img.convert('CMYK')
                
                # Save as CMYK PDF
                buf_pdf1 = io.BytesIO()
                img_cmyk.save(buf_pdf1, format='PDF', dpi=(1200, 1200))
                buf_pdf1.seek(0)
                
                # Save as CMYK TIFF (lossless LZW compression)
                buf_tiff1 = io.BytesIO()
                img_cmyk.save(buf_tiff1, format='TIFF', dpi=(1200, 1200), compression='tiff_lzw')
                buf_tiff1.seek(0)
                
                # Save as CMYK JPEG (high quality)
                buf_jpg1 = io.BytesIO()
                img_cmyk.save(buf_jpg1, format='JPEG', dpi=(300, 300), quality=95)
                buf_jpg1.seek(0)
                
                dc1, dc2, dc3 = st.columns(3)
                with dc1: st.download_button("\U0001f4e5 PDF (1200 DPI CMYK)", buf_pdf1, "Relaxation_Curves_CMYK.pdf", key="dl_pdf_rel")
                with dc2: st.download_button("\U0001f4e5 TIFF (1200 DPI CMYK)", buf_tiff1, "Relaxation_Curves_CMYK.tiff", key="dl_tiff_rel")
                with dc3: st.download_button("\U0001f4e5 JPEG (300 DPI CMYK)", buf_jpg1, "Relaxation_Curves_CMYK.jpg", key="dl_jpg_rel")
            else:
                buf_pdf1 = io.BytesIO(); fig1.savefig(buf_pdf1, format='pdf', bbox_inches='tight'); buf_pdf1.seek(0)
                buf_svg1 = io.BytesIO(); fig1.savefig(buf_svg1, format='svg', bbox_inches='tight'); buf_svg1.seek(0)
                buf_png1 = io.BytesIO(); fig1.savefig(buf_png1, format='png', dpi=1200, bbox_inches='tight'); buf_png1.seek(0)
                from PIL import Image
                img1_rgb = Image.open(buf_png1)
                buf_bmp1 = io.BytesIO(); img1_rgb.save(buf_bmp1, format='BMP'); buf_bmp1.seek(0)
                buf_tiff1_rgb = io.BytesIO(); img1_rgb.save(buf_tiff1_rgb, format='TIFF', dpi=(1200, 1200)); buf_tiff1_rgb.seek(0)
                dc1, dc2, dc3, dc4, dc5 = st.columns(5)
                with dc1: st.download_button("📥 PDF (Vector)", buf_pdf1, "Relaxation_Curves.pdf", key="dl_pdf_rel")
                with dc2: st.download_button("📥 SVG (Vector)", buf_svg1, "Relaxation_Curves.svg", key="dl_svg_rel")
                with dc3: st.download_button("📥 PNG (1200 DPI)", buf_png1, "Relaxation_Curves.png", key="dl_png_rel")
                with dc4: st.download_button("📥 BMP (1200 DPI)", buf_bmp1, "Relaxation_Curves.bmp", key="dl_bmp_rel")
                with dc5: st.download_button("📥 TIFF (1200 DPI)", buf_tiff1_rgb, "Relaxation_Curves.tiff", key="dl_tiff_rel_rgb")
            plt.close(fig1)

            # ════ FIGURE 2: KINETICS PLOT (model-aware) ════
            st.markdown("---")
            st.subheader(f"\U0001f525 {pub_kin_model} Plot")
            if not kinetics_df.empty:
                active_k = kinetics_df[kinetics_df['Include']==True]
                if not active_k.empty and len(active_k) >= 2:
                    k_engine_pub = KineticsEngine()
                    temps_list = active_k['Temp'].tolist()
                    taus_list  = active_k['Tau'].tolist()

                    # --- Run the selected fit ---
                    fit_res_pub = None
                    if pub_kin_model == "Arrhenius":
                        fit_res_pub = k_engine_pub.fit_arrhenius(temps_list, taus_list)
                    elif pub_kin_model == "VFT":
                        fit_res_pub = k_engine_pub.fit_vft(temps_list, taus_list)
                    elif pub_kin_model == "Eyring (Transition State)":
                        fit_res_pub = k_engine_pub.fit_eyring(temps_list, taus_list)
                    elif pub_kin_model == "Van 't Hoff (Decrosslinking)":
                        g0_map = {r['Temp']: r['Raw']['G0'] for r in active_res}
                        active_g0s = [g0_map.get(t, 1.0) for t in temps_list]
                        fit_res_pub = k_engine_pub.fit_van_t_hoff(temps_list, active_g0s)
                    elif pub_kin_model == "Coupled WLF-Arrhenius":
                        fit_res_pub = k_engine_pub.fit_coupled_kinetics(temps_list, taus_list, Tg=Tg_input)

                    if fit_res_pub:
                        r_sq_pub = fit_res_pub.get('R2', 0.0)
                        R_GAS_PUB = 8.314462

                        # --- Metrics row ---
                        if fit_res_pub['Type'] == 'Arrhenius':
                            Ea_pub = fit_res_pub['Ea']
                            Ea_std_pub = fit_res_pub['Ea_std']
                            slope_pub = fit_res_pub['Params']['slope']
                            intercept_pub = fit_res_pub['Params']['intercept']
                            G_Pa_pub = G_prime_input * 1e6
                            tau_target_pub = 1e12 / G_Pa_pub
                            ln_tau_t_pub = np.log(tau_target_pub)
                            Tv_pub = (1000.0 / ((ln_tau_t_pub - intercept_pub)/slope_pub)) - 273.15 if slope_pub != 0 else 0
                            if show_tv:
                                cm1, cm2, cm3 = st.columns(3)
                                cm1.metric("E\u2090", f"{Ea_pub:.1f} \u00b1 {Ea_std_pub:.1f} kJ/mol" if show_ea_std else f"{Ea_pub:.1f} kJ/mol")
                                cm2.metric("T\u1d65", f"{Tv_pub:.1f} \u00b0C")
                                cm3.metric("R\u00b2", f"{r_sq_pub:.4f}")
                            else:
                                cm1, cm2 = st.columns(2)
                                cm1.metric("E\u2090", f"{Ea_pub:.1f} \u00b1 {Ea_std_pub:.1f} kJ/mol" if show_ea_std else f"{Ea_pub:.1f} kJ/mol")
                                cm2.metric("R\u00b2", f"{r_sq_pub:.4f}")

                        elif fit_res_pub['Type'] == 'VFT':
                            B_pub  = fit_res_pub['Params']['B']
                            T0_pub = fit_res_pub['Params']['T0'] - 273.15
                            cm1, cm2, cm3 = st.columns(3)
                            cm1.metric("B (VFT)", f"{B_pub:.1f} K")
                            cm2.metric("T\u2080", f"{T0_pub:.1f} \u00b0C")
                            cm3.metric("R\u00b2", f"{r_sq_pub:.4f}")

                        elif fit_res_pub['Type'] == 'Eyring':
                            dH_pub  = fit_res_pub['dH']
                            dH_std_pub = fit_res_pub['dH_std']
                            dS_pub  = fit_res_pub['dS']
                            cm1, cm2, cm3 = st.columns(3)
                            cm1.metric("\u0394H\u2021", f"{dH_pub:.1f} \u00b1 {dH_std_pub:.1f} kJ/mol" if show_ea_std else f"{dH_pub:.1f} kJ/mol")
                            cm2.metric("\u0394S\u2021", f"{dS_pub:.1f} J/mol\u00b7K")
                            cm3.metric("R\u00b2", f"{r_sq_pub:.4f}")

                        elif fit_res_pub['Type'] == 'Van_t_Hoff':
                            dH_d = fit_res_pub['dH_diss']
                            dS_d = fit_res_pub['dS_diss']
                            G0mx = fit_res_pub['G0_max']
                            cm1, cm2, cm3 = st.columns(3)
                            cm1.metric("\u0394H_diss", f"{dH_d:.1f} kJ/mol")
                            cm2.metric("\u0394S_diss", f"{dS_d:.1f} J/mol\u00b7K")
                            cm3.metric("R\u00b2", f"{r_sq_pub:.4f}")
                            st.caption(f"G₀,max = {G0mx:.3f} MPa")

                        elif fit_res_pub['Type'] == 'Coupled':
                            Ea_c = fit_res_pub['Ea_chem']
                            B_g  = fit_res_pub['B_glass']
                            T0_g = fit_res_pub['T0_glass']
                            cm1, cm2, cm3 = st.columns(3)
                            cm1.metric("Ea,chem", f"{Ea_c:.1f} kJ/mol")
                            cm2.metric("T\u2080 (glass)", f"{T0_g:.1f} \u00b0C")
                            cm3.metric("R\u00b2", f"{r_sq_pub:.4f}")

                        # --- Build matplotlib figure ---
                        fig2, ax2 = plt.subplots(figsize=(fig_width / 2.54, fig_height / 2.54), facecolor='white')
                        ax2.set_facecolor('white'); ax2.grid(False)
                        for spine in ['top', 'bottom', 'left', 'right']:
                            ax2.spines[spine].set_linewidth(1.0); ax2.spines[spine].set_color('black')
                        ax2.tick_params(axis='both', which='major', labelsize=kin_tick_size, width=1.0, length=4, direction='in', color='black', top=kin_mirror, right=kin_mirror)
                        ax2.tick_params(axis='both', which='minor', width=0.8, length=2.5, direction='in', color='black', top=kin_mirror, right=kin_mirror)

                        if kin_x_major != "Auto":
                            ax2.xaxis.set_major_locator(ticker.MaxNLocator(nbins=int(kin_x_major), prune=None))
                        if kin_x_minor != "Auto":
                            n_minor = int(kin_x_minor)
                            ax2.xaxis.set_minor_locator(ticker.NullLocator() if n_minor == 0 else ticker.AutoMinorLocator(n=n_minor + 1))
                        else:
                            ax2.xaxis.set_minor_locator(ticker.AutoMinorLocator())
                        if kin_y_major != "Auto":
                            ax2.yaxis.set_major_locator(ticker.MaxNLocator(nbins=int(kin_y_major), prune=None))
                        if kin_y_minor != "Auto":
                            n_minor = int(kin_y_minor)
                            ax2.yaxis.set_minor_locator(ticker.NullLocator() if n_minor == 0 else ticker.AutoMinorLocator(n=n_minor + 1))
                        else:
                            ax2.yaxis.set_minor_locator(ticker.AutoMinorLocator())

                        font_label_kin = {
                            'family': kin_font_family,
                            'size': kin_label_size,
                            'weight': kin_label_weight,
                            'style': kin_label_style
                        }

                        T_K_all = np.array(temps_list) + 273.15

                        # ── Model-specific plot data ──
                        if fit_res_pub['Type'] == 'Arrhenius':
                            x_data = fit_res_pub['Plot']['x']          # 1/T
                            y_data = fit_res_pub['Plot']['y']          # ln(tau)
                            x_label_kin = r"$1000/T\ (\mathrm{K}^{-1})$"
                            y_label_kin = r"$\ln(\tau)$"
                            # scatter: plot as 1000/T
                            ax2.scatter(x_data * 1000, y_data, s=kin_marker_size**2, alpha=0.8,
                                        edgecolors='black', linewidth=0.8, color='steelblue', zorder=3)
                            x_range = np.linspace(x_data.min() * 0.95, x_data.max() * 1.05, 100)
                            y_fit = slope_pub * x_range + intercept_pub
                            label_fit = (r"$E_\mathrm{a} = %.1f \pm %.1f\ \mathrm{kJ\ mol}^{-1}$" % (Ea_pub, Ea_std_pub)
                                         if show_ea_std else r"$E_\mathrm{a} = %.1f\ \mathrm{kJ\ mol}^{-1}$" % Ea_pub)
                            label_fit += "\n" + r"$R^2 = %.4f$" % r_sq_pub
                            ax2.plot(x_range * 1000, y_fit, '--', color='red', linewidth=kin_line_width, label=label_fit, zorder=2)
                            ax2.set_xlabel(x_label_kin, fontdict=font_label_kin, labelpad=8)
                            ax2.set_ylabel(y_label_kin, fontdict=font_label_kin, labelpad=8)
                            if show_tv:
                                Tv_x_1000 = (ln_tau_t_pub - intercept_pub) / slope_pub * 1000
                                ax2.plot([Tv_x_1000], [ln_tau_t_pub], marker='*', markersize=kin_marker_size * 2,
                                         color='gold', markeredgecolor='black', markeredgewidth=0.8,
                                         label=r"$T_\mathrm{v} = %.1f^\circ\mathrm{C}$" % Tv_pub, zorder=4)
                                min_x_plot = min(x_data.min() * 0.95, (ln_tau_t_pub - intercept_pub) / slope_pub) * 1000
                                max_x_plot = max(x_data.max() * 1.05, (ln_tau_t_pub - intercept_pub) / slope_pub) * 1000
                                min_y_plot = min(y_data.min(), ln_tau_t_pub) - 0.5
                                max_y_plot = max(y_data.max(), ln_tau_t_pub) + 0.5
                            else:
                                min_x_plot = x_data.min() * 0.95 * 1000
                                max_x_plot = x_data.max() * 1.05 * 1000
                                min_y_plot = y_data.min() - 0.5
                                max_y_plot = y_data.max() + 0.5

                        elif fit_res_pub['Type'] == 'VFT':
                            inv_T = 1.0 / T_K_all
                            ln_tau = np.log(np.array(taus_list))
                            ax2.scatter(inv_T * 1000, ln_tau, s=kin_marker_size**2, alpha=0.8,
                                        edgecolors='black', linewidth=0.8, color='steelblue', zorder=3)
                            T_K_grid = np.linspace(T_K_all.min() * 0.97, T_K_all.max() * 1.03, 150)
                            A_p = fit_res_pub['Params']['A']; B_p = fit_res_pub['Params']['B']; T0_p = fit_res_pub['Params']['T0']
                            y_fit = A_p + B_p / (T_K_grid - T0_p)
                            label_fit = r"VFT: $B = %.0f\ \mathrm{K},\ T_0 = %.1f^\circ\mathrm{C}$" % (B_p, T0_p - 273.15)
                            label_fit += "\n" + r"$R^2 = %.4f$" % r_sq_pub
                            ax2.plot(1000 / T_K_grid, y_fit, '--', color='red', linewidth=kin_line_width, label=label_fit, zorder=2)
                            ax2.set_xlabel(r"$1000/T\ (\mathrm{K}^{-1})$", fontdict=font_label_kin, labelpad=8)
                            ax2.set_ylabel(r"$\ln(\tau)$", fontdict=font_label_kin, labelpad=8)
                            min_x_plot = (1000 / T_K_all).min() * 0.95
                            max_x_plot = (1000 / T_K_all).max() * 1.05
                            min_y_plot = ln_tau.min() - 0.5
                            max_y_plot = ln_tau.max() + 0.5

                        elif fit_res_pub['Type'] == 'Eyring':
                            x_data = fit_res_pub['Plot']['x']          # 1/T
                            y_data = fit_res_pub['Plot']['y']          # ln(tau*T)
                            ax2.scatter(x_data * 1000, y_data, s=kin_marker_size**2, alpha=0.8,
                                        edgecolors='black', linewidth=0.8, color='steelblue', zorder=3)
                            x_range = np.linspace(x_data.min() * 0.95, x_data.max() * 1.05, 100)
                            y_fit = fit_res_pub['Params']['slope'] * x_range + fit_res_pub['Params']['intercept']
                            label_fit = (r"$\Delta H^\ddagger = %.1f \pm %.1f\ \mathrm{kJ\ mol}^{-1}$" % (dH_pub, dH_std_pub)
                                         if show_ea_std else r"$\Delta H^\ddagger = %.1f\ \mathrm{kJ\ mol}^{-1}$" % dH_pub)
                            label_fit += "\n" + r"$\Delta S^\ddagger = %.1f\ \mathrm{J\ mol}^{-1}\mathrm{K}^{-1}$" % dS_pub
                            label_fit += "\n" + r"$R^2 = %.4f$" % r_sq_pub
                            ax2.plot(x_range * 1000, y_fit, '--', color='red', linewidth=kin_line_width, label=label_fit, zorder=2)
                            ax2.set_xlabel(r"$1000/T\ (\mathrm{K}^{-1})$", fontdict=font_label_kin, labelpad=8)
                            ax2.set_ylabel(r"$\ln(\tau \cdot T)$", fontdict=font_label_kin, labelpad=8)
                            min_x_plot = x_data.min() * 0.95 * 1000
                            max_x_plot = x_data.max() * 1.05 * 1000
                            min_y_plot = y_data.min() - 0.5
                            max_y_plot = y_data.max() + 0.5

                        elif fit_res_pub['Type'] == 'Van_t_Hoff':
                            x_data = fit_res_pub['Plot']['x']          # 1000/T
                            y_data = fit_res_pub['Plot']['y']          # G0 values
                            ax2.scatter(x_data, y_data, s=kin_marker_size**2, alpha=0.8,
                                        edgecolors='black', linewidth=0.8, color='steelblue', zorder=3)
                            T_K_grid = np.linspace(T_K_all.min() * 0.97, T_K_all.max() * 1.03, 150)
                            G0mx_p = fit_res_pub['Params']['G0_max']
                            dH_p   = fit_res_pub['Params']['dH_diss']
                            dS_p   = fit_res_pub['Params']['dS_diss']
                            y_fit  = G0mx_p / (1.0 + np.exp(np.clip(-dH_p / (R_GAS_PUB * T_K_grid) + dS_p / R_GAS_PUB, -50, 50)))
                            label_fit = (r"$\Delta H_\mathrm{diss} = %.1f\ \mathrm{kJ\ mol}^{-1}$" % dH_d +
                                         "\n" + r"$\Delta S_\mathrm{diss} = %.1f\ \mathrm{J\ mol}^{-1}\mathrm{K}^{-1}$" % dS_d +
                                         "\n" + r"$R^2 = %.4f$" % r_sq_pub)
                            ax2.plot(1000.0 / T_K_grid, y_fit, '--', color='red', linewidth=kin_line_width, label=label_fit, zorder=2)
                            ax2.set_xlabel(r"$1000/T\ (\mathrm{K}^{-1})$", fontdict=font_label_kin, labelpad=8)
                            ax2.set_ylabel(r"$G_0$ (MPa)", fontdict=font_label_kin, labelpad=8)
                            min_x_plot = x_data.min() * 0.95
                            max_x_plot = x_data.max() * 1.05
                            min_y_plot = float(np.min(y_data)) * 0.9
                            max_y_plot = float(np.max(y_data)) * 1.1

                        elif fit_res_pub['Type'] == 'Coupled':
                            inv_T = 1.0 / T_K_all
                            ln_tau = np.log(np.array(taus_list))
                            ax2.scatter(inv_T * 1000, ln_tau, s=kin_marker_size**2, alpha=0.8,
                                        edgecolors='black', linewidth=0.8, color='steelblue', zorder=3)
                            T_K_grid = np.linspace(T_K_all.min() * 0.97, T_K_all.max() * 1.03, 150)
                            T0_p = fit_res_pub['Params']['T0']
                            term1 = np.exp(fit_res_pub['Params']['ln_A'] + fit_res_pub['Params']['Ea'] / (R_GAS_PUB * T_K_grid))
                            term2 = np.exp(np.clip(fit_res_pub['Params']['ln_C'] + fit_res_pub['Params']['B'] / (T_K_grid - T0_p), -50, 50))
                            y_fit = np.log(term1 + term2)
                            label_fit = (r"Coupled: $E_{a,\mathrm{chem}} = %.1f\ \mathrm{kJ\ mol}^{-1}$" % Ea_c +
                                         "\n" + r"$T_0 = %.1f^\circ\mathrm{C}$" % T0_g +
                                         "\n" + r"$R^2 = %.4f$" % r_sq_pub)
                            ax2.plot(1000 / T_K_grid, y_fit, '--', color='red', linewidth=kin_line_width, label=label_fit, zorder=2)
                            ax2.set_xlabel(r"$1000/T\ (\mathrm{K}^{-1})$", fontdict=font_label_kin, labelpad=8)
                            ax2.set_ylabel(r"$\ln(\tau)$", fontdict=font_label_kin, labelpad=8)
                            min_x_plot = (1000 / T_K_all).min() * 0.95
                            max_x_plot = (1000 / T_K_all).max() * 1.05
                            min_y_plot = ln_tau.min() - 0.5
                            max_y_plot = ln_tau.max() + 0.5

                        # --- Axis limits ---
                        if kin_custom_lims:
                            ax2.set_xlim(kin_xmin, kin_xmax)
                            ax2.set_ylim(kin_ymin, kin_ymax)
                        else:
                            ax2.set_xlim(min_x_plot, max_x_plot)
                            ax2.set_ylim(min_y_plot, max_y_plot)

                        # --- Legend ---
                        if show_kin_leg:
                            l_pos = 'best'; l_anchor = None
                            if kin_leg_pos == "Upper Right": l_pos = 'upper right'
                            elif kin_leg_pos == "Upper Left": l_pos = 'upper left'
                            elif kin_leg_pos == "Lower Left": l_pos = 'lower left'
                            elif kin_leg_pos == "Lower Right": l_pos = 'lower right'
                            elif kin_leg_pos == "Right (Outside)": l_pos = 'upper left'; l_anchor = (1.02, 1.0)
                            elif kin_leg_pos == "Above the Plot (Horizontal)": l_pos = 'lower center'; l_anchor = (0.5, 1.05)
                            elif kin_leg_pos == "Below the Plot (Horizontal)": l_pos = 'upper center'; l_anchor = (0.5, -0.22)
                            elif kin_leg_pos == "Custom (Coords)": l_pos = kin_leg_anchor; l_anchor = (kin_leg_x, kin_leg_y)
                            ax2.legend(frameon=kin_leg_box, loc=l_pos, bbox_to_anchor=l_anchor,
                                       fontsize=kin_leg_font_size, ncol=kin_leg_ncol,
                                       columnspacing=1.0, handletextpad=0.5)

                        # --- Panel letter ---
                        if panel_letter and len(panel_letter) == 1 and panel_letter.isalpha():
                            next_letter = chr(ord(panel_letter) + 1)
                            ax2.text(-0.12, 1.02, f"({next_letter})", transform=ax2.transAxes,
                                     fontfamily=panel_font_family, fontsize=panel_font_size,
                                     fontweight=panel_font_weight, fontstyle=panel_font_style,
                                     va='bottom', ha='right')

                        try:
                            fig2.canvas.draw()
                        except Exception as e:
                            st.error(f"Matplotlib canvas draw failed for kinetics figure! Error: {e}")
                            raise e

                        kin_num_family = kin_font_family if kin_tick_font == "Same as Label" else kin_tick_font
                        for lbl in ax2.get_xticklabels():
                            lbl.set_family(kin_num_family); lbl.set_size(kin_tick_size)
                            lbl.set_weight(kin_tick_weight); lbl.set_style(kin_tick_style)
                        for lbl in ax2.get_yticklabels():
                            lbl.set_family(kin_num_family); lbl.set_size(kin_tick_size)
                            lbl.set_weight(kin_tick_weight); lbl.set_style(kin_tick_style)

                        plt.tight_layout()
                        st.pyplot(fig2, dpi=300, bbox_inches='tight')

                        # --- Download buttons ---
                        model_slug = pub_kin_model.replace(" ", "_").replace("'", "").replace("(", "").replace(")", "")
                        if pub_colorspace.startswith("CMYK"):
                            buf_rgb_png = io.BytesIO()
                            fig2.savefig(buf_rgb_png, format='png', dpi=1200, bbox_inches='tight')
                            buf_rgb_png.seek(0)
                            from PIL import Image
                            img = Image.open(buf_rgb_png)
                            img_cmyk = img.convert('CMYK')
                            buf_pdf2 = io.BytesIO(); img_cmyk.save(buf_pdf2, format='PDF', dpi=(1200, 1200)); buf_pdf2.seek(0)
                            buf_tiff2 = io.BytesIO(); img_cmyk.save(buf_tiff2, format='TIFF', dpi=(1200, 1200), compression='tiff_lzw'); buf_tiff2.seek(0)
                            buf_jpg2 = io.BytesIO(); img_cmyk.save(buf_jpg2, format='JPEG', dpi=(300, 300), quality=95); buf_jpg2.seek(0)
                            da1, da2, da3 = st.columns(3)
                            with da1: st.download_button("\U0001f4e5 PDF (1200 DPI CMYK)", buf_pdf2, f"{model_slug}_CMYK.pdf", key="dl_pdf_arr")
                            with da2: st.download_button("\U0001f4e5 TIFF (1200 DPI CMYK)", buf_tiff2, f"{model_slug}_CMYK.tiff", key="dl_tiff_arr")
                            with da3: st.download_button("\U0001f4e5 JPEG (300 DPI CMYK)", buf_jpg2, f"{model_slug}_CMYK.jpg", key="dl_jpg_arr")
                        else:
                            buf_pdf2 = io.BytesIO(); fig2.savefig(buf_pdf2, format='pdf', bbox_inches='tight'); buf_pdf2.seek(0)
                            buf_svg2 = io.BytesIO(); fig2.savefig(buf_svg2, format='svg', bbox_inches='tight'); buf_svg2.seek(0)
                            buf_png2 = io.BytesIO(); fig2.savefig(buf_png2, format='png', dpi=1200, bbox_inches='tight'); buf_png2.seek(0)
                            from PIL import Image
                            img2_rgb = Image.open(buf_png2)
                            buf_bmp2 = io.BytesIO(); img2_rgb.save(buf_bmp2, format='BMP'); buf_bmp2.seek(0)
                            buf_tiff2_rgb = io.BytesIO(); img2_rgb.save(buf_tiff2_rgb, format='TIFF', dpi=(1200, 1200)); buf_tiff2_rgb.seek(0)
                            da1, da2, da3, da4, da5 = st.columns(5)
                            with da1: st.download_button("\U0001f4e5 PDF (Vector)", buf_pdf2, f"{model_slug}.pdf", key="dl_pdf_arr")
                            with da2: st.download_button("\U0001f4e5 SVG (Vector)", buf_svg2, f"{model_slug}.svg", key="dl_svg_arr")
                            with da3: st.download_button("\U0001f4e5 PNG (1200 DPI)", buf_png2, f"{model_slug}.png", key="dl_png_arr")
                            with da4: st.download_button("\U0001f4e5 BMP (1200 DPI)", buf_bmp2, f"{model_slug}.bmp", key="dl_bmp_arr")
                            with da5: st.download_button("\U0001f4e5 TIFF (1200 DPI)", buf_tiff2_rgb, f"{model_slug}.tiff", key="dl_tiff_arr_rgb")
                        plt.close(fig2)
                    else:
                        st.error(f"{pub_kin_model} fitting failed. Try a different model or check your data.")
                else:
                    st.warning("\u26a0\ufe0f Need at least 2 data points with 'Include' checked in the Analysis tab \u2192 Kinetics")
            else:
                st.info("\U0001f4ca Run kinetics analysis in the Analysis tab first, then return here.")

# ==========================
# TAB 6: EDUCATION & THEORY

# --- MODULAR TABS ---
from can_relax.gui.components import render_education_tab, render_credits_tab, render_plotting_tab

render_plotting_tab(tab_plotting)
render_education_tab(tab_education)
render_credits_tab(tab_credits)
