import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import io
import matplotlib.ticker as ticker
from can_relax.core.kinetics import KineticsEngine

def _render_sample_inputs():
    st.subheader("Sample Input")
    st.info("💡 Add up to 6 samples with their own temperature-τ data. We’ll calculate Ea, Tv, and R² for each.")
    
    num_samples = min(6, len(st.session_state.comparison_samples) + 1)
    sample_tabs = st.tabs(["📌 Sample 1", "📌 Sample 2", "📌 Sample 3", "📌 Sample 4", "📌 Sample 5", "📌 Sample 6"])
    
    for sample_idx, sample_tab in enumerate(sample_tabs, start=1):
        sample_key = f"sample_{sample_idx}"
        with sample_tab:
            col_info, col_delete = st.columns([4, 1])
            with col_info:
                col_name, col_tg, col_gp = st.columns(3)
                with col_name:
                    sample_name = st.text_input(f"Sample Name", value=st.session_state.comparison_samples.get(sample_key, {}).get('name', f'Sample {sample_idx}'), key=f"name_{sample_idx}")
                with col_tg:
                    tg_val = st.number_input(f"Tg (°C)", value=st.session_state.comparison_samples.get(sample_key, {}).get('tg', 50.0), key=f"tg_{sample_idx}")
                with col_gp:
                    gp_val = st.number_input(f"G' (MPa)", value=st.session_state.comparison_samples.get(sample_key, {}).get('g_prime', 1.0), key=f"gp_{sample_idx}")
                
                st.markdown("**Upload Data** or enter manually:")
                uploaded_csv = st.file_uploader("Upload fit_parameters.csv", type=['csv'], key=f"file_{sample_idx}", label_visibility="collapsed")
                
                parsed_data = []
                text_data = ""
                
                if uploaded_csv is not None:
                    try:
                        df_upload = pd.read_csv(uploaded_csv)
                        for _, row in df_upload.iterrows():
                            temp = row.get("Temperature (°C)", row.get("Temperature (C)", np.nan))
                            tau = row.get("Tau (s)", np.nan)
                            g0 = row.get("G0 (MPa)", np.nan)
                            if pd.notna(temp) and pd.notna(tau):
                                parsed_data.append({"Temperature (°C)": float(temp), "t (s)": float(tau), "G0 (MPa)": float(g0) if pd.notna(g0) else None})
                        text_data = '\n'.join([f"{r['Temperature (°C)']}, {r['t (s)']}" + (f", {r['G0 (MPa)']}" if r.get('G0 (MPa)') is not None else "") for r in parsed_data])
                    except Exception as e:
                        st.error(f"Error parsing CSV: {e}")
                else:
                    existing_data = st.session_state.comparison_samples.get(sample_key, {}).get('data', [])
                    text_data = '\n'.join([f"{row.get('Temperature (°C)', 0)}, {row.get('t (s)', 0)}" + (f", {row['G0 (MPa)']}" if row.get('G0 (MPa)') is not None else "") for row in existing_data]) if existing_data else ""
                
                with st.expander("📝 Manual Data Entry", expanded=(uploaded_csv is None)):
                    data_input = st.text_area("Data pairs", value=text_data, height=100, key=f"data_{sample_idx}", label_visibility="collapsed")
                    if uploaded_csv is None:
                        try:
                            parsed_data = []
                            for line in data_input.strip().split('\n'):
                                if line.strip():
                                    parts = line.split(',')
                                    if len(parts) >= 2:
                                        temp, tau = float(parts[0].strip()), float(parts[1].strip())
                                        g0 = float(parts[2].strip()) if len(parts) >= 3 and parts[2].strip() else None
                                        parsed_data.append({"Temperature (°C)": temp, "t (s)": tau, "G0 (MPa)": g0})
                        except Exception:
                            st.error(f"⚠️ Parse error in Sample {sample_idx}. Use format: temp, tau, g0")
                
                st.session_state.comparison_samples[sample_key] = {'name': sample_name, 'tg': tg_val, 'g_prime': gp_val, 'data': parsed_data}
            
            with col_delete:
                if st.button("🗑️", key=f"delete_{sample_idx}", help="Clear sample"):
                    if sample_key in st.session_state.comparison_samples: del st.session_state.comparison_samples[sample_key]
                    for k in [f"name_{sample_idx}", f"tg_{sample_idx}", f"gp_{sample_idx}", f"data_{sample_idx}"]:
                        if k in st.session_state: del st.session_state[k]
                    if 'comparison_results' in st.session_state: del st.session_state['comparison_results']
                    st.rerun()

