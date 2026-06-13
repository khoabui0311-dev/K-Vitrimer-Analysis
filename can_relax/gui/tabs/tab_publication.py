import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import io

def render(tab_pub, PLOTLY_STYLE: dict):
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
                        rel_label_size = st.number_input("Label Size", 4, 30, 12, key="pub_rel_lbl_sz")
                    with rls2:
                        rel_label_weight = st.selectbox("Label Weight", ["normal", "bold"], key="pub_rel_lbl_wt")
                    with rls3:
                        rel_label_style = st.selectbox("Label Style", ["normal", "italic"], key="pub_rel_lbl_sty")
                    
                    st.markdown("**Axis Number Font**")
                    rns1, rns2, rns3, rns4 = st.columns(4)
                    with rns1:
                        rel_tick_font = st.selectbox("Number Font", ["Same as Label", "Arial", "Times New Roman", "Courier New", "DejaVu Sans", "serif", "sans-serif", "monospace"], key="pub_rel_num_font")
                    with rns2:
                        rel_tick_size = st.number_input("Number Size", 4, 30, 10, key="pub_rel_num_sz")
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
                        kin_label_size = st.number_input("Label Size ", 4, 30, 12, key="pub_kin_lbl_sz")
                    with kls2:
                        kin_label_weight = st.selectbox("Label Weight ", ["normal", "bold"], key="pub_kin_lbl_wt")
                    with kls3:
                        kin_label_style = st.selectbox("Label Style ", ["normal", "italic"], key="pub_kin_lbl_sty")
                    
                    st.markdown("**Axis Number Font**")
                    kns1, kns2, kns3, kns4 = st.columns(4)
                    with kns1:
                        kin_tick_font = st.selectbox("Number Font ", ["Same as Label", "Arial", "Times New Roman", "Courier New", "DejaVu Sans", "serif", "sans-serif", "monospace"], key="pub_kin_num_font")
                    with kns2:
                        kin_tick_size = st.number_input("Number Size ", 4, 30, 10, key="pub_kin_num_sz")
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
