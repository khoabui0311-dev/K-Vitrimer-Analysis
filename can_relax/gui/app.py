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
from can_relax.core.analyzer import CurveAnalyzer
from can_relax.io.parser import parse_wide_format_data as parser_module_func

# Simple implementations for engine classes used in the app
class SpectrumAnalyzer:
    def compute_continuous_spectrum(self, t, g, num_modes=50, alpha=0.1):
        """Compute relaxation time spectrum using simple Tikhonov regularization"""
        g_norm = g / g[0] if g[0] > 0 else g
        log_min, log_max = np.log10(max(t.min(), 1e-6)), np.log10(t.max())
        tau_grid = np.logspace(log_min-1, log_max+1, num_modes)
        A = np.exp(-t[:, None] / tau_grid[None, :])
        
        # Simple Tikhonov regularization without sklearn
        # Solve: (A^T A + alpha*L^T L) H = A^T g
        # where L is identity matrix for L2 regularization
        ATA = A.T @ A
        ATg = A.T @ g_norm
        L = np.eye(num_modes)
        H = np.linalg.solve(ATA + alpha * (L.T @ L), ATg)
        H = np.maximum(H, 0)  # Non-negative constraint
        return tau_grid, H

class MaterialSimulator:
    def simulate_curve(self, T, model_name, p):
        """Simulate a relaxation curve at temperature T"""
        R = 8.314
        try:
            tau_v = 1e6 / p['G_plateau'] 
            term_tv = np.exp((p['Ea']*1000/R) * (1/(p['Tv']+273.15)))
            tau0 = tau_v / term_tv
            term_t = np.exp((p['Ea']*1000/R) * (1/(T+273.15)))
            tau_T = tau0 * term_t
            t = np.logspace(np.log10(tau_T)-3, np.log10(tau_T)+2, 100)
            
            if model_name == 'Maxwell':
                g = p['G_plateau'] * np.exp(-t/tau_T)
            elif model_name == 'Single_KWW':
                g = p['G_plateau'] * np.exp(-(t/tau_T)**p['beta'])
            else: g = t*0
            
            return t, g, tau_T
        except:
            return np.array([1]), np.array([1]), 1