def _calculate_kinetics(valid_samples):
    results_list = []
    for sample in valid_samples:
        name, tg, g_prime, data = sample['name'], sample['tg'], sample['g_prime'], sample['data']
        temps, taus, g0_list = [], [], []
        
        for row in data:
            t_temp = row.get('Temperature (°C)', 0)
            tau_val = row.get('t (s)', row.get('τ (s)', 0))
            g0_val = row.get('G0 (MPa)', None)
            if t_temp > tg and tau_val > 0:
                temps.append(t_temp)
                taus.append(tau_val)
                g0_list.append(g0_val if pd.notna(g0_val) and g0_val is not None else np.nan)
        
        vh_fit = None
        if len(temps) >= 3:
            g0s_clean = [g for g in g0_list if not np.isnan(g)]
            temps_clean = [temps[i] for i in range(len(temps)) if not np.isnan(g0_list[i])]
            if len(temps_clean) >= 3:
                vh_fit = KineticsEngine().fit_van_t_hoff(temps_clean, g0s_clean)
        
        if len(temps) >= 2:
            inv_T = 1000.0 / (np.array(temps) + 273.15)
            ln_tau = np.log(np.array(taus))
            fit_res = KineticsEngine().fit_arrhenius(temps, taus)
            
            if fit_res:
                slope, intercept, r_sq, Ea = fit_res['Params']['slope'], fit_res['Params']['intercept'], fit_res['R2'], fit_res['Ea']
                warning_msg = f"⚠️ {name}: Negative Ea ({Ea:.1f})" if Ea < 0 else f"⚠️ {name}: Low Ea ({Ea:.1f})" if Ea < 10 else ""
                
                tau_target = 1e12 / (g_prime * 1e6)
                ln_tau_t = np.log(tau_target)
                Tv_val = (1.0 / ((ln_tau_t - intercept)/slope)) - 273.15 if slope != 0 else 0
                
                results_list.append({
                    'Sample Name': name, 'sample_key': sample['key'], 'Tg (°C)': tg, "G' (MPa)": g_prime,
                    'Ea (kJ/mol)': Ea, 'Ea_std (kJ/mol)': fit_res.get('Ea_std', 0), 'Tv (°C)': Tv_val, 'R²': r_sq,
                    'N_points': len(temps), 'inv_T': inv_T, 'warning': warning_msg, 'ln_tau': ln_tau, 'slope': slope,
                    'intercept': intercept, 'tau_target': tau_target, 'ln_tau_target': ln_tau_t,
                    'vh_fit': vh_fit, 'vh_temps': temps_clean if vh_fit else [], 'vh_g0s': g0s_clean if vh_fit else []
                })
    return results_list

