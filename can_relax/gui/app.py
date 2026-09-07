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
import matplotlib.mathtext as mathtext

# Patch MathTextParser to safely handle invalid MathText without crashing
if not hasattr(mathtext.MathTextParser, '_patched_by_us'):
    _original_parse = mathtext.MathTextParser.parse
    def _safe_parse(self, s, *args, **kwargs):
        if not s or str(s).strip() == "" or str(s).strip() == "$$":
            return _original_parse(self, " ", *args, **kwargs)
        try:
            return _original_parse(self, s, *args, **kwargs)
        except Exception:
            return _original_parse(self, " ", *args, **kwargs)
    mathtext.MathTextParser.parse = _safe_parse
    mathtext.MathTextParser._patched_by_us = True

import matplotlib.backends.backend_agg as backend_agg
if not hasattr(backend_agg.RendererAgg, '_patched_by_us'):
    _orig_get_text_width_height_descent = backend_agg.RendererAgg.get_text_width_height_descent
    def _safe_get_text_width_height_descent(self, s, prop, ismath):
        if not s: return 0.0, 0.0, 0.0
        try:
            return _orig_get_text_width_height_descent(self, s, prop, ismath)
        except Exception:
            return 0.0, 0.0, 0.0
    backend_agg.RendererAgg.get_text_width_height_descent = _safe_get_text_width_height_descent
    
    _orig_draw_text = backend_agg.RendererAgg.draw_text
    def _safe_draw_text(self, gc, x, y, s, prop, angle, ismath=False, mtext=None):
        if not s: return
        try:
            _orig_draw_text(self, gc, x, y, s, prop, angle, ismath, mtext)
        except Exception:
            pass
    backend_agg.RendererAgg.draw_text = _safe_draw_text
    backend_agg.RendererAgg._patched_by_us = True

# Import proper modules from can_relax
from can_relax.io.parser import parse_curve_records as parser_module_func
from can_relax.core.observations import relaxation_crossing
from can_relax.core.state import analysis_identity, clear_analysis, clear_derived
from can_relax.gui.labels import curve_labels
from pathlib import Path
from can_relax.core.simulator import MaterialSimulator
from can_relax.core.kinetics import KineticsEngine, predict_van_t_hoff, predict_coupled
from can_relax.core.tts import TTSEngine
from can_relax.core.analyzer import CurveAnalyzer
from can_relax.core.spectrum import SpectrumAnalyzer

# Shared Plotly layout for visual consistency across all tabs
PLOTLY_STYLE = dict(
    font=dict(family="Inter, sans-serif", size=12),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    colorway=["#6366f1", "#f43f5e", "#10b981", "#f59e0b", "#3b82f6", "#8b5cf6"],
)

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
    with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx' if uploaded_file.name.lower().endswith('.xlsx') else '.csv') as tmp:
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

# Cached curve fitting helper to prevent heavy calculations on every rerun
@st.cache_data
def cached_fit_one_temp(temp, df, Tg_input, fit_model, plateau_mode='Zero', fixed_plateau=0.0):
    local_analyzer = CurveAnalyzer()
    return local_analyzer.fit_one_temp(temp, df, Tg=Tg_input, fit_model=fit_model,
                                       plateau_mode=plateau_mode, fixed_plateau=fixed_plateau)

# Cached continuous spectrum helper to prevent heavy calculations on every rerun
@st.cache_data
def cached_compute_continuous_spectrum(t, g, num_modes, alpha, optimize_alpha, subtract_G_eq):
    engine = SpectrumAnalyzer()
    tau_grid, H = engine.compute_continuous_spectrum(
        t, g, num_modes=num_modes, alpha=alpha, 
        optimize_alpha=optimize_alpha, subtract_G_eq=subtract_G_eq
    )
    return tau_grid, H, engine.last_alpha, engine.last_G_eq, engine.last_relative_rmse

