import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import io
import re
import json
from scipy.optimize import curve_fit
from scipy.stats import linregress
from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor
import matplotlib.pyplot as plt

# ==========================================
# 1. CORE ENGINE (INTERNALIZED FROM can_relax)
# ==========================================

# --- A. ROBUST PARSER (The Fix) ---
def parse_wide_format_data(file_obj):
    """
    Parses wide-format CSV/Excel: Col 0 = Time, Cols 1..N = Data at Temp.
    Handles headers like '140', '140C', 'Temp 140'.
    """
    try:
        # 1. Read File
        if isinstance(file_obj, str): 
            if file_obj.endswith('.csv'): df = pd.read_csv(file_obj, header=None) # Read headerless first to inspect
            else: df = pd.read_excel(file_obj, header=None)
        else:
            if file_obj.name.endswith('.csv'): df = pd.read_csv(file_obj, header=None)
            else: df = pd.read_excel(file_obj, header=None)

        curves = {}
        
        # Check if it's the "Block Format" (Temp, Time, Modulus repeated)
        # Row 0 usually contains headers like "Temperature", "Step time", "Modulus" repeated
        # Row 1 might contain units or data.
        
        # Let's try to detect the structure.
        # Strategy: Iterate columns. If we find a "Temperature" column, grab the value from the first data row.
        
        # Convert to string to search for headers
        df_str = df.astype(str)
        
        # Find columns that look like "Step time" or "Time"
        time_cols = []
        mod_cols = []
        temp_vals = []
        
        # Reload with header=0 to get column names if standard
        if isinstance(file_obj, str):
             if file_obj.endswith('.csv'): df_main = pd.read_csv(file_obj)
             else: df_main = pd.read_excel(file_obj)
        else:
             file_obj.seek(0)
             if file_obj.name.endswith('.csv'): df_main = pd.read_csv(file_obj)
             else: df_main = pd.read_excel(file_obj)

        # LOGIC A: Block Format (Temp, Time, Modulus, Temp, Time, Modulus...)
        # In your specific file, it seems like:
        # Col 0: Temp (value 50 repeated), Col 1: Time, Col 2: Modulus
        # Col 3: Temp (value 90 repeated), Col 4: Time, Col 5: Modulus
        
        num_cols = df_main.shape[1]
        
        # Iterate in blocks of 3? Or check headers.
        # Your headers are: "Temperature", "Step time", "Modulus", "Temperature", "Step time", "Modulus"...
        
        # Identify triplets
        for i in range(0, num_cols, 3):
            if i+2 < num_cols:
                # Assume Col i is Temp, i+1 is Time, i+2 is Modulus
                # Check if headers match roughly
                h1 = str(df_main.columns[i]).lower()
                h2 = str(df_main.columns[i+1]).lower()
                h3 = str(df_main.columns[i+2]).lower()
                
                if "temp" in h1 and ("time" in h2 or "s" in h2) and ("modulus" in h3 or "pa" in h3 or "stress" in h3):
                    # Extract Temperature from the first row of data (since it's repeated)
                    try:
                        temp_val = float(df_main.iloc[0, i])
                        
                        t_data = pd.to_numeric(df_main.iloc[:, i+1], errors='coerce').values
                        g_data = pd.to_numeric(df_main.iloc[:, i+2], errors='coerce').values
                        
                        mask = ~np.isnan(t_data) & ~np.isnan(g_data) & (t_data > 0)
                        if np.sum(mask) > 5:
                            curves[temp_val] = pd.DataFrame({'t': t_data[mask], 'g': g_data[mask]})
                    except: pass

        # LOGIC B: Standard Wide Format (Time, Temp1, Temp2...) - Fallback
        if not curves:
            # Assume Col 0 is Time
            t_col = df_main.iloc[:, 0].values
            for col in df_main.columns[1:]:
                match = re.search(r"(\d+(\.\d+)?)", str(col))
                if match:
                    temp_val = float(match.group(1))
                    g_data = df_main[col].values
                    curves[temp_val] = pd.DataFrame({'t': t_col, 'g': g_data})

        return curves
    except Exception as e: 
        st.error(f"Parser Error: {e}")
        return {}

# --- B. PHYSICS MODELS ---
class Maxwell:
    def func(self, t, tau): return np.exp(-t/tau)
    def get_initial_guess(self, t, g): return [np.mean(t)]

class SingleKWW:
    def func(self, t, tau, beta): return np.exp(-(t/tau)**beta)
    def get_initial_guess(self, t, g): return [np.mean(t), 0.8]

class DualKWW:
    def func(self, t, f, tau1, beta1, tau2, beta2): 
        return f * np.exp(-(t/tau1)**beta1) + (1-f) * np.exp(-(t/tau2)**beta2)
    def get_initial_guess(self, t, g): 
        return [0.5, np.mean(t)/10, 0.8, np.mean(t)*10, 0.9]

# --- C. ANALYZER ---
class CurveAnalyzer:
    def __init__(self):
        self.models = {'Maxwell': Maxwell(), 'Single_KWW': SingleKWW(), 'Dual_KWW': DualKWW()}

    def fit_one_temp(self, temp, df, Tg=None):
        # RELAXED Tg CHECK: Only skip if strictly LESS than Tg (allow equal)
        if Tg is not None and temp < Tg: return {'Valid': False}
        
        t = df['t'].values; g = df['g'].values
        
        # Normalize
        g0 = g[0] if g[0] > 0 else 1.0
        g_norm = g / g0
        
        fits = {}
        for name, model in self.models.items():
            try:
                p0 = model.get_initial_guess(t, g_norm)
                bounds = (0, np.inf)
                if name == "Single_KWW": bounds = ([0, 0.1], [np.inf, 1.0])
                elif name == "Dual_KWW": bounds = ([0, 0, 0.1, 0, 0.1], [1, np.inf, 1.0, np.inf, 1.0])
                
                popt, _ = curve_fit(model.func, t, g_norm, p0=p0, bounds=bounds, maxfev=5000)
                g_fit = model.func(t, *popt) * g0
                fits[name] = {'popt': popt, 'curve': g_fit}
            except: pass
        
        return {
            'Valid': True, 'Temp': temp,
            'Raw': {'t': t, 'g': g}, 'Fits': fits
        }