def _render_arrhenius_plot(results, PLOTLY_STYLE):
    st.subheader("📈 Arrhenius Comparison Plot")
    col_plot, col_settings = st.columns([3, 1])
    with col_settings:
        comp_fmt = st.selectbox("Format", ["png", "jpeg", "pdf", "svg"], key="comp_fmt")
        comp_dpi = st.number_input("DPI", 72, 1200, 300, 50, key="comp_dpi")
        comp_colorspace = st.selectbox("Color Space", ["RGB", "CMYK (for Print)"], key="comp_colorspace")
        
        with st.expander("📝 Legend Settings"):
            show_comp_legend = st.checkbox("Show Legend", value=True, key="comp_legend")
            comp_leg_pos = st.selectbox("Position", ["best", "upper right", "upper left", "lower left"], key="comp_leg_pos")
            comp_leg_fontsize = st.slider("Font Size", 4, 20, 8, key="comp_leg_fontsize")
            comp_leg_box = st.checkbox("Box Border", value=True, key="comp_leg_box")
            comp_show_ea = st.checkbox("Show Ea ± std", value=False, key="comp_show_ea")
            comp_show_tv = st.checkbox("Show Tv", value=False, key="comp_show_tv")

        with st.expander("📐 Dimensions & Fonts"):
            comp_width = st.number_input("Width (cm)", 1.0, 40.0, 12.7, 0.1, key="comp_w")
            comp_height = st.number_input("Height (cm)", 1.0, 40.0, 10.0, 0.1, key="comp_h")
            comp_font_family = st.selectbox("Font Family", ["Arial", "Times New Roman", "DejaVu Sans"], key="comp_font_family")
            comp_lbl_sz = st.number_input("Label Size", 4, 30, 12, key="comp_lbl_sz")
            comp_tick_size = st.number_input("Tick Size", 4, 30, 10, key="comp_tick_sz")

        with st.expander("🎨 Style & Limits"):
            comp_lw = st.slider("Line Width", 0.5, 6.0, 1.5, 0.5, key="comp_lw")
            comp_ms = st.slider("Marker Size", 1, 15, 6, 1, key="comp_ms")
            comp_custom_lims = st.checkbox("Manual Axis", value=False, key="comp_custom_lims")

        pl_c1, pl_c2 = st.columns(2)
        with pl_c1: comp_panel_l = st.text_input("Panel Letter", "", key="comp_pl")
        with pl_c2:
            comp_pl_x = st.number_input("X pos", -1.0, 2.0, -0.12, 0.01, key="comp_pl_x")
            comp_pl_y = st.number_input("Y pos", -1.0, 2.0, 1.02, 0.01, key="comp_pl_y")

    with col_plot:
        comp_plot_mode = st.radio("Plot Type", ["Interactive (Plotly)", "Static (Matplotlib)"], horizontal=True)
        colors = PLOTLY_STYLE.get('colorway', ['#EF553B', '#636EFA', '#00CC96', '#AB63FA', '#FFA15A', '#25D098'])
        
        if comp_plot_mode.startswith("Interactive"):
            fig_comp = go.Figure()
            for idx, r in enumerate(results):
                color = colors[idx % 6]
                name = r['Sample Name']
                legend_parts = []
                if comp_show_ea: legend_parts.append(f"Ea={r['Ea (kJ/mol)']:.1f}±{r.get('Ea_std (kJ/mol)', 0):.1f}")
                if comp_show_tv: legend_parts.append(f"Tv={r.get('Tv (°C)', 0):.1f}")
                if legend_parts: name += f" ({', '.join(legend_parts)})"
                
                fig_comp.add_trace(go.Scatter(x=r['inv_T'], y=r['ln_tau'], mode='markers', name=name, marker=dict(size=8, color=color)))
                x_range = np.linspace(r['inv_T'].min() * 0.9, r['inv_T'].max() * 1.1, 50)
                fig_comp.add_trace(go.Scatter(x=x_range, y=(r['slope']/1000.0)*x_range + r['intercept'], mode='lines', line=dict(color=color, dash='dash'), showlegend=False))
            fig_comp.update_layout(title="Arrhenius Comparison", xaxis_title="1000/T", yaxis_title="ln(τ)", height=500, template="plotly_white")
            st.plotly_chart(fig_comp, use_container_width=True)
        else:
            fig_mpl, ax_mpl = plt.subplots(figsize=(comp_width/2.54, comp_height/2.54))
            for idx, r in enumerate(results):
                color = colors[idx % 6]
                name = r['Sample Name']
                legend_parts = []
                if comp_show_ea: legend_parts.append(f"Ea={r['Ea (kJ/mol)']:.1f}±{r.get('Ea_std (kJ/mol)', 0):.1f}")
                if comp_show_tv: legend_parts.append(f"Tv={r.get('Tv (°C)', 0):.1f}")
                if legend_parts: name += f" ({', '.join(legend_parts)})"
                
                ax_mpl.scatter(r['inv_T'], r['ln_tau'], s=comp_ms**2, color=color, label=name, zorder=3)
                x_range = np.linspace(r['inv_T'].min() * 0.9, r['inv_T'].max() * 1.1, 50)
                ax_mpl.plot(x_range, (r['slope']/1000.0)*x_range + r['intercept'], '--', color=color, linewidth=comp_lw, zorder=2)
            
            ax_mpl.set_xlabel("1000/T (K⁻¹)", fontdict={'family': comp_font_family, 'size': comp_lbl_sz})
            ax_mpl.set_ylabel("ln(τ)", fontdict={'family': comp_font_family, 'size': comp_lbl_sz})
            ax_mpl.tick_params(axis='both', labelsize=comp_tick_size)
            if show_comp_legend: ax_mpl.legend(loc=comp_leg_pos, fontsize=comp_leg_fontsize, frameon=comp_leg_box)
            
            if comp_panel_l:
                ax_mpl.text(comp_pl_x, comp_pl_y, f"({comp_panel_l})", transform=ax_mpl.transAxes, 
                            fontfamily=comp_font_family, fontsize=comp_lbl_sz, fontweight='normal', va='bottom', ha='right')
                            
            plt.tight_layout()
            st.pyplot(fig_mpl, dpi=300)
            
            buf = io.BytesIO()
            fig_mpl.savefig(buf, format=comp_fmt, dpi=comp_dpi, bbox_inches='tight')
            buf.seek(0)
            with col_settings:
                st.download_button(f"📥 Download ({comp_fmt})", buf, f"Arrhenius.{comp_fmt}", mime=f"image/{comp_fmt}")