# Helper
def get_tau_1_over_e(t, g):
    return relaxation_crossing(t, g)['tau']


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
        use_example_data = st.checkbox("Use toy_data.csv Example", value=False, key="use_example_data")

    # ── Physics & Fitting (merged) ────────────────────────────────
    with st.sidebar.expander("⚙️ Physics & Fitting", expanded=True):
        G_prime_input = st.number_input("Rubbery G' (MPa)", 0.01, 5000.0, 1.0, help="Used for Tv calculation")
        Tg_input = st.number_input("Tg (°C)", value=50.0, help="Curves below this temperature are skipped")
        time_origin = st.number_input("Loading time origin (s)", value=0.0, help="Subtract this instrument clock value to obtain elapsed time since loading. Cutoffs do not reset this origin.")
        time_cutoff = st.number_input("Short-Time Cutoff (s)", 0.0, 1000.0, 0.0, step=0.1, help="Discard data points where time < this threshold to remove loading transients/machinery artifacts")
        st.markdown("---")
        fit_model = st.selectbox("Model", ["Maxwell", "Single_KWW", "Dual_KWW"], key="analysis_fit_model")
        plateau_mode = st.selectbox('Long-time plateau', ['Zero', 'Fit', 'Fixed'],
                                    key='plateau_mode', disabled=fit_model == 'Dual_KWW')
        if fit_model == 'Dual_KWW':
            plateau_mode = 'Zero'
            st.caption('Plateau options apply to Maxwell and single KWW.')
        fixed_plateau = st.number_input('Fixed plateau (MPa)', min_value=0.0, value=0.0,
                                         key='fixed_plateau') if plateau_mode == 'Fixed' else 0.0
        if plateau_mode != 'Zero':
            st.caption('Plateau estimated over the measurement window; it does not establish permanent crosslinks. Fitted tau describes the relaxing component.')
        kinetics_mode = st.radio("Kinetics Base:", ["Fit Parameter", "Raw 1/e"])
        st.caption("Raw 1/e is the interval from the first retained observation. For a truncated KWW curve it is not the intrinsic fitted tau.")

    # ── Always-visible Run button ─────────────────────────────────
    st.sidebar.markdown("---")
    run_btn = st.sidebar.button("▶ Run Analysis", type="primary", width='stretch')

    source_bytes = uploaded_file.getvalue() if uploaded_file else (Path("examples/toy_data.csv").read_bytes() if use_example_data else b'')
    current_id = analysis_identity(source_bytes, {'model': fit_model, 'Tg': Tg_input,
        'cutoff': time_cutoff, 'origin': time_origin, 'plateau_mode': plateau_mode, 'fixed_plateau': fixed_plateau})
    if st.session_state.get('analysis_id') != current_id:
        clear_analysis(st.session_state)
    # PROCESS: clear old state before parsing so a failed upload cannot retain old results.
    if (uploaded_file or use_example_data) and run_btn:
        clear_analysis(st.session_state)
        try:
            curves = parse_uploaded_file(uploaded_file) if uploaded_file else parser_module_func("examples/toy_data.csv")
        except (ValueError, OSError) as exc:
            st.error(f"Input rejected: {exc}")
            st.stop()
        if not curves:
            st.error("No curves found. Check the documented CSV/XLSX layouts.")
            st.stop()
        res = []
        skipped = []
        bar = st.progress(0)

        idx = 0
        for record in curves:
            temp, df = record["Temp"], record["Data"].copy()
            for notice in record.get('Import_Warnings', []):
                st.warning(notice)
            df["Time"] = df["Time"] - time_origin
            # Apply short-time cutoff if set
            if time_cutoff > 0.0:
                df = df[df['Time'] >= time_cutoff].copy()
            
            # Pass Tg and selected fit_model for cached filtering and fast fit
            out = cached_fit_one_temp(temp, df, Tg_input, fit_model, plateau_mode, fixed_plateau)
            if out.get('Valid', False):
                out['Warnings'].extend(record.get('Import_Warnings', []))
                out['Best_Model'] = fit_model 
                out['Curve_ID'] = record['Curve_ID']
                crossing = relaxation_crossing(out['Raw']['t'], out['Raw']['g'])
                out['Crossing'] = crossing
                out['Tau_1e'] = crossing['tau']
                out['Crossing_Time'] = crossing['crossing_time']
                res.append(out)
            else:
                reason = out.get('Reason', 'Below Tg')
                skipped.append(f"{temp}°C ({reason})")
            idx += 1
            bar.progress(idx/len(curves))
            
        st.session_state.results = res
        st.session_state.analysis_id = current_id
        if res: st.success(f"Processed {len(res)} curves.")
        if skipped: st.warning(f"Skipped curves: {', '.join(skipped)}")

    # DISPLAY
    if 'results' in st.session_state and st.session_state.results:
        all_results = st.session_state.results
        metadata = {'analysis_id': current_id, 'model': fit_model, 'Tg_C': Tg_input,
            'plateau_mode': plateau_mode, 'fixed_plateau_MPa': fixed_plateau if plateau_mode == 'Fixed' else None,
            'cutoff_s': time_cutoff, 'loading_origin_s': time_origin,
            'units': {'time': 's', 'modulus': 'MPa', 'temperature': 'C'},
            'curves': [{'curve_id': r['Curve_ID'], 'temperature_C': r['Temp'],
                        'preprocessing': r['Preprocessing'], 'warnings': r['Warnings'],
                        'fit_flags': r['Fits'][fit_model]['flags'],
                        'parameters': r['Fits'][fit_model]['popt'].tolist(),
                        'G_inf_MPa': r['Fits'][fit_model]['G_inf']}
                       for r in all_results]}
        st.download_button('Download analysis provenance JSON', json.dumps(metadata, indent=2),
                           'analysis_provenance.json', mime='application/json')
        for r in all_results:
            for warning in r['Warnings']:
                st.caption(f"{r['Curve_ID']}: {warning}")
        
        # Live Filter
        labels = curve_labels(all_results)
        col_sel, _ = st.columns([1, 1])
        with col_sel:
            selected_curves = st.multiselect("Select Curves:", list(labels), default=list(labels),
                format_func=labels.get, key=f"selection_{current_id}")
        active_results = [r for r in all_results if r['Curve_ID'] in selected_curves]
        plot_labels = curve_labels(active_results)
        def format_label(r):
            return plot_labels[r['Curve_ID']]
        selection_id = analysis_identity(current_id.encode(), {'curves': selected_curves, 'kinetics': kinetics_mode})
        if st.session_state.get('selection_id') != selection_id:
            clear_derived(st.session_state)
            st.session_state.selection_id = selection_id
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
                    name=format_label(r),
                    marker=dict(size=6, opacity=0.8)
                ))
                if show_fits and fit_model in r['Fits']:
                    g_fit_raw = r['Fits'][fit_model].get('curve', r['Raw']['g'])
                    g_fit_plot = g_fit_raw if mod_plot_type == "Normalized" else g_fit_raw * G0
                    fig.add_trace(go.Scatter(
                        x=t_raw,
                        y=g_fit_plot,
                        mode='lines',
                        name=f"Fit ({format_label(r)})",
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
            with st.expander("\U0001f4ca Fitting Parameters", expanded=True):
                fit_details = []
                for r in active_results:
                    temp = r['Temp']
                    g0 = r['Raw'].get('G0', np.nan)
                    if fit_model in r['Fits']:
                        p = r['Fits'][fit_model]['popt']
                        r2 = r['Fits'][fit_model]['r2']
                        aic = r['Fits'][fit_model].get('aic', np.inf)
                        bic = r['Fits'][fit_model].get('bic', np.inf)
                        if fit_model == "Maxwell":
                            fit_details.append({"Curve ID": r["Curve_ID"], "Temperature (\u00b0C)": temp, "G0 (MPa)": g0, "Tau (s)": p[0], "R\u00b2": r2, "AICc": aic, "BIC": bic})
                        elif fit_model == "Single_KWW":
                            fit_details.append({"Curve ID": r["Curve_ID"], "Temperature (\u00b0C)": temp, "G0 (MPa)": g0, "Tau (s)": p[0], "Beta (\u03b2)": p[1], "R\u00b2": r2, "AICc": aic, "BIC": bic})
                        elif fit_model == "Dual_KWW":
                            fit_details.append({"Curve ID": r["Curve_ID"], "Temperature (\u00b0C)": temp, "G0 (MPa)": g0, "Fraction A": p[0], "Tau 1 (s)": p[1], "Beta 1 (\u03b21)": p[2], "Tau 2 (s)": p[3], "Beta 2 (\u03b22)": p[4], "R\u00b2": r2, "AICc": aic, "BIC": bic})
                if fit_details:
                    for row, r in zip(fit_details, active_results):
                        fit = r['Fits'][fit_model]
                        row.update({'Plateau mode': fit['plateau_mode'], 'G_inf (MPa)': fit['G_inf'],
                                    'G_inf local SE (MPa)': fit['G_inf_std'],
                                    'Fit flags': '; '.join(fit['flags']) or 'None',
                                    'First fitted time (s)': float(r['Raw']['t'][0]),
                                    'Last fitted time (s)': float(r['Raw']['t'][-1])})
                    df_details = pd.DataFrame(fit_details)
                    col_config = {
                        "Temperature (\u00b0C)": st.column_config.NumberColumn(format="%.1f"),
                        "G0 (MPa)": st.column_config.NumberColumn(format="%.3f"),
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
            with st.expander('Residuals and fit checks', expanded=False):
                residual_plot = go.Figure()
                for r in active_results:
                    fit = r['Fits'][fit_model]
                    residual_plot.add_trace(go.Scatter(x=r['Raw']['t'], y=fit['residuals'],
                                                       mode='lines', name=format_label(r)))
                    for flag in fit['flags']:
                        st.warning(f'{format_label(r)}: {flag}')
                residual_plot.add_hline(y=0, line_dash='dash')
                residual_plot.update_layout(xaxis_title='Time (s)', yaxis_title='Observed − fitted (normalized)', xaxis_type=t_type)
                st.plotly_chart(residual_plot, width='stretch')
                st.caption('Flags and local standard errors are screening aids, not proof of parameter identifiability. Normalization can correlate measurement errors.')

        # 2. KINETICS
        with t2:
            kinetic_component = st.radio('Fitted component', ['Slow (tau2)', 'Fast (tau1)'], horizontal=True) if fit_model == 'Dual_KWW' else None
            st.caption("G0 denotes the first retained reference modulus, not an inferred zero-time plateau. Raw 1/e requires one observed crossing.")
            k_data = []
            st.session_state.kinetics_df = pd.DataFrame()
            for r in active_results:
                t_val = np.nan
                if kinetics_mode == "Raw 1/e": t_val = r.get('Tau_1e', np.nan)
                elif fit_model in r['Fits']:
                    p = r['Fits'][fit_model]['popt']
                    if fit_model == "Maxwell": idx = 0
                    elif fit_model == "Single_KWW": idx = 0
                    elif fit_model == "Dual_KWW": idx = 3 if kinetic_component == 'Slow (tau2)' else 1
                    else: idx = 0
                    t_val = p[idx]
                if kinetics_mode == 'Raw 1/e' and r['Crossing']['status'] != 'observed':
                    st.warning(f"{r['Temp']:g} C / {r['Curve_ID']}: 1/e {r['Crossing']['status']}; excluded from raw kinetics.")
                if np.isfinite(t_val) and t_val > 0:
                    fit = r['Fits'][fit_model]
                    flags = fit['flags'] if kinetics_mode == 'Fit Parameter' else []
                    beta = (fit['popt'][1] if fit_model == 'Single_KWW' else
                            fit['popt'][4 if kinetic_component == 'Slow (tau2)' else 2] if fit_model == 'Dual_KWW' else 1.0)
                    k_data.append({"Curve_ID": r["Curve_ID"], "Include": True, "Temp": r['Temp'], "1000/T": 1000.0/(r['Temp']+273.15), "Tau": t_val, "ln(Tau)": np.log(t_val), "Type": "Main",
                                   'Beta': beta, 'Fit flags': '; '.join(flags) or 'None'})

            if k_data:
                df_k = pd.DataFrame(k_data)
                col_edit, col_chart = st.columns([1, 2])
                with col_edit:
                    st.markdown("##### Outlier Rejection")
                    st.caption("Review flagged curves and uncheck rows to exclude them. Out-of-window tau values are not automatically rejected.")
                    edited_df = st.data_editor(df_k, column_config={"Include": st.column_config.CheckboxColumn("Fit?", default=True)}, hide_index=True, height=280, width='stretch', disabled=[c for c in df_k.columns if c != "Include"], key=f"kinetics_editor_{selection_id}_{kinetic_component}")
                    st.session_state.kinetics_df = edited_df
                    
                    st.markdown("---")
                    kinetics_model_type = st.selectbox(
                        "Kinetics Model", 
                        ["Arrhenius", "VFT", "Eyring (Transition State)", "Van 't Hoff (Decrosslinking)", "Coupled WLF-Arrhenius"],
                        key="kinetics_model_type"
                    )

                with col_chart:
                    active = edited_df[edited_df["Include"] == True]
                    if any(active['Fit flags'] != 'None'):
                        st.warning('Included curves have fit-quality flags. Review them before interpreting activation energy.')
                    st.download_button('Download kinetics selection CSV', edited_df.to_csv(index=False), 'kinetics_selection.csv')
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
                            g0_map = {r['Curve_ID']: r['Raw']['G0'] for r in active_results}
                            active_G0s = [g0_map[cid] for cid in active["Curve_ID"]]
                            fit_res = k_engine.fit_van_t_hoff(active["Temp"].tolist(), active_G0s)
                        elif kinetics_model_type == "Coupled WLF-Arrhenius":
                            fit_res = k_engine.fit_coupled_kinetics(active["Temp"].tolist(), active["Tau"].tolist(), Tg=Tg_input)
                            
                        if fit_res:
                            if fit_res.get("Warning"):
                                st.warning(fit_res["Warning"])
                            r_sq = fit_res.get("R2", 0.0)
                            
                            if fit_res["Type"] == "Arrhenius":
                                Ea = fit_res["Ea"]
                                Ea_std = fit_res["Ea_std"]
                                slope = fit_res["Params"]["slope"]
                                intercept = fit_res["Params"]["intercept"]
                                
                                mc1, mc2, mc3 = st.columns(3)
                                mc1.metric("Apparent Ea", f"{Ea:.1f} kJ/mol")
                                mc2.metric("Regression SE", f"{Ea_std:.1f} kJ/mol" if np.isfinite(Ea_std) else 'Unavailable')
                                mc3.metric("R\u00b2", f"{r_sq:.4f}")
                                st.caption(f"{len(active)} curves; {active['Temp'].min():g}–{active['Temp'].max():g} °C. Uncertainty is the regression standard error; it does not propagate uncertainty in each fitted tau.")
                                st.download_button('Download Arrhenius result CSV', pd.DataFrame([{
                                    'Apparent Ea (kJ/mol)': Ea, 'Regression SE (kJ/mol)': Ea_std,
                                    'R2': r_sq, 'Minimum temperature (C)': active['Temp'].min(),
                                    'Maximum temperature (C)': active['Temp'].max(), 'Curves': len(active),
                                    'Model': fit_model, 'Tau source': kinetics_mode, 'Component': kinetic_component,
                                    'Plateau mode': plateau_mode}]).to_csv(index=False), 'arrhenius_result.csv')
                                
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
                                amplitude_A = fit_res["A"]
                                
                                mc1, mc2, mc3 = st.columns(3)
                                mc1.metric("\u0394H_diss", f"{dH_diss:.1f} kJ/mol")
                                mc2.metric("\u0394S_diss", f"{dS_diss:.1f} J/mol\u00b7K")
                                mc3.metric("R\u00b2", f"{r_sq:.4f}")
                                st.caption(f"Amplitude A: {amplitude_A:.6g} MPa/K; fitted to observed reference moduli.")
                                
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
                                pred_grid = predict_van_t_hoff(T_K_grid, **fit_res["Params"])
                                fig_k.add_trace(go.Scatter(x=1000.0/T_K_grid, y=pred_grid, mode='lines', name="Van 't Hoff Fit", line=dict(dash='dash', color='red')))
                                fig_k.update_layout(xaxis_title="1000/T (K\u207b\u00b9)", yaxis_title="G\u2080 (MPa)")
                                
                            elif fit_res["Type"] == "Coupled":
                                fig_k.add_trace(go.Scatter(x=fit_res["Plot"]["x"], y=fit_res["Plot"]["y"], mode='markers', name="Data"))
                                T_K_grid = np.linspace(273.15 + min(active["Temp"]), 273.15 + max(active["Temp"]), 50)
                                T0_val = fit_res["Params"]["T0"]
                                R_GAS_VAL = 8.314462
                                pred_grid = predict_coupled(T_K_grid, **fit_res["Params"])
                                fig_k.add_trace(go.Scatter(x=1.0/T_K_grid, y=pred_grid, mode='lines', name="Coupled Fit", line=dict(dash='dash', color='red')))
                                fig_k.update_layout(xaxis_title="1/T (K\u207b\u00b9)", yaxis_title="ln(\u03c4)")
                                
                            fig_k.update_layout(height=420, margin=dict(l=10, r=10, t=20, b=20))
                            st.plotly_chart(fig_k, width='stretch')
                            if fit_res['Type'] == 'Arrhenius' and kinetics_mode == 'Fit Parameter' and fit_model != 'Maxwell':
                                beta_plot = go.Figure(go.Scatter(x=active['Temp'], y=active['Beta'], mode='markers', name='Beta'))
                                beta_plot.update_layout(height=240, xaxis_title='Temperature (°C)', yaxis_title='KWW beta')
                                st.plotly_chart(beta_plot, width='stretch')
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
                    temps_available = sorted(set(r['Temp'] for r in active_results))
                    mid_idx = len(temps_available) // 2
                    ref_temp_sel = st.selectbox("Reference T (°C)", temps_available, index=mid_idx)
                    references = [r for r in active_results if r['Temp'] == ref_temp_sel]
                    reference_id = None
                    if len(references) > 1:
                        reference_id = st.selectbox('Reference replicate',
                            [None] + [r['Curve_ID'] for r in references],
                            format_func=lambda cid: 'Mean of all selected replicates' if cid is None else plot_labels[cid],
                            key=f'tts_reference_{selection_id}_{ref_temp_sel}')
                    st.caption('Reference tau uses the arithmetic mean of selected replicates at this temperature, unless a specific curve is chosen.')
                    master_config = (selection_id, ref_temp_sel, reference_id)
                    if st.session_state.get('master_config') != master_config:
                        st.session_state.pop('master_data', None)
                    # Generate mastercurve
                    if st.button("Generate Mastercurve"):
                        try:
                            master_data = tts_engine.generate_mastercurve(active_results, ref_temp=ref_temp_sel, ref_curve_id=reference_id)
                            st.session_state.master_data = master_data
                            st.session_state.master_config = master_config
                            st.success(f"✅ Mastercurve at Tref = {master_data['T_ref']}°C")
                        except Exception as e:
                            st.error(f"Error: {e}")
                
                with col_tts_plot:
                    if 'master_data' in st.session_state:
                        master = st.session_state.master_data
                        st.caption(f"Reference tau: {master['Tau_ref']:.6g} s; method: {master['Reference_mode']}; curves: {', '.join(master['Reference_curve_ids'])}")
                        
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
                        fig_mc.update_yaxes(title="G(t) / G(reference)")
                        fig_mc.update_layout(height=500, title="Time-Temperature Superposition Mastercurve")
                        st.plotly_chart(fig_mc, width='stretch')
                        
                        # Display shift factors
                        st.markdown("##### Shift Factors (aT)")
                        shifts_df = pd.DataFrame([
                            {"Curve ID": T, "log(aT)": np.log10(aT), "aT": f"{aT:.2e}"}
                            for T, aT in master['Shifts'].items()
                        ])
                        st.dataframe(shifts_df, hide_index=True, width='stretch')
                    else:
                        st.info("👈 Click 'Generate Mastercurve' to create TTS plot")
            else:
                st.warning("⚠️ Need at least 2 temperatures for TTS mastercurve")

        # 4. SPECTRUM
        with t4:
            spectrum_status = st.empty()
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
                
            spec_outputs = []
            for r in active_results:
                t, g = r['Raw']['t'], r['Raw']['g']
                tau_grid, H, last_alpha, last_G_eq, reconstruction_error = cached_compute_continuous_spectrum(
                    t, g, num_modes=n_modes, alpha=alpha_reg,
                    optimize_alpha=opt_alpha, subtract_G_eq=sub_G_eq)
                spec_outputs.append({'Temp': r['Temp'], 'Curve_ID': r['Curve_ID'],
                    'tau_grid': tau_grid, 'H': H, 'last_alpha': last_alpha,
                    'last_G_eq': last_G_eq, 'G0': r['Raw']['G0'],
                    'reconstruction_error': reconstruction_error, 't_max': float(t[-1])})
            with c_spec:
                fig_h = go.Figure()
                incomplete_warnings = []
                spectrum_engine_local = SpectrumAnalyzer()

                for item in spec_outputs:
                    tau_grid = item['tau_grid']
                    H = item['H']
                    G0 = item['G0']
                    
                    # Scale output metrics and curves to absolute scale only during display step
                    if mod_plot_type == "Absolute":
                        H_plot = H * G0
                        last_G_eq_plot = item['last_G_eq'] * G0
                    else:
                        H_plot = H
                        last_G_eq_plot = item['last_G_eq']
                    
                    # Display L-curve corner alpha and G_eq details
                    with c_ctrl:
                        st.caption(f"{item['Temp']}°C: α={item['last_alpha']:.2e} (G_eq: {last_G_eq_plot:.2e})")
                    
                    st.caption(f"{item['Curve_ID']}: reconstruction RMSE / reference modulus = {item['reconstruction_error']:.2%}")
                    # --- Incomplete relaxation detection ---
                    tau_dom = spectrum_engine_local.get_weighted_avg_tau(tau_grid, H)
                    # Find t_max for this temperature from active results
                    t_max_this = item['t_max']
                    if t_max_this is not None and tau_dom > t_max_this * 0.8:
                        incomplete_warnings.append(
                            f"**{format_label(item)}**: weighted geometric mean τ ≈ {tau_dom:.1f} s > 0.8 × t_max ({t_max_this:.1f} s)"
                        )

                    fig_h.add_trace(go.Scatter(x=tau_grid, y=H_plot, mode='lines', name=format_label(item), fill='tozeroy'))

                fig_h.update_xaxes(type="log", title="Relaxation Time τ (s)")
                fig_h.update_yaxes(title="Discrete modal weight (MPa)" if mod_plot_type == "Absolute" else "Discrete modal weight / G(reference)")
                st.caption("Weights sum discrete exponential modes; they are not a continuous density. Tail subtraction assumes the measured tail estimates equilibrium.")
                st.plotly_chart(fig_h, width="stretch")

                if incomplete_warnings:
                    with spectrum_status.container():
                        st.badge(f"Possible incomplete relaxation · {len(incomplete_warnings)} of {len(spec_outputs)} curves", icon="⚠️", color="orange")
                    st.warning(
                        "⚠️ **Possible Incomplete Relaxation** — The weighted geometric mean relaxation time approaches or exceeds the experiment window "
                        "for the following curves. The spectrum may be **right-truncated**: the true peak could lie beyond t_max. "
                        "Consider extending the experiment duration; the inferred spectrum is sensitive to the observation window.\n\n"
                        + "\n\n".join(f"- {w}" for w in incomplete_warnings)
                    )




# ------------------------------------------------------------------
# TAB 3: VIRTUAL LAB  →  extracted to can_relax/gui/tabs/tab_virtual_lab.py
# ------------------------------------------------------------------
from can_relax.gui.tabs import tab_virtual_lab
with tab_sim:
    tab_virtual_lab.render(sim, PLOTLY_STYLE)


# ==========================
# TAB 4: COMPARISON  →  extracted to can_relax/gui/tabs/tab_comparison.py
from can_relax.gui.tabs import tab_comparison as tab_comparison_mod
tab_comparison_mod.render(tab_comparison, PLOTLY_STYLE)

# ==========================
# TAB 5: PUBLICATION  →  extracted to can_relax/gui/tabs/tab_publication.py
# ==========================
from can_relax.gui.tabs import tab_pub_main as tab_publication
tab_publication.render_publication(tab_pub, PLOTLY_STYLE, Tg_input, G_prime_input)


# --- MODULAR TABS ---
from can_relax.gui.components import render_education_tab, render_credits_tab, render_plotting_tab

render_plotting_tab(tab_plotting)
render_education_tab(tab_education)
render_credits_tab(tab_credits)