# --- D. SPECTRUM ANALYZER ---
class SpectrumAnalyzer:
    def compute_continuous_spectrum(self, t, g, num_modes=50, alpha=0.1):
        g_norm = g / g[0]
        log_min, log_max = np.log10(min(t)), np.log10(max(t))
        tau_grid = np.logspace(log_min-1, log_max+1, num_modes)
        A = np.exp(-t[:, None] / tau_grid[None, :])
        clf = Ridge(alpha=alpha, fit_intercept=False, positive=True)
        clf.fit(A, g_norm)
        return tau_grid, clf.coef_

# --- E. SIMULATOR ---
class MaterialSimulator:
    def simulate_curve(self, T, model_name, p):
        R = 8.314
        try:
            # Calculate Tau based on Tv/Ea logic
            # tau(Tv) = 1e6/G (if G in MPa). 
            # tau0 = tau(Tv) / exp(Ea/RTv)
            tau_v = 1e6 / p['G_plateau'] 
            term_tv = np.exp((p['Ea']*1000/R) * (1/(p['Tv']+273.15)))
            tau0 = tau_v / term_tv
            
            # Tau at T
            term_t = np.exp((p['Ea']*1000/R) * (1/(T+273.15)))
            tau_T = tau0 * term_t
            
            t = np.logspace(np.log10(tau_T)-3, np.log10(tau_T)+2, 100)
            
            if model_name == 'Maxwell':
                g = p['G_plateau'] * np.exp(-t/tau_T)
            elif model_name == 'Single_KWW':
                g = p['G_plateau'] * np.exp(-(t/tau_T)**p['beta'])
            elif model_name == 'Dual_KWW':
                tau1 = tau_T / np.sqrt(p['tau_factor'])
                tau2 = tau_T * np.sqrt(p['tau_factor'])
                g = p['G_plateau'] * (p['fraction_fast']*np.exp(-(t/tau1)**0.8) + (1-p['fraction_fast'])*np.exp(-(t/tau2)**p['beta_2']))
            else: g = t*0
            
            return t, g, tau_T
        except:
            return np.array([1]), np.array([1]), 1