def _render_vant_hoff_plot(results, PLOTLY_STYLE):
    st.subheader("📈 Van 't Hoff Comparison Plot")
    col_plot, col_settings = st.columns([3, 1])
    valid_vh = [r for r in results if r.get('vh_fit') is not None]
    
    with col_settings:
        vh_comp_fmt = st.selectbox("Format", ["png", "jpeg", "pdf"], key="vh_comp_fmt")
        vh_comp_dpi = st.number_input("DPI", 72, 1200, 300, 50, key="vh_comp_dpi")
        vh_y_scale = st.radio("Y Scale", ["Log", "Linear"], horizontal=True, key="vh_y_scale")
        
        vh_pl_c1, vh_pl_c2 = st.columns(2)
        with vh_pl_c1: vh_comp_panel_l = st.text_input("Panel Letter", "", key="vh_comp_pl")
        with vh_pl_c2:
            vh_comp_pl_x = st.number_input("X pos ", -1.0, 2.0, -0.12, 0.01, key="vh_comp_pl_x")
            vh_comp_pl_y = st.number_input("Y pos ", -1.0, 2.0, 1.02, 0.01, key="vh_comp_pl_y")
        
    with col_plot:
        if not valid_vh:
            st.info("No valid samples with G0 data for Van 't Hoff plot.")
            return
            
        fig_vh, ax_vh = plt.subplots(figsize=(12.7/2.54, 10.0/2.54))
        colors = PLOTLY_STYLE.get('colorway', ['#EF553B', '#636EFA', '#00CC96', '#AB63FA', '#FFA15A', '#25D098'])
        
        for idx, r in enumerate(valid_vh):
            color = colors[idx % 6]
            T_K = np.array(r['vh_temps']) + 273.15
            inv_T = 1000.0 / T_K
            ax_vh.scatter(inv_T, r['vh_g0s'], color=color, label=f"{r['Sample Name']} (ΔH={r['vh_fit']['dH_diss']:.1f})")
            
            x_range = np.linspace(inv_T.min()*0.9, inv_T.max()*1.1, 100)
            T_range = 1000.0 / x_range
            exponent = -(r['vh_fit']['dH_diss']*1000.0)/(8.314462*T_range) + r['vh_fit']['dS_diss']/8.314462
            y_fit = r['vh_fit'].get('A', r['vh_fit']['G0_max']) * T_range / (1.0 + np.exp(np.clip(exponent, -50.0, 50.0))) if 'A' in r['vh_fit'] else r['vh_fit']['G0_max'] / (1.0 + np.exp(np.clip(exponent, -50.0, 50.0)))
            ax_vh.plot(x_range, y_fit, '--', color=color)
            
        ax_vh.set_yscale('log' if vh_y_scale == "Log" else 'linear')
        ax_vh.set_xlabel("1000/T (K⁻¹)")
        ax_vh.set_ylabel("G0 (MPa)")
        ax_vh.legend()
        
        if vh_comp_panel_l:
            ax_vh.text(vh_comp_pl_x, vh_comp_pl_y, f"({vh_comp_panel_l})", transform=ax_vh.transAxes, 
                       fontweight='normal', va='bottom', ha='right')
                       
        plt.tight_layout()
        st.pyplot(fig_vh)

def render(tab_comparison, PLOTLY_STYLE: dict):
    if 'comparison_samples' not in st.session_state:
        st.session_state.comparison_samples = {}
    
    with tab_comparison:
        st.header("📊 Multi-Sample Kinetic Comparison")
        _render_sample_inputs()
        
        st.markdown("---")
        if st.button("🔍 Analyze All Samples", type="primary", width='stretch'):
            valid_samples = [dict(v, key=k) for k, v in st.session_state.comparison_samples.items() if v.get('data') and len(v['data']) >= 2]
            if valid_samples:
                results_list = _calculate_kinetics(valid_samples)
                if results_list:
                    st.session_state.comparison_results = results_list
                    st.success(f"✅ Analyzed {len(results_list)} samples")
                else: st.error("❌ No valid samples (need ≥2 points above Tg for each)")
            else: st.error("❌ Add samples with at least 2 data points each")
        
        if 'comparison_results' in st.session_state and st.session_state.comparison_results:
            results = st.session_state.comparison_results
            for r in results:
                if r.get('warning'): st.warning(r['warning'].replace(r['Sample Name'], st.session_state.comparison_samples.get(r.get('sample_key'), {}).get('name', r['Sample Name'])))
            
            st.subheader("📊 Results Summary")
            results_df = pd.DataFrame([{'Sample': r['Sample Name'], 'Tg': r['Tg (°C)'], 'Ea': r['Ea (kJ/mol)'], 'Tv': r['Tv (°C)'], 'R²': r['R²']} for r in results])
            st.dataframe(results_df, hide_index=True, use_container_width=True)
            
            comp_tab_arr, comp_tab_vh = st.tabs(["Arrhenius Kinetics", "Van 't Hoff"])
            with comp_tab_arr: _render_arrhenius_plot(results, PLOTLY_STYLE)
            with comp_tab_vh: _render_vant_hoff_plot(results, PLOTLY_STYLE)
        else:
            st.info("💡 Fill in samples and click 'Analyze All Samples' to start comparison")
