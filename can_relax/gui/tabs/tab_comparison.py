import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import io
from can_relax.core.kinetics import KineticsEngine

def render(tab_comparison, PLOTLY_STYLE: dict):
    if 'comparison_samples' not in st.session_state:
        st.session_state.comparison_samples = {}
    
    with tab_comparison:
        st.header("📊 Multi-Sample Kinetic Comparison")
        st.markdown("Compare Arrhenius kinetics across up to 6 different samples")
        st.subheader("Sample Input")
        col_help = st.info("💡 Add up to 6 samples with their own temperature-τ data. We’ll calculate Ea, Tv, and R² for each.")
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
                    
                    # Data Input
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
                                    parsed_data.append({
                                        "Temperature (°C)": float(temp),
                                        "t (s)": float(tau),
                                        "G0 (MPa)": float(g0) if pd.notna(g0) else None
                                    })
                            text_data = '\n'.join([f"{r['Temperature (°C)']}, {r['t (s)']}" + (f", {r['G0 (MPa)']}" if r.get('G0 (MPa)') is not None else "") for r in parsed_data])
                        except Exception as e:
                            st.error(f"Error parsing CSV: {e}")
                    else:
                        existing_data = st.session_state.comparison_samples.get(sample_key, {}).get('data', [])
                        text_data = '\n'.join([f"{row.get('Temperature (°C)', 0)}, {row.get('t (s)', 0)}" + (f", {row['G0 (MPa)']}" if row.get('G0 (MPa)') is not None else "") for row in existing_data]) if existing_data else ""
                    
                    with st.expander("📝 Manual Data Entry" if uploaded_csv else "📝 Manual Data Entry (Open)", expanded=(uploaded_csv is None)):
                        st.caption("Format: `Temperature, Tau, G0` (G0 is optional for Arrhenius only)")
                        data_input = st.text_area(
                            "Data pairs",
                            value=text_data,
                            height=100,
                            key=f"data_{sample_idx}",
                            label_visibility="collapsed",
                            placeholder="100, 1.5, 50.0\n110, 0.5, 45.0\n120, 0.2, 40.0"
                        )
                        
                        if uploaded_csv is None:
                            try:
                                parsed_data = []
                                for line in data_input.strip().split('\n'):
                                    if line.strip():
                                        parts = line.split(',')
                                        if len(parts) >= 2:
                                            temp = float(parts[0].strip())
                                            tau = float(parts[1].strip())
                                            g0 = float(parts[2].strip()) if len(parts) >= 3 and parts[2].strip() else None
                                            parsed_data.append({"Temperature (°C)": temp, "t (s)": tau, "G0 (MPa)": g0})
                            except:
                                st.error(f"⚠️ Parse error in Sample {sample_idx}. Use format: temp, tau, g0")
                    
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
                    g0_list = []
                    
                    for row in data:
                        t_temp = row.get('Temperature (°C)', 0)
                        tau_val = row.get('t (s)', row.get('τ (s)', 0))
                        g0_val = row.get('G0 (MPa)', None)
                        
                        # Only include data above Tg
                        if t_temp > tg and tau_val > 0:
                            temps.append(t_temp)
                            taus.append(tau_val)
                            if pd.notna(g0_val) and g0_val is not None:
                                g0_list.append(g0_val)
                            else:
                                g0_list.append(np.nan)
                    
                    vh_fit = None
                    if len(temps) >= 3:
                        g0s_clean = [g for g in g0_list if not np.isnan(g)]
                        temps_clean = [temps[i] for i in range(len(temps)) if not np.isnan(g0_list[i])]
                        if len(temps_clean) >= 3:
                            k_engine = KineticsEngine()
                            vh_fit = k_engine.fit_van_t_hoff(temps_clean, g0s_clean)
                    
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
                            slope = fit_res['Params']['slope']
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
                            Tv_val = (1.0 / ((ln_tau_t - intercept)/slope)) - 273.15
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
                            'ln_tau_target': ln_tau_t,
                            'vh_fit': vh_fit,
                            'vh_temps': temps_clean if vh_fit else [],
                            'vh_g0s': g0s_clean if vh_fit else []
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
            comp_tab_arr, comp_tab_vh = st.tabs(["Arrhenius Kinetics", "Van 't Hoff"])
            
            with comp_tab_arr:
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
                        comp_leg_fontsize = st.slider("Font Size", 4, 20, 8, key="comp_leg_fontsize")
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
                        comp_lbl_sz = st.number_input("Label Size", 4, 30, 12, key="comp_lbl_sz")
                        comp_lbl_wt = st.selectbox("Label Weight", ["normal", "bold"], key="comp_lbl_wt")
                        comp_lbl_sty = st.selectbox("Label Style", ["normal", "italic"], key="comp_lbl_sty")

                        st.markdown("**Axis Number Font**")
                        comp_tick_font = st.selectbox("Number Font", ["Same as Label", "Arial", "Times New Roman", "Courier New", "DejaVu Sans", "serif", "sans-serif", "monospace"], key="comp_tick_font")
                        comp_tick_size = st.number_input("Number Size", 4, 30, 10, key="comp_tick_sz")
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

                    # Plot fit line (slope is in 1/T units, x_range is 1000/T, so divide slope by 1000)
                    x_range = np.linspace(inv_T.min() * 0.9, inv_T.max() * 1.1, 50)
                    y_fit = (slope / 1000.0) * x_range + intercept
                    ax_mpl.plot(x_range, y_fit, '--', color=color, linewidth=comp_lw, alpha=0.8, zorder=2)

                    # Plot Tv marker (convert 1/T result to 1000/T axis)
                    if comp_show_tv:
                        tv_x = ((ln_tau_target - intercept) / slope) * 1000.0
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

                            # Fit line (slope is in 1/T units, x_range is 1000/T, so divide slope by 1000)
                            x_range = np.linspace(inv_T.min() * 0.9, inv_T.max() * 1.1, 50)
                            y_fit = (slope / 1000.0) * x_range + intercept
                            fig_comp.add_trace(go.Scatter(
                                x=x_range,
                                y=y_fit,
                                mode='lines',
                                name=f"{name} fit",
                                line=dict(color=color, dash='dash', width=2),
                                showlegend=False,
                                hoverinfo='skip'
                            ))

                            # Tv marker (star) - convert 1/T result to 1000/T axis
                            tv_x = ((ln_tau_target - intercept) / slope) * 1000.0
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
            with comp_tab_vh:
                st.subheader("📈 Van 't Hoff Comparison Plot")
                col_plot_vh, col_settings_vh = st.columns([3, 1])
                
                with col_settings_vh:
                    st.markdown("**Export Settings:**")
                    vh_comp_fmt = st.selectbox("Format", ["png", "jpeg", "bmp", "tiff", "pdf", "svg"], key="vh_comp_fmt")
                    vh_comp_dpi = st.number_input("DPI", 72, 1200, 300, 50, key="vh_comp_dpi")
                    
                    with st.expander("📝 Legend Settings", expanded=False):
                        show_vh_comp_legend = st.checkbox("Show Legend", value=True, key="vh_comp_legend")
                        vh_comp_leg_pos = st.selectbox("Position", ["best", "upper right", "upper left", "lower left", "lower right", "right (outside)"], key="vh_comp_leg_pos")
                        vh_comp_leg_fontsize = st.slider("Font Size", 4, 20, 8, key="vh_comp_leg_fontsize")
                        vh_comp_leg_box = st.checkbox("Box Border", value=True, key="vh_comp_leg_box")
                    
                    with st.expander("📐 Figure Dimensions", expanded=True):
                        vh_comp_width = st.number_input("Width (cm)", 1.0, 40.0, 12.7, 0.1, key="vh_comp_w")
                        vh_comp_height = st.number_input("Height (cm)", 1.0, 40.0, 10.0, 0.1, key="vh_comp_h")
                    
                    with st.expander("🔤 Axis Typography", expanded=False):
                        vh_comp_font_family = st.selectbox("Font Family", ["Arial", "Times New Roman", "Courier New", "DejaVu Sans"], key="vh_comp_font_family")
                        st.markdown("**Axis Label Font**")
                        vh_comp_lbl_sz = st.number_input("Label Size", 4, 30, 12, key="vh_comp_lbl_sz")
                        st.markdown("**Axis Number Font**")
                        vh_comp_tick_size = st.number_input("Number Size", 4, 30, 10, key="vh_comp_tick_sz")
                
                with col_plot_vh:
                    import matplotlib.ticker as ticker
                    
                    fig_vh, ax_vh = plt.subplots(figsize=(vh_comp_width/2.54, vh_comp_height/2.54))
                    
                    colors_mpl = ['#EF553B', '#636EFA', '#00CC96', '#AB63FA', '#FFA15A', '#25D098']
                    
                    valid_vh_results = [r for r in results if r.get('vh_fit') is not None]
                    
                    if not valid_vh_results:
                        st.info("No valid samples with G0 data (need >=3 points) for Van 't Hoff plot.")
                    else:
                        for idx, r in enumerate(valid_vh_results):
                            vh_fit = r['vh_fit']
                            vh_temps = r['vh_temps']
                            vh_g0s = r['vh_g0s']
                            
                            name = st.session_state.comparison_samples.get(r.get('sample_key'), {}).get('name', r['Sample Name'])
                            
                            color = colors_mpl[idx % 6]
                            
                            T_K = np.array(vh_temps) + 273.15
                            inv_T = 1000.0 / T_K
                            
                            ax_vh.scatter(inv_T, vh_g0s, color=color, s=40, edgecolors='black', linewidth=0.8, alpha=0.8, zorder=3)
                            
                            x_range = np.linspace(inv_T.min() * 0.9, inv_T.max() * 1.1, 100)
                            T_range = 1000.0 / x_range
                            exponent = -(vh_fit['dH_diss'] * 1000.0) / (8.314462 * T_range) + vh_fit['dS_diss'] / 8.314462
                            y_fit = vh_fit['G0_max'] / (1.0 + np.exp(np.clip(exponent, -50.0, 50.0)))
                            
                            label_fit = f"{name}: ΔH = {vh_fit['dH_diss']:.1f} kJ/mol"
                            ax_vh.plot(x_range, y_fit, '--', color=color, linewidth=1.5, label=label_fit, zorder=2)
                        
                        ax_vh.set_yscale('log')
                        ax_vh.set_xlabel(r"$1000/T\ (\mathrm{K}^{-1})$", fontdict={'family': vh_comp_font_family, 'size': vh_comp_lbl_sz})
                        ax_vh.set_ylabel(r"$G_0$ (MPa)", fontdict={'family': vh_comp_font_family, 'size': vh_comp_lbl_sz})
                        
                        ax_vh.tick_params(axis='both', labelsize=vh_comp_tick_size)
                        
                        if show_vh_comp_legend:
                            ax_vh.legend(loc=vh_comp_leg_pos, fontsize=vh_comp_leg_fontsize, frameon=vh_comp_leg_box)
                        
                        st.pyplot(fig_vh, dpi=300, bbox_inches='tight')
                        
                        # Export logic
                        import io
                        buf_vh = io.BytesIO()
                        
                        fmt_lower = vh_comp_fmt.lower()
                        if fmt_lower in ['bmp', 'tiff']:
                            buf_tmp = io.BytesIO()
                            fig_vh.savefig(buf_tmp, format='png', dpi=vh_comp_dpi, bbox_inches='tight')
                            buf_tmp.seek(0)
                            from PIL import Image
                            Image.open(buf_tmp).save(buf_vh, format=fmt_lower.upper())
                        else:
                            fig_vh.savefig(buf_vh, format=fmt_lower, dpi=vh_comp_dpi, bbox_inches='tight')
                        buf_vh.seek(0)
                        
                        with col_settings_vh:
                            st.download_button(f"📥 Download Van 't Hoff Figure ({vh_comp_fmt})", buf_vh, f"Van_t_Hoff_Comparison.{fmt_lower}", mime=f"image/{fmt_lower}" if fmt_lower != 'pdf' else 'application/pdf', key="dl_vh_plot")
        else:
            st.info("💡 Fill in samples and click 'Analyze All Samples' to start comparison")