class TTSEngine:
    def __init__(self):
        pass

    def generate_mastercurve(self, results, ref_temp=None):
        """
        Shifts curves horizontally to create a Mastercurve.
        Shift Factor a_T = tau(T) / tau(T_ref)
        """
        if not results: return None
        
        # 1. Sort results by Temperature
        sorted_res = sorted(results, key=lambda x: x['Temp'])
        
        # 2. Pick Reference Temperature (middle temp usually best, or user defined)
        if ref_temp is None:
            # Default to the one in the middle
            mid_idx = len(sorted_res) // 2
            ref_res = sorted_res[mid_idx]
        else:
            # Find closest
            ref_res = min(sorted_res, key=lambda x: abs(x['Temp'] - ref_temp))
            
        T_ref = ref_res['Temp']
        
        # Get Ref Tau (from the Best Model fit)
        def get_tau(res):
            best = res.get('Best_Model', 'Single_KWW')
            if best not in res.get('Fits', {}):
                return 1.0
            popt = res['Fits'][best]['popt']
            if best == 'Maxwell': return popt[0]  # Maxwell: tau is index 0
            if best == 'Single_KWW': return popt[0]  # Single_KWW: tau is index 0
            if best == 'Dual_KWW': return popt[1]  # Dual_KWW: tau1 is index 1
            return 1.0

        tau_ref = get_tau(ref_res)
        
        master_t = []
        master_g = []
        shift_factors = {}
        
        for res in sorted_res:
            T = res['Temp']
            tau = get_tau(res)
            
            # Calculate Shift Factor a_T
            aT = tau / tau_ref
            shift_factors[T] = aT
            
            # Shift Time: t_master = t / aT
            t_shifted = res['Raw']['t'] / aT
            g_raw = res['Raw']['g']
            
            master_t.append(t_shifted)
            master_g.append(g_raw)
            
        # Concatenate
        full_t = np.concatenate(master_t)
        full_g = np.concatenate(master_g)
        
        # Sort for plotting
        sort_idx = np.argsort(full_t)
        
        return {
            "T_ref": T_ref,
            "Master_t": full_t[sort_idx],
            "Master_g": full_g[sort_idx],
            "Shifts": shift_factors
        }

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
    st.sidebar.header("1. Data Input")
    uploaded_file = st.sidebar.file_uploader("Upload Data (CSV/XLSX)", type=["csv", "xlsx"])

    # --- MATERIAL ONTOLOGY ---
    with st.sidebar.expander("🧬 Material DNA", expanded=True):
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
            
        # UPGRADE: Add Chemistry Tags here as requested
        st.markdown("**Exchange Chemistry**")
        chem_tags = st.multiselect("Mechanism", ["Transesterification", "Disulfide", "Imine", "Boronic Ester", "Urethane"], default=["Transesterification"])

    st.sidebar.header("2. Physics")
    G_prime_input = st.sidebar.number_input("Rubbery G' (MPa)", 0.01, 5000.0, 1.0, help="Used for Tv calculation")
    Tg_input = st.sidebar.number_input("Tg (Glass Transition) °C", value=50.0, help="Skips fitting below this temp")
    
    st.sidebar.markdown("---")
    st.sidebar.header("3. Fitting")
    fit_model = st.sidebar.selectbox("Model", ["Maxwell", "Single_KWW", "Dual_KWW"])
    kinetics_mode = st.sidebar.radio("Kinetics Base:", ["Fit Parameter", "Raw 1/e"])
    run_btn = st.sidebar.button("Run Analysis", type="primary")

    # PROCESS
    if uploaded_file and run_btn:
        # Use Internal Parser
        curves = parse_wide_format_data(uploaded_file)
        
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

        t1, t2, t3, t4 = st.tabs(["Curves", "Kinetics", "Mastercurve", "🌈 Spectrum"])
        
        # 1. CURVES
        with t1:
            c_plot, c_settings = st.columns([3, 1])
            with c_settings:
                time_axis_type = st.radio("Scale", ["Log", "Linear"])
                show_fits = st.checkbox("Fits", True)
            with c_plot:
                fig = go.Figure()
                for r in active_results:
                    t_raw = r['Raw']['t']
                    g_raw = r['Raw']['g']
                    
                    # Normalize G(t) / G(0)
                    if len(g_raw) > 0 and g_raw[0] != 0:
                        g_norm = g_raw / g_raw[0]
                    else:
                        g_norm = g_raw
                        
                    # Decimate for speed
                    step = max(1, len(t_raw)//50)
                    
                    # Plot Normalized Data
                    fig.add_trace(go.Scatter(
                        x=t_raw[::step], 
                        y=g_norm[::step], 
                        mode='markers', 
                        name=f"{r['Temp']}C", 
                        marker=dict(size=6, opacity=0.8)
                    ))
                    
                    if show_fits and fit_model in r['Fits']:
                        # The fit curve is un-normalized in the analyzer (g_fit = func * g0)
                        # So we need to normalize it back for display: g_fit / g0
                        g_fit_raw = r['Fits'][fit_model]['curve']
                        if len(g_raw) > 0 and g_raw[0] != 0:
                            g_fit_norm = g_fit_raw / g_raw[0]
                        else:
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
                fig.update_yaxes(title="G(t)/G₀") # Updated label
                fig.update_layout(height=500, margin=dict(l=20,r=20,t=20,b=20))
                st.plotly_chart(fig, width="stretch")

        # 2. KINETICS
        with t2:
            k_data = []
            for r in active_results:
                t_val = np.nan
                if kinetics_mode == "Raw 1/e": t_val = r.get('Tau_1e', np.nan)
                elif fit_model in r['Fits']:
                    p = r['Fits'][fit_model]['popt']
                    idx = 2 if fit_model == 'Dual_KWW' else 0 # 0 for Single KWW/Maxwell (tau is usually first)
                    if fit_model == "Single_KWW": idx = 0
                    if fit_model == "Maxwell": idx = 0
                    if fit_model == "Dual_KWW": idx = 3 # Tau 2
                    t_val = p[idx]
                if t_val > 0:
                    k_data.append({"Include": True, "Temp": r['Temp'], "1000/T": 1000.0/(r['Temp']+273.15), "Tau": t_val, "ln(Tau)": np.log(t_val), "Type": "Main"})

            if k_data:
                df_k = pd.DataFrame(k_data)
                col_edit, col_chart = st.columns([1, 2])
                with col_edit:
                    st.markdown("##### Outlier Rejection")
                    edited_df = st.data_editor(df_k, column_config={"Include": st.column_config.CheckboxColumn("Fit?", default=True)}, hide_index=True, height=400, width="stretch")
                    st.session_state.kinetics_df = edited_df

                with col_chart:
                    active = edited_df[edited_df["Include"] == True]
                    if len(active) >= 2:
                        slope, intercept, r_sq, _, _ = linregress(active["1000/T"], active["ln(Tau)"])
                        Ea = slope * 8.314462
                        G_Pa = G_prime_input * 1e6; tau_target = 1e12 / G_Pa; ln_tau_t = np.log(tau_target)
                        if slope != 0: Tv_val = (1000.0 / ((ln_tau_t - intercept)/slope)) - 273.15
                        else: Tv_val = 0
                        
                        fig_k = go.Figure()
                        fig_k.add_trace(go.Scatter(x=active["1000/T"], y=active["ln(Tau)"], mode='markers', name="Data"))
                        xr = np.linspace(active["1000/T"].min()*0.95, active["1000/T"].max()*1.05, 10)
                        fig_k.add_trace(go.Scatter(x=xr, y=slope*xr+intercept, mode='lines', name=f"Ea={Ea:.1f} kJ", line=dict(dash='dash', color='red')))
                        fig_k.add_trace(go.Scatter(x=[(ln_tau_t - intercept)/slope], y=[ln_tau_t], mode='markers', marker=dict(symbol='star', size=14, color='gold'), name=f"Tv={Tv_val:.1f}C"))
                        st.metric("Results", f"Tv: {Tv_val:.1f} °C", f"Ea: {Ea:.1f} kJ/mol")
                        fig_k.update_layout(xaxis_title="1000/T", yaxis_title="ln(tau)", height=500)
                        st.plotly_chart(fig_k, width="stretch")
                    else:
                        st.warning("Need more points")

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
                        st.plotly_chart(fig_mc, use_container_width=True)
                        
                        # Display shift factors
                        st.markdown("##### Shift Factors (aT)")
                        shifts_df = pd.DataFrame([
                            {"Temperature (°C)": T, "log(aT)": np.log10(aT), "aT": f"{aT:.2e}"}
                            for T, aT in master['Shifts'].items()
                        ])
                        st.dataframe(shifts_df, hide_index=True, use_container_width=True)
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
                    model_map = {'Maxwell': Maxwell(), 'Single_KWW': SingleKWW(), 'Dual_KWW': DualKWW()}
                    model_obj = model_map[sim_model]
                    try:
                        p0 = model_obj.get_initial_guess(t, g_true/g_true[0])
                        popt, _ = curve_fit(model_obj.func, t, g_true/g_true[0], p0=p0, maxfev=5000)
                        if sim_model=='Maxwell': t_fit=popt[0]
                        elif sim_model=='Single_KWW': t_fit=popt[0]
                        elif sim_model=='Dual_KWW': t_fit=popt[3]
                        else: t_fit=0
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
    
    # Create 6 expanders for sample input
    sample_results = {}
    num_samples = min(6, len(st.session_state.comparison_samples) + 1)
    
    for sample_idx in range(1, 7):
        sample_key = f"sample_{sample_idx}"
        
        with st.expander(f"📌 Sample {sample_idx}", expanded=(sample_idx==1)):
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
    if st.button("🔍 Analyze All Samples", type="primary", use_container_width=True):
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
        
        st.dataframe(results_df, hide_index=True, use_container_width=True)
        
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
            
            st.plotly_chart(fig_comp, use_container_width=True)
        
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
    st.header("📝 Publication Figures")
    if 'active_results' in st.session_state and st.session_state.active_results:
        active_res = st.session_state.active_results
        kinetics_df = st.session_state.get('kinetics_df', pd.DataFrame())
        
        with st.expander("⚙️ Figure Settings", expanded=True):
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                fig_style = st.selectbox("Style", ["Classic (Origin)", "Modern"])
                fig_fmt = st.selectbox("Format", ["png", "pdf", "svg"])
            with c2:
                fig_width = st.number_input("Width (in)", 2.0, 10.0, 3.5, 0.1)
                fig_height = st.number_input("Height (in)", 2.0, 10.0, 3.0, 0.1)
            with c3:
                fig_dpi = st.number_input("DPI", 72, 1200, 300, 50)
                pub_time_axis = st.selectbox("Time Scale", ["Log", "Linear"])
            with c4:
                show_legend = st.checkbox("Legend", value=True)
                show_fit_pub = st.checkbox("Show Fits", value=False)

        # Matplotlib Export Logic
        col_relax, col_arr = st.columns(2)
        
        with col_relax:
            st.subheader("📊 Relaxation Curves")
            fig1, ax1 = plt.subplots(figsize=(fig_width, fig_height))
            
            # Use matplotlib color cycle
            colors = plt.cm.tab10(np.linspace(0, 1, len(active_res)))
            
            for idx, r in enumerate(active_res):
                t_raw = r['Raw']['t']
                g_raw = r['Raw']['g']
                
                # Normalize G(t) / G(0)
                if len(g_raw) > 0 and g_raw[0] != 0:
                    g_norm = g_raw / g_raw[0]
                else:
                    g_norm = g_raw
                
                # Decimate for cleaner plot
                step = max(1, len(t_raw)//50)
                
                ax1.plot(t_raw[::step], g_norm[::step], 'o', alpha=0.7, 
                        label=f"{r['Temp']}°C", color=colors[idx], markersize=5)
                
                # Add fit if requested
                if show_fit_pub and 'Best_Model' in r:
                    fit_model = r['Best_Model']
                    if fit_model in r['Fits']:
                        g_fit_raw = r['Fits'][fit_model]['curve']
                        if len(g_raw) > 0 and g_raw[0] != 0:
                            g_fit_norm = g_fit_raw / g_raw[0]
                        else:
                            g_fit_norm = g_fit_raw
                        ax1.plot(t_raw, g_fit_norm, '--', color=colors[idx], linewidth=1.5, alpha=0.8)
            
            # Formatting
            if pub_time_axis == "Log":
                ax1.set_xscale('log')
            ax1.set_xlabel("Time (s)", fontsize=11, fontweight='bold')
            ax1.set_ylabel("G(t) / G₀", fontsize=11, fontweight='bold')
            ax1.grid(True, alpha=0.3, linestyle='--')
            if show_legend:
                ax1.legend(frameon=True, loc='best', fontsize=9)
            ax1.tick_params(labelsize=10)
            plt.tight_layout()
            
            st.pyplot(fig1)
            buf1 = io.BytesIO()
            fig1.savefig(buf1, format=fig_fmt, dpi=fig_dpi, bbox_inches='tight')
            buf1.seek(0)
            st.download_button("📥 Download Relaxation Figure", buf1, f"Relaxation_Curves.{fig_fmt}", key="dl_relax")
            
        with col_arr:
            st.subheader("🔥 Arrhenius Plot")
            if not kinetics_df.empty:
                active_k = kinetics_df[kinetics_df['Include']==True]
                if not active_k.empty and len(active_k) >= 2:
                    # Calculate Arrhenius fit
                    slope, intercept, r_val, _, _ = linregress(active_k['1000/T'], active_k['ln(Tau)'])
                    r_sq = r_val**2
                    Ea = slope * 8.314462  # kJ/mol
                    
                    # Calculate Tv
                    G_Pa = G_prime_input * 1e6
                    tau_target = 1e12 / G_Pa
                    ln_tau_t = np.log(tau_target)
                    if slope != 0:
                        Tv_val = (1000.0 / ((ln_tau_t - intercept)/slope)) - 273.15
                    else:
                        Tv_val = 0
                    
                    fig2, ax2 = plt.subplots(figsize=(fig_width, fig_height))
                    
                    # Plot data points
                    ax2.scatter(active_k['1000/T'], active_k['ln(Tau)'], 
                               s=80, alpha=0.8, edgecolors='black', linewidth=1.5, 
                               color='steelblue', zorder=3)
                    
                    # Plot fit line
                    x_range = np.linspace(active_k['1000/T'].min()*0.95, 
                                         active_k['1000/T'].max()*1.05, 100)
                    y_fit = slope * x_range + intercept
                    ax2.plot(x_range, y_fit, '--', color='red', linewidth=2, 
                            label=f'Eₐ = {Ea:.1f} kJ/mol\nR² = {r_sq:.4f}', zorder=2)
                    
                    # Plot Tv extrapolation
                    Tv_x = (ln_tau_t - intercept) / slope
                    ax2.plot([Tv_x], [ln_tau_t], marker='*', markersize=18, 
                            color='gold', markeredgecolor='black', markeredgewidth=1.5,
                            label=f'Tᵥ = {Tv_val:.1f}°C', zorder=4)
                    
                    # Formatting
                    ax2.set_xlabel("1000/T (K⁻¹)", fontsize=11, fontweight='bold')
                    ax2.set_ylabel("ln(τ)", fontsize=11, fontweight='bold')
                    ax2.grid(True, alpha=0.3, linestyle='--')
                    if show_legend:
                        ax2.legend(frameon=True, loc='best', fontsize=9)
                    ax2.tick_params(labelsize=10)
                    plt.tight_layout()
                    
                    st.pyplot(fig2)
                    
                    # Display metrics
                    col_m1, col_m2, col_m3 = st.columns(3)
                    with col_m1:
                        st.metric("Activation Energy", f"{Ea:.1f} kJ/mol")
                    with col_m2:
                        st.metric("Tᵥ (Volkov)", f"{Tv_val:.1f} °C")
                    with col_m3:
                        st.metric("R²", f"{r_sq:.4f}")
                    
                    buf2 = io.BytesIO()
                    fig2.savefig(buf2, format=fig_fmt, dpi=fig_dpi, bbox_inches='tight')
                    buf2.seek(0)
                    st.download_button("📥 Download Arrhenius Figure", buf2, f"Arrhenius_Plot.{fig_fmt}", key="dl_arr")
                else:
                    st.warning("⚠️ Need at least 2 data points with 'Include' checked in Analysis tab")
            else:
                st.info("📊 Run kinetics analysis in Analysis tab first")
    else: 
        st.info("🚀 Run analysis first to generate publication figures")

# ==========================
# TAB 6: EDUCATION & THEORY
# ==========================
with tab_education:
    st.header("📚 Educational & Scientific Foundation")
    
    edu_tabs = st.tabs([
        "🔬 Relaxation Models",
        "🌡️ Temperature Kinetics",
        "🧪 Vitrimer Chemistry",
        "📊 Model Comparison",
        "📖 References"
    ])
    
    # ====== TAB 1: RELAXATION MODELS ======
    with edu_tabs[0]:
        st.subheader("Stress Relaxation Models")
        
        st.markdown("""
        When a material is subjected to **constant strain** $\\varepsilon_0$, the stress decays over time. 
        The **relaxation modulus** describes this decay:
        
        $$G(t) = \\frac{\\sigma(t)}{\\varepsilon_0}$$
        
        Different materials exhibit different relaxation behaviors, described by mathematical models below.
        """)
        
        # Maxwell Model
        st.markdown("#### 1️⃣ Maxwell Model")
        st.latex(r"G(t) = G_0 \exp\left(-\frac{t}{\tau}\right)")
        st.markdown("""
        **Physical Interpretation:**
        - Single relaxation time $\\tau$
        - Assumes liquid-like behavior with one dominant relaxation process
        - Characteristic time: material relaxes to 37% ($1/e \\approx 0.368$) of initial value at $t = \\tau$
        
        **Parameters:**
        - $G_0$: Initial modulus (Pa)
        - $\\tau$: Relaxation time (s)
        
        **Applications:**
        - Simple polymers above glass transition
        - Newtonian liquids
        - First-order approximation for complex systems
        
        **Limitations:**
        - Assumes instantaneous strain response (no elasticity before relaxation)
        - Real polymers show broader distribution of relaxation times
        """)
        
        # KWW Model
        st.markdown("#### 2️⃣ Kohlrausch-Williams-Watts (KWW) Model")
        st.latex(r"G(t) = G_0 \exp\left[-\left(\frac{t}{\tau}\right)^{\beta}\right]")
        st.markdown("""
        **Physical Interpretation:**
        - **Stretched exponential** captures heterogeneous relaxation
        - $\\beta$ parameter quantifies non-exponential behavior
        - Accounts for **distribution of relaxation times** (polydispersity)
        
        **Parameters:**
        - $G_0$: Initial modulus (Pa)
        - $\\tau$: Characteristic time (s)
        - $\\beta$: Stretching exponent (0 < $\\beta$ ≤ 1)
        
        **Interpretation of $\\beta$:**
        | $\\beta$ | Meaning | Example |
        |---------|---------|---------|
        | $\\beta = 1.0$ | Single relaxation time (recovers Maxwell) | Ideal liquid |
        | $0.7 < \\beta < 1.0$ | Narrow distribution | Linear polymers |
        | $0.4 < \\beta < 0.7$ | Broad distribution | Branched polymers |
        | $\\beta < 0.4$ | Very broad distribution | Glassy polymers |
        
        **Applications:**
        - Amorphous polymers
        - Complex fluids
        - Glassy systems
        - Better fit for real experimental data
        """)
        
        # Dual KWW Model
        st.markdown("#### 3️⃣ Dual-Mode KWW (Prony-like) Model")
        st.latex(r"G(t) = G_0 \left[ f \exp\left[-\left(\frac{t}{\tau_1}\right)^{\beta_1}\right] + (1-f) \exp\left[-\left(\frac{t}{\tau_2}\right)^{\beta_2}\right] \right]")
        st.markdown("""
        **Physical Interpretation:**
        - **Superposition** of two independent relaxation processes
        - Fast mode ($\\tau_1$, $\\beta_1$): Local chain motion / exchange reactions
        - Slow mode ($\\tau_2$, $\\beta_2$): Cooperative relaxation / long-chain effects
        
        **Parameters:**
        - $f$: Fraction of fast mode (0 < $f$ < 1)
        - $\\tau_1, \\tau_2$: Time scales (s)
        - $\\beta_1, \\beta_2$: Stretching exponents
        
        **Physical Basis:**
        - **Vitrimers**: Fast mode = transesterification kinetics
        - **Block copolymers**: Fast = block motion, Slow = interface dynamics
        - **Filled polymers**: Fast = matrix, Slow = filler-matrix interaction
        
        **Advantages:**
        - Captures complex multi-scale dynamics
        - Better R² fit for polydisperse systems
        - Physically meaningful separation of processes
        """)
        
        st.info("✅ **CAN-Relax Implements**: Maxwell, Single-KWW, and Dual-KWW models with automatic model selection")
    
    # ====== TAB 2: TEMPERATURE KINETICS ======
    with edu_tabs[1]:
        st.subheader("Temperature-Dependent Relaxation Kinetics")
        
        st.markdown("""
        Relaxation times are **highly temperature-dependent**. Different models describe this behavior:
        """)
        
        # Arrhenius
        st.markdown("#### 🔴 Arrhenius Model (High Temperature)")
        st.latex(r"\tau(T) = \tau_0 \exp\left(\frac{E_a}{R T}\right)")
        st.markdown("""
        **Linear form** (most useful for analysis):
        $$\\ln(\\tau) = \\ln(\\tau_0) + \\frac{E_a}{R T}$$
        
        Or equivalently:
        $$\\ln(\\tau) = \\ln(\\tau_0) + \\frac{E_a}{R} \\left(\\frac{1}{T}\\right)$$
        
        **Plot:** $\\ln(\\tau)$ vs $1000/T$ gives **linear slope** $= E_a / (1000 R)$
        
        **Parameters:**
        - $E_a$: Activation energy (kJ/mol) — typical range: 20-300 kJ/mol
        - $\\tau_0$: Pre-exponential factor (s)
        - $R = 8.314$ J/(mol·K): Gas constant
        - $T$: Absolute temperature (K)
        
        **Typical Ranges:**
        | Material Class | $E_a$ (kJ/mol) | Valid T Range |
        |---|---|---|
        | Silicone polymers | 30-60 | $T_g + 50°C$ and above |
        | Epoxy vitrimers | 80-150 | $T_g + 40°C$ and above |
        | Polyethylene | 80-120 | Rubbery plateau region |
        | Cross-linked polymers | 100-200 | Above network Tg |
        
        **When to use:**
        - Data well above glass transition ($T \\gtrsim T_g + 50°C$)
        - Linear Arrhenius plot
        - Temperature range doesn't approach $T_g$
        """)
        
        # VFT
        st.markdown("#### 🔵 Vogel-Fulcher-Tammann (VFT) Model (Near Glass Transition)")
        st.latex(r"\ln(\tau) = \ln(\tau_0) + \frac{B}{T - T_0}")
        st.markdown("""
        **Physical Meaning:**
        - $T_0$: **Ideal glass transition temperature** (usually $T_0 \\approx T_g - 50$°C)
        - Accounts for **non-linear curvature** near $T_g$
        - Relaxation time → ∞ as $T$ → $T_0$ (system "freezes")
        
        **Parameters:**
        - $\\tau_0$: Pre-exponential factor (s)
        - $B$: Steepness parameter (K) — larger $B$ = steeper rise near $T_g$
        - $T_0$: Ideal glass temperature (K)
        
        **When to use:**
        - Data spanning across and near $T_g$
        - Curved Arrhenius plot
        - Strongly temperature-sensitive materials (vitrimers, polymer blends)
        
        **Comparison:**
        | Property | Arrhenius | VFT |
        |---|---|---|
        | **Valid range** | $T \\gg T_g$ | $T_0 < T < T_g + 100°C$ |
        | **Shape** | Linear in semi-log | Curved |
        | **Parameters** | 2 ($E_a$, $\\tau_0$) | 3 ($B$, $T_0$, $\\tau_0$) |
        | **Physics** | Simple activation | Complex cooperative motion |
        """)
        
        st.markdown("#### 🎯 Comparison Plot: Arrhenius vs VFT")
        
        # Generate comparison plot
        T_range = np.linspace(300, 450, 100)
        tau_arr = np.exp(np.log(1e-6) + (80000/8.314) * (1/T_range - 1/373.15))
        tau_vft = np.exp(np.log(1e-6) + 2000/(T_range - 323.15))
        
        fig_comp, ax_comp = plt.subplots(figsize=(8, 5))
        ax_comp.semilogy(T_range - 273.15, tau_arr, 'o-', linewidth=2.5, markersize=4, label='Arrhenius ($E_a = 80$ kJ/mol)', color='#EF553B')
        ax_comp.semilogy(T_range - 273.15, tau_vft, 's-', linewidth=2.5, markersize=4, label='VFT ($B = 2000$ K)', color='#636EFA')
        ax_comp.axvline(x=50, color='gray', linestyle='--', alpha=0.6, label='Approximate $T_g$')
        ax_comp.set_xlabel('Temperature (°C)', fontsize=12, fontweight='bold')
        ax_comp.set_ylabel('Relaxation Time τ (s)', fontsize=12, fontweight='bold')
        ax_comp.set_title('Temperature Dependence: Arrhenius vs VFT', fontsize=13, fontweight='bold')
        ax_comp.grid(True, alpha=0.3, which='both')
        ax_comp.legend(fontsize=11, loc='upper left')
        ax_comp.set_ylim([1e-8, 1e4])
        plt.tight_layout()
        st.pyplot(fig_comp)
        
        st.markdown("""
        **Key Observations:**
        - VFT shows **stronger curvature** near $T_g$ (50°C in this example)
        - Arrhenius remains linear across the entire range
        - For **vitrimers near exchange threshold**, VFT is more appropriate
        """)
    
    # ====== TAB 3: VITRIMER CHEMISTRY ======
    with edu_tabs[2]:
        st.subheader("Vitrimer Exchange Kinetics & Mechanisms")
        
        st.markdown("""
        **Vitrimers** are dynamic polymers with exchangeable cross-links. Unlike traditional cross-linked polymers,
        they can flow and be reprocessed through **transesterification or other exchange reactions**.
        """)
        
        st.markdown("#### 🔄 Common Exchange Mechanisms")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**1. Transesterification (Ester Exchange)**")
            st.latex(r"R_1-C(=O)-O-R_2 + R_3-OH \rightleftharpoons R_1-C(=O)-O-R_3 + R_2-OH")
            st.markdown("""
            - **Catalyst**: Usually acid, base, or metal catalysts
            - **Example materials**: Epoxy-anhydride, polyester
            - **Temperature range**: 100-200°C
            - **Kinetics**: Typically 1st or 2nd order
            """)
        
        with col2:
            st.markdown("**2. Disulfide Exchange (Bond Exchange)**")
            st.latex(r"R-S-S-R' + R''-SH \rightleftharpoons R-S-S-R'' + R'-SH")
            st.markdown("""
            - **Catalyst**: Disulfide-containing species
            - **Example materials**: Polysulfide-based vitrimers
            - **Temperature range**: 80-150°C
            - **Kinetics**: Nucleophilic substitution
            """)
        
        st.markdown("#### ⚛️ Relaxation Mechanism in Vitrimers")
        st.markdown("""
        **Two-timescale process:**
        
        1. **Short timescale** ($\\tau_1 \\sim$ ms-s): Glassy/rubbery relaxation (no chain motion)
        2. **Long timescale** ($\\tau_2 \\sim$ s-hours): **Exchange-induced flow**
        
        The **Dual-KWW model** captures this:
        - Fast component ($\\tau_1, \\beta_1$): Inherent polymer relaxation
        - Slow component ($\\tau_2, \\beta_2$): Stress relaxation due to bond exchange
        
        **Key insight**: $\\tau_2$ is **kinetically controlled** by reaction rates, not just molecular weight!
        
        $$\\tau_2 \\propto \\frac{1}{k_{exchange}} \\propto \\exp\\left(\\frac{E_a}{RT}\\right)$$
        
        This explains why vitrimers show **VFT-like or Arrhenius behavior** despite being amorphous.
        """)
        
        st.markdown("#### 📊 Vitrimer vs Thermoset vs Thermoplastic")
        
        comparison_df = pd.DataFrame({
            'Property': ['Reversibility', 'Reprocessability', 'Stress Relaxation', 'Typical τ@T_g+50', 'Model Fit'],
            'Thermoset': ['❌ Irreversible', '❌ Cannot remold', '🔴 No relaxation', '$\\infty$ (frozen)', 'N/A'],
            'Vitrimer': ['✅ Reversible exchange', '✅ Can remold', '🟡 Slow (hrs)', '100-10000 s', 'Dual-KWW'],
            'Thermoplastic': ['✅ Reversible chain', '✅ Can remold', '✅ Fast (mins)', '1-100 s', 'Single-KWW']
        })
        
        st.dataframe(comparison_df, hide_index=True, use_container_width=True)
        
        st.markdown("""
        **Temperature Effect on Vitrimer Exchange:**
        
        $$k_{exchange}(T) = k_0 \\exp\\left(-\\frac{E_{a,exchange}}{RT}\\right)$$
        
        - **Low T** ($T < T_{exchange}$): Exchange frozen, behaves like thermoset
        - **Mid T** ($T_{exchange} < T < T_g + 50°C$): Slow exchange, plastic behavior
        - **High T** ($T > T_g + 50°C$): Fast exchange, liquid-like behavior
        """)
    
    # ====== TAB 4: MODEL COMPARISON ======
    with edu_tabs[3]:
        st.subheader("Comparing Relaxation Models: Examples & Decision Tree")
        
        st.markdown("#### 📊 When to Use Which Model?")
        
        decision_tree = """
        ```
        START: Relaxation curve analysis
        │
        ├─ Is R² for Maxwell > 0.95?
        │  ├─ YES → Use MAXWELL
        │  │        (Simple liquid-like behavior)
        │  │
        │  └─ NO → Continue...
        │
        ├─ Is R² for Single-KWW > 0.98?
        │  ├─ YES → Use SINGLE-KWW
        │  │        (Monodisperse relaxation)
        │  │        Check β: if β > 0.85 → nearly exponential
        │  │              if β < 0.75 → broad distribution
        │  │
        │  └─ NO → Continue...
        │
        └─ Use DUAL-KWW
           (Multiple relaxation mechanisms detected)
           Interpret: Fast mode + Slow mode
                      (e.g., glassy + exchange in vitrimer)
        ```
        """
        st.code(decision_tree, language=None)
        
        st.markdown("#### 🔬 Simulated Examples: Model Comparison")
        
        # Create synthetic data comparing models
        t = np.logspace(-4, 2, 200)
        
        # Parameters
        G0 = 1.0
        tau_m = 10.0
        tau_kww = 15.0
        beta_kww = 0.85
        tau1_dual = 5.0
        beta1_dual = 0.9
        tau2_dual = 100.0
        beta2_dual = 0.7
        f_dual = 0.4
        
        # Generate curves
        g_maxwell = G0 * np.exp(-t/tau_m)
        g_kww = G0 * np.exp(-(t/tau_kww)**beta_kww)
        g_dual = G0 * (f_dual * np.exp(-(t/tau1_dual)**beta1_dual) + (1-f_dual) * np.exp(-(t/tau2_dual)**beta2_dual))
        
        fig_models, ax_models = plt.subplots(figsize=(10, 6))
        ax_models.loglog(t, g_maxwell, 'o-', linewidth=2.5, markersize=4, alpha=0.8, label='Maxwell ($τ=10$ s)')
        ax_models.loglog(t, g_kww, 's-', linewidth=2.5, markersize=4, alpha=0.8, label=f'Single-KWW ($τ=15$ s, $β=0.85$)')
        ax_models.loglog(t, g_dual, '^-', linewidth=2.5, markersize=4, alpha=0.8, label=f'Dual-KWW ($τ_1=5$, $τ_2=100$ s)')
        ax_models.set_xlabel('Time (s)', fontsize=12, fontweight='bold')
        ax_models.set_ylabel('G(t) / G₀', fontsize=12, fontweight='bold')
        ax_models.set_title('Comparison of Relaxation Models', fontsize=13, fontweight='bold')
        ax_models.grid(True, alpha=0.3, which='both')
        ax_models.legend(fontsize=11, loc='upper right')
        plt.tight_layout()
        st.pyplot(fig_models)
        
        st.markdown("""
        **Observations from Example:**
        - **Maxwell** (red): Simplest, single exponential decay
        - **Single-KWW** (blue): Stretched exponential, slight curvature on log-log plot
        - **Dual-KWW** (green): Two distinct timescales visible, strong multi-slope behavior
        
        **How to Recognize:**
        - **Single-slope on log-log plot** → Maxwell or Single-KWW
        - **Clear change in slope** → Dual-KWW (indicates multiple processes)
        - **β value interpretation**: β < 0.8 suggests significant polydispersity
        """)
    
    # ====== TAB 5: REFERENCES ======
    with edu_tabs[4]:
        st.subheader("Scientific References & Literature")
        
        st.markdown("""
        ### 📚 Foundational Papers on Relaxation Models
        
        **KWW (Stretched Exponential):**
        1. Kohlrausch, R. (1847). "Theorie des elektrischen Rückstandes." *Poggendorff's Ann. Phys. Chem.* 91(2), 179-214.
           - Original stretched exponential discovery
        
        2. Williams, G., & Watts, D. C. (1970). "Non-symmetrical dielectric relaxation behaviour arising from a simple empirical decay function." *Trans. Faraday Soc.* 66, 80-85.
           - Modern formulation as "KWW function"
        
        3. Phillips, J. C. (1996). "Stretched exponential relaxation in molecular and electronic glasses." *Rep. Prog. Phys.* 59(9), 1133.
           - Theoretical justification and applications
        
        ### 🧪 Vitrimer Chemistry & Design
        
        **Seminal Vitrimer Papers:**
        4. Denissen, W., et al. (2016). "Vitrimers: Permanent organic networks with glass-like mechanical properties." *Nat. Commun.* 7, 11960.
           - Landmark paper introducing concept
        
        5. Montarnal, D., et al. (2011). "Silica-like malleable materials from permanent organic polymers." *Science* 334(6058), 965-968.
           - Original transesterification-based vitrimer
        
        6. Guerre, M., et al. (2020). "Vitrimers: Directing dynamic chemistry toward the main chain." *Polym. Chem.* 11(42), 6789-6799.
           - Recent comprehensive review
        
        ### 🌡️ Temperature-Dependent Kinetics
        
        7. Arrhenius, S. (1889). "Über die Dissociationswärme und den Einfluss der Temperatur auf den Ausschlag des galvanischen Elements." *Z. Phys. Chem.* 4, 96-116.
           - Classical Arrhenius equation
        
        8. Vogel, H. (1921). "The temperature dependence law for the viscosity of fluids." *Phys. Z.* 22, 645-646.
           - VFT model introduction
        
        9. Fulcher, G. S. (1925). "Analysis of recent measurements of the viscosity of glasses." *J. Am. Ceram. Soc.* 8(6), 339-355.
           - VFT formulation
        
        10. Böhmer, R., et al. (1992). "Nonexponential relaxations in strong and fragile glass formers." *J. Chem. Phys.* 99(5), 4201-4209.
            - Fragility concept and VFT analysis
        
        ### 📊 Rheology & Polymer Physics
        
        11. Ferry, J. D. (1980). *Viscoelastic Properties of Polymers* (3rd ed.). Wiley.
            - Classic textbook on polymer relaxation
        
        12. Menard, K. P. (2008). *Dynamic Mechanical Analysis: A Practical Introduction* (2nd ed.). CRC Press.
            - Experimental techniques and analysis
        
        13. Larson, R. G. (1999). *The Structure and Rheology of Complex Fluids*. Oxford University Press.
            - Comprehensive theory
        
        ### 🔍 Time-Temperature Superposition
        
        14. Williams, M. L., et al. (1955). "The temperature dependence of relaxation mechanisms in amorphous polymers and other glass-forming liquids." *J. Am. Chem. Soc.* 77(14), 3701-3707.
            - WLF equation and TTS principle
        
        ### 🧬 Advanced Topics: Vitrimer Dynamics
        
        15. Zheng, P., et al. (2021). "Vitrimer polyurethanes with improved reprocessability and recovery of mechanical properties." *ACS Macro Lett.* 10(5), 559-565.
        
        16. Micheletti, A., et al. (2020). "A general model for viscous flow in linear vitrimer polymer glasses." *Macromolecules* 53(17), 7254-7265.
        
        ---
        
        ### 🌐 Online Resources
        
        - **NIST Polymer Database**: https://www.nist.gov/mml/polymers
        - **Matminer Materials Database**: https://hackingmaterials.lbl.gov/matminer/
        - **OpenScience resources**: Preprints and data repositories
        
        ### 💡 Key Takeaways
        
        ✅ **Maxwell model** = baseline (single time scale)  
        ✅ **KWW model** = stretching exponent captures polydispersity  
        ✅ **Dual-KWW model** = multiple concurrent processes  
        ✅ **Arrhenius** = simple, works far above $T_g$  
        ✅ **VFT** = better near $T_g$ (dynamic/vitrimer systems)  
        ✅ **Vitrimers** = exchangeable bonds enable reprocessing  
        
        """)


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