class TTSEngine:
    def generate_mastercurve(self, results, ref_temp=None):
        """Generate time-temperature superposition mastercurve"""
        if not results: return None
        
        sorted_res = sorted(results, key=lambda x: x['Temp'])
        if ref_temp is None:
            ref_res = sorted_res[len(sorted_res)//2]
        else:
            ref_res = min(sorted_res, key=lambda x: abs(x['Temp'] - ref_temp))
        
        T_ref = ref_res['Temp']
        
        def get_tau(res):
            best = res.get('Best_Model', 'Single_KWW')
            if best not in res.get('Fits', {}): return 1.0
            popt = res['Fits'][best]['popt']
            if best == 'Maxwell' or best == 'Single_KWW': return popt[0]
            if best == 'Dual_KWW': return popt[1]
            return 1.0

        tau_ref = get_tau(ref_res)
        master_t, master_g, shift_factors = [], [], {}
        
        for res in sorted_res:
            T = res['Temp']
            tau = get_tau(res)
            aT = tau / tau_ref
            shift_factors[T] = aT
            t_shifted = res['Raw']['t'] / aT
            master_t.append(t_shifted)
            master_g.append(res['Raw']['g'])
        
        full_t = np.concatenate(master_t)
        full_g = np.concatenate(master_g)
        sort_idx = np.argsort(full_t)
        
        return {
            "T_ref": T_ref,
            "Master_t": full_t[sort_idx],
            "Master_g": full_g[sort_idx],
            "Shifts": shift_factors
        }



# ==========================================
# 1. CORE ENGINE (INTERNALIZED FROM can_relax)
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
st.sidebar.title("🧪 K Vitrimer Analysis")
st.sidebar.caption("v1.0 | Professional Edition")

# Init Modules
analyzer = CurveAnalyzer()
spectrum_engine = SpectrumAnalyzer()
sim = MaterialSimulator()
tts_engine = TTSEngine()

# Helper
def get_tau_1_over_e(t, g):
    target = 0.36788 * g[0] # Scale target by G0
    try:
        if g[0] > g[-1]: return np.interp(target, g[::-1], t[::-1])
    except: pass
    return np.nan

# TABS
tab_analysis, tab_sim, tab_pub, tab_comparison, tab_education, tab_credits = st.tabs([
    "🚀 Analysis", "🧪 Virtual Lab", "📝 Publish", "📊 Compare", "📚 Education", "©️ Credits"
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
    run_btn = st.sidebar.button("▶ Run Analysis", type="primary", use_container_width=True)

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
            ctl1, ctl2, _ctl3 = st.columns([1, 1, 4])
            with ctl1:
                time_axis_type = st.radio("Time Scale", ["Log", "Linear"], horizontal=True)
            with ctl2:
                show_fits = st.checkbox("Show Fits", True)

            fig = go.Figure()
            for r in active_results:
                t_raw = r['Raw']['t']
                g_raw = r['Raw']['g']
                g_norm = g_raw
                step = max(1, len(t_raw)//300)
                fig.add_trace(go.Scatter(
                    x=t_raw[::step],
                    y=g_norm[::step],
                    mode='markers',
                    name=f"{r['Temp']}C",
                    marker=dict(size=6, opacity=0.8)
                ))
                if show_fits and fit_model in r['Fits']:
                    g_fit_raw = r['Fits'][fit_model].get('curve', r['Raw']['g'])
                    g_fit_norm = g_fit_raw
                    fig.add_trace(go.Scatter(
                        x=t_raw,
                        y=g_fit_norm,
                        mode='lines',
                        name=f"Fit",
                        line=dict(width=2, dash='dash', color='black')
                    ))

            t_type = "log" if time_axis_type == "Log" else "linear"
            fig.update_xaxes(type=t_type, title="Time (s)")
            fig.update_yaxes(title="G(t)/G\u2080")
            fig.update_layout(height=500, margin=dict(l=20,r=20,t=20,b=20))
            st.plotly_chart(fig, use_container_width=True)

            # ── Fitting parameters: collapsible ──
            with st.expander("\U0001f4ca Fitting Parameters", expanded=False):
                fit_details = []
                for r in active_results:
                    temp = r['Temp']
                    if fit_model in r['Fits']:
                        p = r['Fits'][fit_model]['popt']
                        r2 = r['Fits'][fit_model]['r2']
                        if fit_model == "Maxwell":
                            fit_details.append({"Temperature (\u00b0C)": temp, "Tau (s)": p[0], "R\u00b2": r2})
                        elif fit_model == "Single_KWW":
                            fit_details.append({"Temperature (\u00b0C)": temp, "Tau (s)": p[0], "Beta (\u03b2)": p[1], "R\u00b2": r2})
                        elif fit_model == "Dual_KWW":
                            fit_details.append({"Temperature (\u00b0C)": temp, "Fraction A": p[0], "Tau 1 (s)": p[1], "Beta 1 (\u03b21)": p[2], "Tau 2 (s)": p[3], "Beta 2 (\u03b22)": p[4], "R\u00b2": r2})
                if fit_details:
                    df_details = pd.DataFrame(fit_details)
                    col_config = {
                        "Temperature (\u00b0C)": st.column_config.NumberColumn(format="%.1f"),
                        "R\u00b2": st.column_config.NumberColumn(format="%.4f")
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
                    st.dataframe(df_details, column_config=col_config, hide_index=True, use_container_width=True)
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
                    st.caption("Uncheck rows to exclude them from the Arrhenius fit.")
                    edited_df = st.data_editor(df_k, column_config={"Include": st.column_config.CheckboxColumn("Fit?", default=True)}, hide_index=True, height=380, use_container_width=True)
                    st.session_state.kinetics_df = edited_df

                with col_chart:
                    active = edited_df[edited_df["Include"] == True]
                    if len(active) >= 2:
                        slope, intercept, r_sq, _, _ = linregress(active["1000/T"], active["ln(Tau)"])
                        Ea = slope * 8.314462
                        G_Pa = G_prime_input * 1e6; tau_target = 1e12 / G_Pa; ln_tau_t = np.log(tau_target)
                        if slope != 0: Tv_val = (1000.0 / ((ln_tau_t - intercept)/slope)) - 273.15
                        else: Tv_val = 0

                        mc1, mc2, mc3 = st.columns(3)
                        mc1.metric("E\u2090", f"{Ea:.1f} kJ/mol")
                        mc2.metric("T\u1d65", f"{Tv_val:.1f} \u00b0C")
                        mc3.metric("R\u00b2", f"{r_sq:.4f}")

                        fig_k = go.Figure()
                        fig_k.add_trace(go.Scatter(x=active["1000/T"], y=active["ln(Tau)"], mode='markers', name="Data"))
                        xr = np.linspace(active["1000/T"].min()*0.95, active["1000/T"].max()*1.05, 10)
                        fig_k.add_trace(go.Scatter(x=xr, y=slope*xr+intercept, mode='lines', name=f"Ea={Ea:.1f} kJ", line=dict(dash='dash', color='red')))
                        fig_k.add_trace(go.Scatter(x=[(ln_tau_t - intercept)/slope], y=[ln_tau_t], mode='markers', marker=dict(symbol='star', size=14, color='gold'), name=f"Tv={Tv_val:.1f}C"))
                        fig_k.update_layout(xaxis_title="1000/T (K\u207b\u00b9)", yaxis_title="ln(\u03c4)", height=420, margin=dict(l=10, r=10, t=20, b=20))
                        st.plotly_chart(fig_k, use_container_width=True)
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
                        fig_mc.update_yaxes(title="G(t) (Pa)")
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
                alpha_reg = st.slider("Smoothness", 0.0, 1.0, 0.1)
                n_modes = st.slider("Bins", 20, 200, 50)
            with c_spec:
                fig_h = go.Figure()
                for i, r in enumerate(active_results):
                    t = r['Raw']['t']; g = r['Raw']['g']
                    tau_grid, H = spectrum_engine.compute_continuous_spectrum(t, g, num_modes=n_modes, alpha=alpha_reg)
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
                    slope, intercept, _, _, _ = linregress(inv_T, ln_tau)
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
                sim_fig_fmt = st.selectbox("Format", ["png", "pdf", "svg"], key="sim_fmt")
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
                        slope, intercept, r_val, _, _ = linregress(inv_T, ln_tau)
                        r_sq = r_val**2
                        Ea_rec = slope * 8.314462
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
                text_data = '\n'.join([f"{row.get('Temperature (°C)', 0)}, {row.get('τ (s)', 0)}" for row in existing_data]) if existing_data else "100, 1.0\n110, 0.5\n120, 0.2"
                
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
                    st.rerun()
    
    # Analysis button
    st.markdown("---")
    if st.button("🔍 Analyze All Samples", type="primary", width='stretch'):
        # Collect non-empty samples
        valid_samples = []
        for key, sample_data in st.session_state.comparison_samples.items():
            if sample_data.get('data') and len(sample_data['data']) >= 2:
                valid_samples.append(sample_data)
        
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
                    slope, intercept, r_val, _, _ = linregress(inv_T, ln_tau)
                    r_sq = r_val**2
                    Ea = slope * 8.314462  # kJ/mol
                    
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
                        'Tg (°C)': tg,
                        "G' (MPa)": g_prime,
                        'Ea (kJ/mol)': Ea,
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
                st.warning(r['warning'])
        
        # Results table
        st.subheader("📊 Results Summary")
        gp_key = "G' (MPa)"
        results_df = pd.DataFrame([
            {
                'Sample Name': r['Sample Name'],
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
            comp_fmt = st.selectbox("Format", ["png", "pdf", "svg"], key="comp_fmt")
            comp_dpi = st.number_input("DPI", 72, 1200, 300, 50, key="comp_dpi")
            comp_width = st.number_input("Width (in)", 2.0, 12.0, 5.0, 0.1, key="comp_width")
            comp_height = st.number_input("Height (in)", 2.0, 10.0, 4.0, 0.1, key="comp_height")
            show_comp_legend = st.checkbox("Legend", value=True, key="comp_legend")
        
        with col_plot:
            fig_comp = go.Figure()
            
            # Color palette for up to 6 samples
            colors = ['#EF553B', '#636EFA', '#00CC96', '#AB63FA', '#FFA15A', '#25D098']
            
            for idx, r in enumerate(results):
                inv_T = r['inv_T']
                ln_tau = r['ln_tau']
                name = r['Sample Name']
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
            
            fig_comp.update_layout(
                title="Arrhenius Comparison: Multiple Samples",
                xaxis_title="1000/T (K<sup>-1</sup>)",
                yaxis_title="ln(tau) (s)",
                height=500,
                hovermode='closest',
                showlegend=show_comp_legend,
                legend=dict(x=0.02, y=0.98, bgcolor='rgba(255,255,255,0.8)', borderwidth=1),
                margin=dict(l=60, r=20, t=50, b=50)
            )
            
            st.plotly_chart(fig_comp, width='stretch')
        
        # Export matplotlib figure
        if st.button("📥 Export Comparison Plot", key="export_comp"):
            fig_mpl = plt.figure(figsize=(comp_width, comp_height))
            ax_mpl = fig_mpl.add_subplot(111)
            
            colors_mpl = plt.cm.tab10(np.linspace(0, 1, len(results)))
            
            for idx, r in enumerate(results):
                inv_T = r['inv_T']
                ln_tau = r['ln_tau']
                name = r['Sample Name']
                slope = r['slope']
                intercept = r['intercept']
                Ea = r['Ea (kJ/mol)']
                tau_target = r['tau_target']
                ln_tau_target = r['ln_tau_target']
                
                # Plot data
                ax_mpl.scatter(inv_T, ln_tau, s=100, alpha=0.7, edgecolors='black', linewidth=1.2,
                             label=name, color=colors_mpl[idx], zorder=3)
                
                # Plot fit line
                x_range = np.linspace(inv_T.min() * 0.9, inv_T.max() * 1.1, 50)
                y_fit = slope * x_range + intercept
                ax_mpl.plot(x_range, y_fit, '--', color=colors_mpl[idx], linewidth=2, alpha=0.8, zorder=2)
                
                # Plot Tv marker
                tv_x = (ln_tau_target - intercept) / slope
                ax_mpl.plot([tv_x], [ln_tau_target], marker='*', markersize=20, color=colors_mpl[idx],
                          markeredgecolor='black', markeredgewidth=1.5, zorder=4)
            
            ax_mpl.set_xlabel(r"$1000/T$ (K$^{-1}$)", fontsize=12, fontweight='bold')
            ax_mpl.set_ylabel(r"$\ln(\tau)$ (s)", fontsize=12, fontweight='bold')
            ax_mpl.grid(True, alpha=0.3, linestyle='--')
            ax_mpl.legend(frameon=True, fontsize=10, loc='best')
            ax_mpl.tick_params(labelsize=10)
            plt.tight_layout()
            
            buf = io.BytesIO()
            fig_mpl.savefig(buf, format=comp_fmt, dpi=comp_dpi, bbox_inches='tight')
            buf.seek(0)
            st.download_button("⬇️ Download Comparison Figure", buf, f"Arrhenius_Comparison.{comp_fmt}", key="dl_comp_plot")
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
                    default_width, default_height, disable_size = 3.35, 2.95, True
                elif fig_preset == "ACS/RSC Double-Column (170 x 140 mm)":
                    default_width, default_height, disable_size = 6.69, 5.51, True
                else:
                    default_width, default_height, disable_size = 3.5, 3.0, False

                sz1, sz2 = st.columns(2)
                with sz1:
                    fig_width = st.number_input("Width (in)", 1.0, 15.0, default_width, 0.1, disabled=disable_size, key="pub_w")
                with sz2:
                    fig_height = st.number_input("Height (in)", 1.0, 15.0, default_height, 0.1, disabled=disable_size, key="pub_h")
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
                y_norm_select = st.selectbox("Normalization", ["Normalized (G/G\u2080 or E/E\u2080)", "Non-Normalized (G or E)"], key="pub_ynorm")
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
                chk4, chk5 = st.columns(2)
                with chk4:
                    show_tv = st.checkbox("Show T\u1d65", value=True, key="pub_showtv")
                with chk5:
                    show_ea_std = st.checkbox("Ea \u00b1 std", value=True, key="pub_eastd")
                
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
            fig1, ax1 = plt.subplots(figsize=(fig_width, fig_height), facecolor='white')
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
                y_label_text = r"$G(t)$" if y_label_select.startswith("G") else r"$E(t)$"

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
                            ax1.text(tau_star_plot * 1.15, intersection_level + (0.02 if is_normalized else intersection_level * 0.02), r"$\tau^* = %.1f\text{ %s}$" % (tau_star_plot, x_label), fontsize=7, color=color)

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

            fig1.canvas.draw()
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
                dc1, dc2, dc3 = st.columns(3)
                with dc1: st.download_button("\U0001f4e5 PDF (Vector)", buf_pdf1, "Relaxation_Curves.pdf", key="dl_pdf_rel")
                with dc2: st.download_button("\U0001f4e5 SVG (Vector)", buf_svg1, "Relaxation_Curves.svg", key="dl_svg_rel")
                with dc3: st.download_button("\U0001f4e5 PNG (1200 DPI)", buf_png1, "Relaxation_Curves.png", key="dl_png_rel")
            plt.close(fig1)

            # ════ FIGURE 2: ARRHENIUS PLOT ════
            st.markdown("---")
            st.subheader("\U0001f525 Arrhenius Plot")
            if not kinetics_df.empty:
                active_k = kinetics_df[kinetics_df['Include']==True]
                if not active_k.empty and len(active_k) >= 2:
                    slope, intercept, r_val, p_val, stderr = linregress(active_k['1000/T'], active_k['ln(Tau)'])
                    r_sq = r_val**2
                    Ea = slope * 8.314462
                    Ea_stderr = stderr * 8.314462 if stderr is not None else 0.0
                    G_Pa = G_prime_input * 1e6
                    tau_target = 1e12 / G_Pa
                    ln_tau_t = np.log(tau_target)
                    Tv_val = (1000.0 / ((ln_tau_t - intercept)/slope)) - 273.15 if slope != 0 else 0

                    if show_tv:
                        cm1, cm2, cm3 = st.columns(3)
                        with cm1:
                            st.metric("E\u2090", f"{Ea:.1f} \u00b1 {Ea_stderr:.1f} kJ/mol" if show_ea_std else f"{Ea:.1f} kJ/mol")
                        with cm2: st.metric("T\u1d65", f"{Tv_val:.1f} \u00b0C")
                        with cm3: st.metric("R\u00b2", f"{r_sq:.4f}")
                    else:
                        cm1, cm2 = st.columns(2)
                        with cm1:
                            st.metric("E\u2090", f"{Ea:.1f} \u00b1 {Ea_stderr:.1f} kJ/mol" if show_ea_std else f"{Ea:.1f} kJ/mol")
                        with cm2: st.metric("R\u00b2", f"{r_sq:.4f}")

                    fig2, ax2 = plt.subplots(figsize=(fig_width, fig_height), facecolor='white')
                    ax2.set_facecolor('white'); ax2.grid(False)
                    for spine in ['top', 'bottom', 'left', 'right']:
                        ax2.spines[spine].set_linewidth(1.0); ax2.spines[spine].set_color('black')
                    ax2.tick_params(axis='both', which='major', labelsize=kin_tick_size, width=1.0, length=4, direction='in', color='black', top=kin_mirror, right=kin_mirror)
                    ax2.tick_params(axis='both', which='minor', width=0.8, length=2.5, direction='in', color='black', top=kin_mirror, right=kin_mirror)

                    # Apply tick locator settings
                    # X-Axis Ticks
                    if kin_x_major != "Auto":
                        ax2.xaxis.set_major_locator(ticker.MaxNLocator(nbins=int(kin_x_major), prune=None))
                    if kin_x_minor != "Auto":
                        n_minor = int(kin_x_minor)
                        if n_minor == 0:
                            ax2.xaxis.set_minor_locator(ticker.NullLocator())
                        else:
                            ax2.xaxis.set_minor_locator(ticker.AutoMinorLocator(n=n_minor + 1))
                    else:
                        ax2.xaxis.set_minor_locator(ticker.AutoMinorLocator())
                    
                    # Y-Axis Ticks
                    if kin_y_major != "Auto":
                        ax2.yaxis.set_major_locator(ticker.MaxNLocator(nbins=int(kin_y_major), prune=None))
                    if kin_y_minor != "Auto":
                        n_minor = int(kin_y_minor)
                        if n_minor == 0:
                            ax2.yaxis.set_minor_locator(ticker.NullLocator())
                        else:
                            ax2.yaxis.set_minor_locator(ticker.AutoMinorLocator(n=n_minor + 1))
                    else:
                        ax2.yaxis.set_minor_locator(ticker.AutoMinorLocator())


                    font_label_kin = {
                        'family': kin_font_family,
                        'size': kin_label_size,
                        'weight': kin_label_weight,
                        'style': kin_label_style
                    }
                    ax2.scatter(active_k['1000/T'], active_k['ln(Tau)'], s=kin_marker_size**2, alpha=0.8, edgecolors='black', linewidth=0.8, color='steelblue', zorder=3)

                    label_ea = (r"$E_\mathrm{a} = %.1f \pm %.1f\text{ kJ~mol}^{-1}$" + "\n" + r"$R^2 = %.4f$") % (Ea, Ea_stderr, r_sq) if show_ea_std else (r"$E_\mathrm{a} = %.1f\text{ kJ~mol}^{-1}$" + "\n" + r"$R^2 = %.4f$") % (Ea, r_sq)

                    if show_tv:
                        Tv_x = (ln_tau_t - intercept) / slope
                        min_x = min(active_k['1000/T'].min(), Tv_x); max_x = max(active_k['1000/T'].max(), Tv_x)
                        x_range = np.linspace(min_x * 0.95, max_x * 1.05, 100)
                        min_y = min(active_k['ln(Tau)'].min(), ln_tau_t); max_y = max(active_k['ln(Tau)'].max(), ln_tau_t)
                        if kin_custom_lims:
                            ax2.set_xlim(kin_xmin, kin_xmax)
                            ax2.set_ylim(kin_ymin, kin_ymax)
                        else:
                            ax2.set_xlim(min_x * 0.95, max_x * 1.05)
                            ax2.set_ylim(min_y - 0.5, max_y + 0.5)
                        ax2.plot([Tv_x], [ln_tau_t], marker='*', markersize=kin_marker_size * 2, color='gold', markeredgecolor='black', markeredgewidth=0.8, label=r"$T_\mathrm{v} = %.1f^\circ\text{C}$" % Tv_val, zorder=4)
                    else:
                        x_range = np.linspace(active_k['1000/T'].min() * 0.95, active_k['1000/T'].max() * 1.05, 100)
                        if kin_custom_lims:
                            ax2.set_xlim(kin_xmin, kin_xmax)
                            ax2.set_ylim(kin_ymin, kin_ymax)
                        else:
                            ax2.set_xlim(active_k['1000/T'].min() * 0.95, active_k['1000/T'].max() * 1.05)
                            ax2.set_ylim(active_k['ln(Tau)'].min() - 0.5, active_k['ln(Tau)'].max() + 0.5)

                    y_fit = slope * x_range + intercept
                    ax2.plot(x_range, y_fit, '--', color='red', linewidth=kin_line_width, label=label_ea, zorder=2)
                    ax2.set_xlabel(r"$1000/T$ ($\mathrm{K}^{-1}$)", fontdict=font_label_kin, labelpad=8)
                    ax2.set_ylabel(r"$\ln(\tau)$", fontdict=font_label_kin, labelpad=8)

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
                        ax2.legend(frameon=kin_leg_box, loc=l_pos, bbox_to_anchor=l_anchor, fontsize=kin_leg_font_size, ncol=kin_leg_ncol, columnspacing=1.0, handletextpad=0.5)

                    if panel_letter and len(panel_letter) == 1 and panel_letter.isalpha():
                        next_letter = chr(ord(panel_letter) + 1)
                        ax2.text(-0.12, 1.02, f"({next_letter})", transform=ax2.transAxes,
                                 fontfamily=panel_font_family, fontsize=panel_font_size,
                                 fontweight=panel_font_weight, fontstyle=panel_font_style,
                                 va='bottom', ha='right')

                    fig2.canvas.draw()
                    kin_num_family = kin_font_family if kin_tick_font == "Same as Label" else kin_tick_font
                    for label in ax2.get_xticklabels():
                        label.set_family(kin_num_family)
                        label.set_size(kin_tick_size)
                        label.set_weight(kin_tick_weight)
                        label.set_style(kin_tick_style)
                    for label in ax2.get_yticklabels():
                        label.set_family(kin_num_family)
                        label.set_size(kin_tick_size)
                        label.set_weight(kin_tick_weight)
                        label.set_style(kin_tick_style)

                    plt.tight_layout()
                    st.pyplot(fig2, dpi=300, bbox_inches='tight')

                    if pub_colorspace.startswith("CMYK"):
                        # Save figure as RGB PNG bytes first
                        buf_rgb_png = io.BytesIO()
                        fig2.savefig(buf_rgb_png, format='png', dpi=1200, bbox_inches='tight')
                        buf_rgb_png.seek(0)
                        
                        # Convert to CMYK using Pillow
                        from PIL import Image
                        img = Image.open(buf_rgb_png)
                        img_cmyk = img.convert('CMYK')
                        
                        # Save as CMYK PDF
                        buf_pdf2 = io.BytesIO()
                        img_cmyk.save(buf_pdf2, format='PDF', dpi=(1200, 1200))
                        buf_pdf2.seek(0)
                        
                        # Save as CMYK TIFF (lossless LZW compression)
                        buf_tiff2 = io.BytesIO()
                        img_cmyk.save(buf_tiff2, format='TIFF', dpi=(1200, 1200), compression='tiff_lzw')
                        buf_tiff2.seek(0)
                        
                        # Save as CMYK JPEG (high quality)
                        buf_jpg2 = io.BytesIO()
                        img_cmyk.save(buf_jpg2, format='JPEG', dpi=(300, 300), quality=95)
                        buf_jpg2.seek(0)
                        
                        da1, da2, da3 = st.columns(3)
                        with da1: st.download_button("\U0001f4e5 PDF (1200 DPI CMYK)", buf_pdf2, "Arrhenius_Plot_CMYK.pdf", key="dl_pdf_arr")
                        with da2: st.download_button("\U0001f4e5 TIFF (1200 DPI CMYK)", buf_tiff2, "Arrhenius_Plot_CMYK.tiff", key="dl_tiff_arr")
                        with da3: st.download_button("\U0001f4e5 JPEG (300 DPI CMYK)", buf_jpg2, "Arrhenius_Plot_CMYK.jpg", key="dl_jpg_arr")
                    else:
                        buf_pdf2 = io.BytesIO(); fig2.savefig(buf_pdf2, format='pdf', bbox_inches='tight'); buf_pdf2.seek(0)
                        buf_svg2 = io.BytesIO(); fig2.savefig(buf_svg2, format='svg', bbox_inches='tight'); buf_svg2.seek(0)
                        buf_png2 = io.BytesIO(); fig2.savefig(buf_png2, format='png', dpi=1200, bbox_inches='tight'); buf_png2.seek(0)
                        da1, da2, da3 = st.columns(3)
                        with da1: st.download_button("\U0001f4e5 PDF (Vector)", buf_pdf2, "Arrhenius_Plot.pdf", key="dl_pdf_arr")
                        with da2: st.download_button("\U0001f4e5 SVG (Vector)", buf_svg2, "Arrhenius_Plot.svg", key="dl_svg_arr")
                        with da3: st.download_button("\U0001f4e5 PNG (1200 DPI)", buf_png2, "Arrhenius_Plot.png", key="dl_png_arr")
                    plt.close(fig2)
                else:
                    st.warning("\u26a0\ufe0f Need at least 2 data points with 'Include' checked in the Analysis tab \u2192 Kinetics")
            else:
                st.info("\U0001f4ca Run kinetics analysis in the Analysis tab first, then return here.")
    else:
        st.info("\U0001f680 Run analysis first to generate publication figures")

# ==========================
# TAB 6: EDUCATION & THEORY

# --- MODULAR TABS ---
from can_relax.gui.components import render_education_tab, render_credits_tab

render_education_tab(tab_education)
render_credits_tab(tab_credits)
