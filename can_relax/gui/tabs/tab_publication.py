import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import matplotlib as mpl
mpl.rcParams['svg.fonttype'] = 'none'
mpl.rcParams['pdf.fonttype'] = 42
import matplotlib.ticker as ticker
import io
from PIL import Image
import matplotlib.mathtext as mathtext
from can_relax.core.kinetics import KineticsEngine

if not hasattr(mathtext.MathTextParser, '_patched_by_us'):
    _original_parse = mathtext.MathTextParser.parse
    def _safe_parse(self, s, *args, **kwargs):
        if not s or str(s).strip() == "" or str(s).strip() == "$$":
            return _original_parse(self, r"~", *args, **kwargs)
        try:
            return _original_parse(self, s, *args, **kwargs)
        except ValueError:
            return _original_parse(self, r"~", *args, **kwargs)
    mathtext.MathTextParser.parse = _safe_parse
    mathtext.MathTextParser._patched_by_us = True
def save_and_download(fig, title_prefix, pub_colorspace, key_suffix):
    buf_rgb_png = io.BytesIO()
    fig.savefig(buf_rgb_png, format='png', dpi=1200)
    buf_rgb_png.seek(0)
    img = Image.open(buf_rgb_png)

    cmyk_mode = pub_colorspace.startswith("CMYK")
    if cmyk_mode:
        img_out = img.convert('CMYK')
        title_suffix = "_CMYK"
    else:
        if img.mode == 'RGBA':
            bg = Image.new('RGB', img.size, (255, 255, 255))
            bg.paste(img, mask=img.split()[3])
            img_out = bg
        else:
            img_out = img.convert('RGB')
        title_suffix = "_RGB"

    buf_tiff = io.BytesIO()
    img_out.save(buf_tiff, format='TIFF', dpi=(1200, 1200), compression='tiff_lzw' if cmyk_mode else None)
    buf_tiff.seek(0)

    buf_jpg = io.BytesIO()
    img_out.save(buf_jpg, format='JPEG', dpi=(600, 600), quality=95)
    buf_jpg.seek(0)

    dc1, dc2 = st.columns(2)
    with dc1:
        st.download_button(f"📥 Download TIFF (1200 DPI)", buf_tiff, f"{title_prefix}{title_suffix}.tiff", key=f"dl_tiff_{key_suffix}")
    with dc2:
        st.download_button(f"📥 Download JPEG (600 DPI)", buf_jpg, f"{title_prefix}{title_suffix}.jpg", key=f"dl_jpg_{key_suffix}")


def render(tab_pub, PLOTLY_STYLE: dict, Tg_input: float, G_prime_input: float):
    with tab_pub:
        st.header("📝 Publication Figures")
        if 'active_results' in st.session_state and st.session_state.active_results:
            active_res = st.session_state.active_results
            kinetics_df = st.session_state.get('kinetics_df', pd.DataFrame())
            
            x_unit_sel_temp = st.session_state.get('pub_xunit', 'Seconds (s)')
            y_norm_sel_temp = st.session_state.get('pub_ynorm', 'Normalized (G/G₀ or E/E₀)')
            x_factor_temp = 60.0 if x_unit_sel_temp == "Minutes (min)" else 3600.0 if x_unit_sel_temp == "Hours (h)" else 1.0
            
            all_times_temp = np.concatenate([r['Raw']['t'] / x_factor_temp for r in active_res])
            auto_rel_xmin = float(all_times_temp.min() * 0.8)
            auto_rel_xmax = float(all_times_temp.max() * 1.2)
            is_norm_temp = y_norm_sel_temp.startswith("Normal")
            if is_norm_temp:
                auto_rel_ymin, auto_rel_ymax = 0.0, 1.05
            else:
                max_y_temp = max([np.max(r['Raw']['g'] * r['Raw'].get('G0', 1.0)) for r in active_res])
                auto_rel_ymin, auto_rel_ymax = 0.0, float(max_y_temp * 1.05)

            # Pre-calculate kinetics bounds
            auto_vh_ymin, auto_vh_ymax = 0.1, 1000.0
            if not kinetics_df.empty:
                active_k_temp = kinetics_df[kinetics_df['Include']==True]
                if not active_k_temp.empty and len(active_k_temp) >= 2:
                    auto_kin_xmin = float(active_k_temp['1000/T'].min() * 0.95)
                    auto_kin_xmax = float(active_k_temp['1000/T'].max() * 1.05)
                    auto_kin_ymin = float(active_k_temp['ln(Tau)'].min() - 0.5)
                    auto_kin_ymax = float(active_k_temp['ln(Tau)'].max() + 0.5)
                    
                    g0_vals = []
                    if 'analysis_results' in st.session_state:
                        for t in active_k_temp['Temp']:
                            match = next((r for r in st.session_state['analysis_results'] if r.get('Temp') == t), None)
                            if match and 'Raw' in match and 'G0' in match['Raw']:
                                g0_vals.append(match['Raw']['G0'])
                    if g0_vals:
                        auto_vh_ymin = float(max(1e-6, min(g0_vals)) * 0.5)
                        auto_vh_ymax = float(max(g0_vals) * 2.0)
                else:
                    auto_kin_xmin, auto_kin_xmax, auto_kin_ymin, auto_kin_ymax = 2.0, 3.5, -2.0, 10.0
            else:
                auto_kin_xmin, auto_kin_xmax, auto_kin_ymin, auto_kin_ymax = 2.0, 3.5, -2.0, 10.0

            pan_settings, pan_preview = st.columns([1, 2], gap="large")

            with pan_settings:
                st.markdown("### ⚙️ Settings")

                with st.expander("📐 Global Figure Settings", expanded=True):
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
                    with sz1: fig_width = st.number_input("Width (cm)", 1.0, 40.0, float(default_width), 0.1, disabled=disable_size, key="pub_w")
                    with sz2: fig_height = st.number_input("Height (cm)", 1.0, 40.0, float(default_height), 0.1, disabled=disable_size, key="pub_h")

                    st.markdown("**Panel Letter Font**")
                    pl1, pl2 = st.columns(2)
                    with pl1:
                        panel_font_family = st.selectbox("Panel Font Family", ["Arial", "Times New Roman", "Courier New", "DejaVu Sans", "serif", "sans-serif", "monospace"], key="pub_panel_font_family")
                        panel_font_weight = st.selectbox("Panel Font Weight", ["normal", "bold"], key="pub_panel_weight")
                    with pl2:
                        panel_font_size = st.number_input("Panel Font Size", 4, 30, 12, key="pub_panel_size")
                        panel_font_style = st.selectbox("Panel Font Style", ["normal", "italic"], key="pub_panel_style")
                    
                    pub_colorspace = st.selectbox("Color Space Mode", ["RGB", "CMYK (for Print/Publication)"], key="pub_colorspace")

                # ==============================================================================
                # RELAXATION CURVES CONFIG
                # ==============================================================================
                with st.expander("📈 Fig 1: Relaxation Curves", expanded=False):
                    show_fig1 = st.checkbox("Generate Fig 1", value=True, key="sh_fig1")
                    if show_fig1:
                        f1_pan_c1, f1_pan_c2 = st.columns(2)
                        with f1_pan_c1: panel_l_1 = st.text_input("Panel Letter", "a", key="pl_1")
                        with f1_pan_c2:
                            pl_x_1 = st.number_input("X pos", -1.0, 2.0, -0.12, 0.01, key="plx_1")
                            pl_y_1 = st.number_input("Y pos", -1.0, 2.0, 1.02, 0.01, key="ply_1")

                        y_label_select = st.selectbox("Modulus Notation", ["G (Shear Modulus)", "E (Tensile Modulus)"], key="pub_ylabel")
                        y_norm_select = st.selectbox("Normalization", ["Normalized (G/G₀ or E/E₀)", "Non-Normalized (G or E)"], key="pub_ynorm")
                        curve_style = st.selectbox("Data Style", ["Continuous Lines (Raw)", "Markers Only", "Lines + Markers"], key="pub_style")
                        ax1c, ax2c, ax3c = st.columns(3)
                        with ax1c: pub_time_axis = st.selectbox("Time Scale", ["Log", "Linear"], key="pub_xscale")
                        with ax2c: pub_y_scale = st.selectbox("Y-Axis Scale", ["Linear", "Log"], key="pub_yscale")
                        with ax3c: x_unit_select = st.selectbox("Time Unit", ["Seconds (s)", "Minutes (min)", "Hours (h)"], key="pub_xunit")
                        
                        chk1, chk2, chk3 = st.columns(3)
                        with chk1: show_fit_pub = st.checkbox("Fits", value=False, key="pub_showfit")
                        with chk2: show_tau_star = st.checkbox("τ* mark", value=True, key="pub_taustar")
                        with chk3: annotate_tau_star = st.checkbox("τ* label", value=False, key="pub_taulabel")

                        rc1, rc2, rc3 = st.columns(3)
                        with rc1: rel_line_width = st.slider("Line Width", 0.5, 6.0, 1.5, 0.5, key="pub_rel_lw")
                        with rc2: rel_marker_size = st.slider("Marker Size", 1, 15, 4, 1, key="pub_rel_ms")
                        with rc3: rel_marker_density = st.slider("Marker Density (%)", 0, 100, 20, 5, key="pub_rel_md")

                        rel_font_family = st.selectbox("Font Family", ["Arial", "Times New Roman", "Courier New", "DejaVu Sans"], key="pub_relfont_family")
                        rls1, rls2, rls3 = st.columns(3)
                        with rls1: rel_label_size = st.number_input("Label Size", 4, 30, 12, key="pub_rel_lbl_sz")
                        with rls2: rel_label_weight = st.selectbox("Label Weight", ["normal", "bold"], key="pub_rel_lbl_wt")
                        with rls3: rel_label_style = st.selectbox("Label Style", ["normal", "italic"], key="pub_rel_lbl_sty")
                        
                        rns1, rns2, rns3, rns4 = st.columns(4)
                        with rns1: rel_tick_font = st.selectbox("Num Font", ["Same as Label", "Arial", "Times New Roman"], key="pub_rel_num_font")
                        with rns2: rel_tick_size = st.number_input("Num Size", 4, 30, 10, key="pub_rel_num_sz")
                        with rns3: rel_tick_weight = st.selectbox("Num Wt", ["normal", "bold"], key="pub_rel_num_wt")
                        with rns4: rel_tick_style = st.selectbox("Num Sty", ["normal", "italic"], key="pub_rel_num_sty")

                        rel_mirror = st.checkbox("Mirror Ticks to Top/Right", value=False, key="pub_rel_mirror")
                        rel_custom_lims = st.checkbox("Manual Axis Bounding", value=False, key="pub_rel_cust_lims")
                        if rel_custom_lims:
                            xlim_col1, xlim_col2 = st.columns(2)
                            ylim_col1, ylim_col2 = st.columns(2)
                            with xlim_col1: rel_xmin = st.number_input("X Min (Time)", value=auto_rel_xmin, format="%.3e", key="pub_rel_xmin")
                            with xlim_col2: rel_xmax = st.number_input("X Max (Time)", value=auto_rel_xmax, format="%.3e", key="pub_rel_xmax")
                            with ylim_col1: rel_ymin = st.number_input("Y Min (Modulus)", value=auto_rel_ymin, format="%.3e", key="pub_rel_ymin")
                            with ylim_col2: rel_ymax = st.number_input("Y Max (Modulus)", value=auto_rel_ymax, format="%.3e", key="pub_rel_ymax")

                        show_rel_leg = st.checkbox("Show Legend", value=True, key="pub_relleg")
                        if show_rel_leg:
                            rel_leg_pos = st.selectbox("Position", ["Best (Auto)", "Upper Right", "Upper Left", "Lower Left", "Lower Right", "Right (Outside)"], key="pub_relpos")
                            rnc1, rnc2 = st.columns(2)
                            with rnc1: rel_leg_ncol = st.number_input("Columns", 1, 10, 1, key="pub_relncol")
                            with rnc2: rel_leg_font_size = st.slider("Font Size", 4, 16, 8, key="pub_relfont")
                            rel_leg_box = st.checkbox("Box Border", value=False, key="pub_relbox")
                        else:
                            rel_leg_pos, rel_leg_font_size, rel_leg_box, rel_leg_ncol = "Best (Auto)", 8, False, 1

                # ==============================================================================
                # TAU KINETICS CONFIG
                # ==============================================================================
                with st.expander("🔥 Fig 2: Tau Kinetics (Arrhenius / VFT)", expanded=False):
                    show_fig2 = st.checkbox("Generate Fig 2", value=True, key="sh_fig2")
                    if show_fig2:
                        f2_pan_c1, f2_pan_c2 = st.columns(2)
                        with f2_pan_c1: panel_l_2 = st.text_input("Panel Letter", "b", key="pl_2")
                        with f2_pan_c2:
                            pl_x_2 = st.number_input("X pos ", -1.0, 2.0, -0.12, 0.01, key="plx_2")
                            pl_y_2 = st.number_input("Y pos ", -1.0, 2.0, 1.02, 0.01, key="ply_2")

                        tau_kin_model = st.selectbox("Tau Kinetics Model", ["Arrhenius", "VFT"], key="f2_model")
                        chk4, chk5 = st.columns(2)
                        with chk4: show_tv = st.checkbox("Show T_v", value=True, key="pub_showtv", disabled=(tau_kin_model != "Arrhenius"))
                        with chk5: show_ea_std = st.checkbox("Ea ± std", value=True, key="pub_eastd", disabled=(tau_kin_model != "Arrhenius"))

                        kc1, kc2 = st.columns(2)
                        with kc1: kin_line_width = st.slider("Fit Line Width", 0.5, 6.0, 1.5, 0.5, key="pub_kin_lw")
                        with kc2: kin_marker_size = st.slider("Data Marker Size", 1, 15, 6, 1, key="pub_kin_ms")

                        kin_font_family = st.selectbox("Font Family ", ["Arial", "Times New Roman", "Courier New", "DejaVu Sans"], key="pub_kinfont_family")
                        kls1, kls2, kls3 = st.columns(3)
                        with kls1: kin_label_size = st.number_input("Label Size ", 4, 30, 12, key="pub_kin_lbl_sz")
                        with kls2: kin_label_weight = st.selectbox("Label Weight ", ["normal", "bold"], key="pub_kin_lbl_wt")
                        with kls3: kin_label_style = st.selectbox("Label Style ", ["normal", "italic"], key="pub_kin_lbl_sty")
                        kns1, kns2, kns3, kns4 = st.columns(4)
                        with kns1: kin_tick_font = st.selectbox("Num Font ", ["Same as Label", "Arial", "Times New Roman"], key="pub_kin_num_font")
                        with kns2: kin_tick_size = st.number_input("Num Size ", 4, 30, 10, key="pub_kin_num_sz")
                        with kns3: kin_tick_weight = st.selectbox("Num Weight ", ["normal", "bold"], key="pub_kin_num_wt")
                        with kns4: kin_tick_style = st.selectbox("Num Style ", ["normal", "italic"], key="pub_kin_num_sty")

                        kin_mirror = st.checkbox("Mirror Ticks to Top/Right ", value=False, key="pub_kin_mirror")
                        kin_custom_lims = st.checkbox("Manual Axis Bounding ", value=False, key="pub_kin_cust_lims")
                        if kin_custom_lims:
                            kxlim_col1, kxlim_col2 = st.columns(2)
                            kylim_col1, kylim_col2 = st.columns(2)
                            with kxlim_col1: kin_xmin = st.number_input("X Min (1000/T)", value=auto_kin_xmin, format="%.4f", key="pub_kin_xmin")
                            with kxlim_col2: kin_xmax = st.number_input("X Max (1000/T)", value=auto_kin_xmax, format="%.4f", key="pub_kin_xmax")
                            with kylim_col1: kin_ymin = st.number_input("Y Min (ln(τ))", value=auto_kin_ymin, format="%.4f", key="pub_kin_ymin")
                            with kylim_col2: kin_ymax = st.number_input("Y Max (ln(τ))", value=auto_kin_ymax, format="%.4f", key="pub_kin_ymax")

                        show_kin_leg = st.checkbox("Show Legend ", value=True, key="pub_kinleg")
                        if show_kin_leg:
                            kin_leg_pos = st.selectbox("Position ", ["Best (Auto)", "Upper Right", "Upper Left", "Lower Left", "Lower Right", "Right (Outside)"], key="pub_kinpos")
                            knc1, knc2 = st.columns(2)
                            with knc1: kin_leg_ncol = st.number_input("Columns ", 1, 10, 1, key="pub_kinncol")
                            with knc2: kin_leg_font_size = st.slider("Font Size ", 4, 16, 8, key="pub_kinfont")
                            kin_leg_box = st.checkbox("Box Border ", value=False, key="pub_kinbox")
                        else:
                            kin_leg_pos, kin_leg_font_size, kin_leg_box, kin_leg_ncol = "Best (Auto)", 8, False, 1

                # ==============================================================================
                # EYRING CONFIG
                # ==============================================================================
                with st.expander("⚛️ Fig 3: Eyring Kinetics", expanded=False):
                    show_fig3 = st.checkbox("Generate Fig 3 (Eyring)", value=False, key="sh_fig3")
                    if show_fig3:
                        f3_pan_c1, f3_pan_c2 = st.columns(2)
                        with f3_pan_c1: panel_l_3 = st.text_input("Panel Letter  ", "c", key="pl_3")
                        with f3_pan_c2:
                            pl_x_3 = st.number_input("X pos  ", -1.0, 2.0, -0.12, 0.01, key="plx_3")
                            pl_y_3 = st.number_input("Y pos  ", -1.0, 2.0, 1.02, 0.01, key="ply_3")
                        ec1, ec2 = st.columns(2)
                        with ec1: eyr_line_width = st.slider("Fit Line Width", 0.5, 6.0, 1.5, 0.5, key="eyr_lw")
                        with ec2: eyr_marker_size = st.slider("Data Marker Size", 1, 15, 6, 1, key="eyr_ms")
                        eyr_font_family = st.selectbox("Font Family", ["Arial", "Times New Roman", "Courier New", "DejaVu Sans"], key="eyr_ff")
                        els1, els2, els3 = st.columns(3)
                        with els1: eyr_label_size = st.number_input("Label Size", 4, 30, 12, key="eyr_lsz")
                        with els2: eyr_label_weight = st.selectbox("Label Weight", ["normal", "bold"], key="eyr_lwt")
                        with els3: eyr_label_style = st.selectbox("Label Style", ["normal", "italic"], key="eyr_lst")
                        ens1, ens2, ens3, ens4 = st.columns(4)
                        with ens1: eyr_tick_font = st.selectbox("Num Font", ["Same as Label", "Arial", "Times New Roman"], key="eyr_nf")
                        with ens2: eyr_tick_size = st.number_input("Num Size", 4, 30, 10, key="eyr_nsz")
                        with ens3: eyr_tick_weight = st.selectbox("Num Weight", ["normal", "bold"], key="eyr_nwt")
                        with ens4: eyr_tick_style = st.selectbox("Num Style", ["normal", "italic"], key="eyr_nst")
                        eyr_mirror = st.checkbox("Mirror Ticks to Top/Right", value=False, key="eyr_mir")
                        eyr_custom_lims = st.checkbox("Manual Axis Bounding", value=False, key="eyr_clim")
                        if eyr_custom_lims:
                            ex1, ex2 = st.columns(2)
                            ey1, ey2 = st.columns(2)
                            with ex1: eyr_xmin = st.number_input("X Min", value=auto_kin_xmin, format="%.4f", key="eyr_xmin")
                            with ex2: eyr_xmax = st.number_input("X Max", value=auto_kin_xmax, format="%.4f", key="eyr_xmax")
                            with ey1: eyr_ymin = st.number_input("Y Min", value=auto_kin_ymin, format="%.4f", key="eyr_ymin")
                            with ey2: eyr_ymax = st.number_input("Y Max", value=auto_kin_ymax, format="%.4f", key="eyr_ymax")
                        show_eyr_leg = st.checkbox("Show Legend ", value=True, key="eyr_leg")
                        if show_eyr_leg:
                            eyr_leg_pos = st.selectbox("Position ", ["Best (Auto)", "Upper Right", "Upper Left", "Lower Left", "Lower Right", "Right (Outside)"], key="eyr_legpos")
                            enc1, enc2 = st.columns(2)
                            with enc1: eyr_leg_ncol = st.number_input("Columns ", 1, 10, 1, key="eyr_legncol")
                            with enc2: eyr_leg_font_size = st.slider("Font Size ", 4, 16, 8, key="eyr_legfont")
                            eyr_leg_box = st.checkbox("Box Border ", value=False, key="eyr_legbox")
                        else:
                            eyr_leg_pos, eyr_leg_font_size, eyr_leg_box, eyr_leg_ncol = "Best (Auto)", 8, False, 1

                # ==============================================================================
                # VAN T HOFF CONFIG
                # ==============================================================================
                with st.expander("🌡️ Fig 4: Van 't Hoff (Decrosslinking)", expanded=False):
                    show_fig4 = st.checkbox("Generate Fig 4 (Van 't Hoff)", value=False, key="sh_fig4")
                    if show_fig4:
                        f4_pan_c1, f4_pan_c2 = st.columns(2)
                        with f4_pan_c1: panel_l_4 = st.text_input("Panel Letter   ", "d", key="pl_4")
                        with f4_pan_c2:
                            pl_x_4 = st.number_input("X pos   ", -1.0, 2.0, -0.12, 0.01, key="plx_4")
                            pl_y_4 = st.number_input("Y pos   ", -1.0, 2.0, 1.02, 0.01, key="ply_4")
                        vc1, vc2 = st.columns(2)
                        with vc1: vh_line_width = st.slider("Fit Line Width", 0.5, 6.0, 1.5, 0.5, key="vh_lw")
                        with vc2: vh_marker_size = st.slider("Data Marker Size", 1, 15, 6, 1, key="vh_ms")
                        vh_font_family = st.selectbox("Font Family", ["Arial", "Times New Roman", "Courier New", "DejaVu Sans"], key="vh_ff")
                        vls1, vls2, vls3 = st.columns(3)
                        with vls1: vh_label_size = st.number_input("Label Size", 4, 30, 12, key="vh_lsz")
                        with vls2: vh_label_weight = st.selectbox("Label Weight", ["normal", "bold"], key="vh_lwt")
                        with vls3: vh_label_style = st.selectbox("Label Style", ["normal", "italic"], key="vh_lst")
                        vns1, vns2, vns3, vns4 = st.columns(4)
                        with vns1: vh_tick_font = st.selectbox("Num Font", ["Same as Label", "Arial", "Times New Roman"], key="vh_nf")
                        with vns2: vh_tick_size = st.number_input("Num Size", 4, 30, 10, key="vh_nsz")
                        with vns3: vh_tick_weight = st.selectbox("Num Weight", ["normal", "bold"], key="vh_nwt")
                        with vns4: vh_tick_style = st.selectbox("Num Style", ["normal", "italic"], key="vh_nst")
                        vh_mirror = st.checkbox("Mirror Ticks to Top/Right", value=False, key="vh_mir")
                        vh_custom_lims = st.checkbox("Manual Axis Bounding", value=False, key="vh_clim")
                        if vh_custom_lims:
                            vx1, vx2 = st.columns(2)
                            vy1, vy2 = st.columns(2)
                            with vx1: vh_xmin = st.number_input("X Min", value=auto_kin_xmin, format="%.4f", key="vh_xmin")
                            with vx2: vh_xmax = st.number_input("X Max", value=auto_kin_xmax, format="%.4f", key="vh_xmax")
                            with vy1: vh_ymin = st.number_input("Y Min", value=auto_vh_ymin, format="%.4f", key="vh_ymin")
                            with vy2: vh_ymax = st.number_input("Y Max", value=auto_vh_ymax, format="%.4f", key="vh_ymax")
                        vh_y_scale = st.selectbox("Y Axis Scale ", ["Linear", "Log"], key="vh_yscale")
                        show_vh_leg = st.checkbox("Show Legend ", value=True, key="vh_leg")
                        if show_vh_leg:
                            vh_leg_pos = st.selectbox("Position ", ["Best (Auto)", "Upper Right", "Upper Left", "Lower Left", "Lower Right", "Right (Outside)"], key="vh_legpos")
                            vnc1, vnc2 = st.columns(2)
                            with vnc1: vh_leg_ncol = st.number_input("Columns ", 1, 10, 1, key="vh_legncol")
                            with vnc2: vh_leg_font_size = st.slider("Font Size ", 4, 16, 8, key="vh_legfont")
                            vh_leg_box = st.checkbox("Box Border ", value=False, key="vh_legbox")
                        else:
                            vh_leg_pos, vh_leg_font_size, vh_leg_box, vh_leg_ncol = "Best (Auto)", 8, False, 1

            # ── Right panel: figure previews ──────────────────────────────
            with pan_preview:
                color_palette = ['#1b9e77', '#d95f02', '#7570b3', '#e7298a', '#66a61e', '#e6ab02', '#a6761d', '#666666']
                
                # Helper function for legends
                def apply_legend(ax, pos, box, fontsize=8, ncol=1):
                    l_pos = 'best'; l_anchor = None
                    if pos == "Upper Right": l_pos = 'upper right'
                    elif pos == "Upper Left": l_pos = 'upper left'
                    elif pos == "Lower Left": l_pos = 'lower left'
                    elif pos == "Lower Right": l_pos = 'lower right'
                    elif pos == "Right (Outside)": l_pos = 'upper left'; l_anchor = (1.02, 1.0)
                    ax.legend(frameon=box, loc=l_pos, bbox_to_anchor=l_anchor, fontsize=fontsize, ncol=ncol, columnspacing=1.0, handletextpad=0.5)

                # ================= FIGURE 1 =================
                if 'show_fig1' in locals() and show_fig1:
                    st.subheader("📊 Figure 1: Relaxation Curves")
                    rel_num_family = rel_font_family if rel_tick_font == "Same as Label" else rel_tick_font
                    with plt.rc_context({
                        'font.family': rel_num_family,
                        'xtick.labelsize': rel_tick_size,
                        'ytick.labelsize': rel_tick_size,
                        'axes.unicode_minus': False,
                    }):
                        fig1, ax1 = plt.subplots(figsize=(fig_width / 2.54, fig_height / 2.54), facecolor='white')
                        ax1.set_facecolor('white')
                        ax1.grid(False)
                        for spine in ['top', 'bottom', 'left', 'right']:
                            ax1.spines[spine].set_linewidth(1.0)
                            ax1.spines[spine].set_color('black')
                        ax1.tick_params(axis='both', which='major', width=1.0, length=4, direction='in', color='black', top=rel_mirror, right=rel_mirror)
                        ax1.tick_params(axis='both', which='minor', width=0.8, length=2.5, direction='in', color='black', top=rel_mirror, right=rel_mirror)

                        if pub_time_axis != "Log": ax1.xaxis.set_minor_locator(ticker.AutoMinorLocator())
                        else:
                            ax1.xaxis.set_major_locator(ticker.LogLocator(base=10.0))
                            ax1.xaxis.set_minor_locator(ticker.LogLocator(base=10.0, subs=(2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0)))
                        
                        if pub_y_scale != "Log": ax1.yaxis.set_minor_locator(ticker.AutoMinorLocator())
                        else:
                            ax1.yaxis.set_major_locator(ticker.LogLocator(base=10.0))
                            ax1.yaxis.set_minor_locator(ticker.LogLocator(base=10.0, subs=(2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0)))

                        font_label_rel = {'family': rel_font_family, 'size': rel_label_size, 'weight': rel_label_weight, 'style': rel_label_style}

                        if x_unit_select == "Minutes (min)": x_factor, x_label = 60.0, "min"
                        elif x_unit_select == "Hours (h)": x_factor, x_label = 3600.0, "h"
                        else: x_factor, x_label = 1.0, "s"

                        is_normalized = y_norm_select.startswith("Normal")
                        if is_normalized: y_label_text = r"$G(t) / G_0$" if y_label_select.startswith("G") else r"$E(t) / E_0$"
                        else: y_label_text = r"$G(t)$ (MPa)" if y_label_select.startswith("G") else r"$E(t)$ (MPa)"

                        for idx, r in enumerate(active_res):
                            t_raw = r['Raw']['t']
                            g_norm = r['Raw']['g']
                            G0 = r['Raw'].get('G0', 1.0)
                            t_plot = t_raw / x_factor
                            g_plot = g_norm if is_normalized else g_norm * G0
                            color = color_palette[idx % len(color_palette)]
                            label_name = f"{r['Temp']}°C"

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
                        if pub_time_axis == "Log": ax1.set_xscale('log')
                        if pub_y_scale == "Log": ax1.set_yscale('log')

                        ax1.set_xlabel(r"Time, $t$ ({})".format(x_label), fontdict=font_label_rel, labelpad=8)
                        ax1.set_ylabel(y_label_text, fontdict=font_label_rel, labelpad=8)

                        if rel_custom_lims:
                            ax1.set_xlim(rel_xmin, rel_xmax)
                            ax1.set_ylim(rel_ymin, rel_ymax)
                        else:
                            if is_normalized:
                                if pub_y_scale == "Log": ax1.set_ylim(1e-3, 1.05)
                                else: ax1.set_ylim(0, 1.05)
                            else:
                                max_y = max([np.max(r['Raw']['g'] * r['Raw'].get('G0', 1.0)) for r in active_res])
                                if pub_y_scale == "Log":
                                    min_y = min([np.min(r['Raw']['g'] * r['Raw'].get('G0', 1.0)) for r in active_res])
                                    if min_y <= 0: min_y = max_y * 1e-4
                                    ax1.set_ylim(min_y * 0.8, max_y * 1.2)
                                else:
                                    ax1.set_ylim(0, max_y * 1.05)
                            all_times = np.concatenate([r['Raw']['t'] / x_factor for r in active_res])
                            ax1.set_xlim(all_times.min() * 0.8, all_times.max() * 1.2)

                        if show_rel_leg: apply_legend(ax1, rel_leg_pos, rel_leg_box, fontsize=rel_leg_font_size, ncol=rel_leg_ncol)

                        if panel_l_1:
                            ax1.text(pl_x_1, pl_y_1, f"({panel_l_1})", transform=ax1.transAxes,
                                     fontfamily=panel_font_family, fontsize=panel_font_size,
                                     fontweight=panel_font_weight, fontstyle=panel_font_style,
                                     va='bottom', ha='right')

                        plt.tight_layout()
                        st.pyplot(fig1, dpi=300)
                        save_and_download(fig1, "Relaxation_Curves", pub_colorspace, "f1")
                        plt.close(fig1)

                # ================= FIGURE 2: Tau Kinetics =================
                if 'show_fig2' in locals() and show_fig2 and not kinetics_df.empty:
                    st.markdown("---")
                    st.subheader(f"🔥 Figure 2: {tau_kin_model} Plot")
                    active_k = kinetics_df[kinetics_df['Include']==True]
                    if not active_k.empty and len(active_k) >= 2:
                        k_engine_pub = KineticsEngine()
                        temps_list = active_k['Temp'].tolist()
                        taus_list  = active_k['Tau'].tolist()
                        
                        fit_res_pub = k_engine_pub.fit_arrhenius(temps_list, taus_list) if tau_kin_model == "Arrhenius" else k_engine_pub.fit_vft(temps_list, taus_list)
                        
                        if fit_res_pub:
                            r_sq_pub = fit_res_pub.get('R2', 0.0)
                            if tau_kin_model == "Arrhenius":
                                Ea_pub, Ea_std_pub = fit_res_pub['Ea'], fit_res_pub['Ea_std']
                                slope_pub, intercept_pub = fit_res_pub['Params']['slope'], fit_res_pub['Params']['intercept']
                                G_Pa_pub = G_prime_input * 1e6
                                tau_target_pub = 1e12 / G_Pa_pub
                                ln_tau_t_pub = np.log(tau_target_pub)
                                Tv_pub = (1.0 / ((ln_tau_t_pub - intercept_pub)/slope_pub)) - 273.15 if slope_pub != 0 else 0
                                
                                c1, c2, c3 = st.columns(3)
                                c1.metric("Ea", f"{Ea_pub:.1f} ± {Ea_std_pub:.1f} kJ/mol" if show_ea_std else f"{Ea_pub:.1f} kJ/mol")
                                if show_tv: c2.metric("Tv", f"{Tv_pub:.1f} °C")
                                c3.metric("R²", f"{r_sq_pub:.4f}")
                            else:
                                B_pub, T0_pub = fit_res_pub['Params']['B'], fit_res_pub['Params']['T0'] - 273.15
                                c1, c2, c3 = st.columns(3)
                                c1.metric("B", f"{B_pub:.1f} K")
                                c2.metric("T₀", f"{T0_pub:.1f} °C")
                                c3.metric("R²", f"{r_sq_pub:.4f}")

                            kin_num_family = kin_font_family if kin_tick_font == "Same as Label" else kin_tick_font
                            with plt.rc_context({
                                'font.family': kin_num_family,
                                'xtick.labelsize': kin_tick_size,
                                'ytick.labelsize': kin_tick_size,
                                'axes.unicode_minus': False,
                            }):
                                fig2, ax2 = plt.subplots(figsize=(fig_width / 2.54, fig_height / 2.54), facecolor='white')
                                ax2.grid(False)
                                for spine in ['top', 'bottom', 'left', 'right']:
                                    ax2.spines[spine].set_linewidth(1.0); ax2.spines[spine].set_color('black')
                                ax2.tick_params(axis='both', which='major', width=1.0, length=4, direction='in', color='black', top=kin_mirror, right=kin_mirror)
                                ax2.tick_params(axis='both', which='minor', width=0.8, length=2.5, direction='in', color='black', top=kin_mirror, right=kin_mirror)
                                ax2.xaxis.set_minor_locator(ticker.AutoMinorLocator())
                                ax2.yaxis.set_minor_locator(ticker.AutoMinorLocator())

                                font_label_kin = {'family': kin_font_family, 'size': kin_label_size, 'weight': kin_label_weight, 'style': kin_label_style}

                                T_K_all = np.array(temps_list) + 273.15
                                
                                if tau_kin_model == "Arrhenius":
                                    x_data = fit_res_pub['Plot']['x'] * 1000.0
                                    y_data = fit_res_pub['Plot']['y']
                                    ax2.scatter(x_data, y_data, s=kin_marker_size**2, alpha=0.8, edgecolors='black', linewidth=0.8, color='steelblue', zorder=3)
                                    x_range = np.linspace(x_data.min() * 0.95, x_data.max() * 1.05, 100)
                                    y_fit = (slope_pub / 1000.0) * x_range + intercept_pub
                                    label_fit = r"$E_\mathrm{a} = %.1f \pm %.1f\ \mathrm{kJ\ mol}^{-1}$" % (Ea_pub, Ea_std_pub) if show_ea_std else r"$E_\mathrm{a} = %.1f\ \mathrm{kJ\ mol}^{-1}$" % Ea_pub
                                    label_fit += "\n" + r"$R^2 = %.4f$" % r_sq_pub
                                    ax2.plot(x_range, y_fit, '--', color='red', linewidth=kin_line_width, label=label_fit, zorder=2)
                                    
                                    if show_tv:
                                        Tv_x_1000 = ((ln_tau_t_pub - intercept_pub) / slope_pub) * 1000.0
                                        ax2.plot([Tv_x_1000], [ln_tau_t_pub], marker='*', markersize=kin_marker_size * 2, color='gold', markeredgecolor='black', markeredgewidth=0.8, label=r"$T_\mathrm{v} = %.1f^\circ\mathrm{C}$" % Tv_pub, zorder=4)
                                else:
                                    inv_T = 1.0 / T_K_all
                                    ln_tau = np.log(np.array(taus_list))
                                    ax2.scatter(inv_T * 1000, ln_tau, s=kin_marker_size**2, alpha=0.8, edgecolors='black', linewidth=0.8, color='steelblue', zorder=3)
                                    T_K_grid = np.linspace(T_K_all.min() * 0.97, T_K_all.max() * 1.03, 150)
                                    y_fit = B_pub + B_pub / (T_K_grid - (T0_pub + 273.15)) if tau_kin_model == "VFT" else B_pub / (T_K_grid - (T0_pub+273.15))
                                    y_fit = fit_res_pub['Params']['A'] + fit_res_pub['Params']['B'] / (T_K_grid - fit_res_pub['Params']['T0'])
                                    label_fit = r"VFT: $B = %.0f\ \mathrm{K},\ T_0 = %.1f^\circ\mathrm{C}$" % (B_pub, T0_pub)
                                    label_fit += "\n" + r"$R^2 = %.4f$" % r_sq_pub
                                    ax2.plot(1000 / T_K_grid, y_fit, '--', color='red', linewidth=kin_line_width, label=label_fit, zorder=2)

                                ax2.set_xlabel(r"$1000/T\ (\mathrm{K}^{-1})$", fontdict=font_label_kin, labelpad=8)
                                ax2.set_ylabel(r"$\ln(\tau)$", fontdict=font_label_kin, labelpad=8)

                                if kin_custom_lims:
                                    ax2.set_xlim(kin_xmin, kin_xmax)
                                    ax2.set_ylim(kin_ymin, kin_ymax)
                                
                                if show_kin_leg: apply_legend(ax2, kin_leg_pos, kin_leg_box, fontsize=kin_leg_font_size, ncol=kin_leg_ncol)

                                if panel_l_2:
                                    ax2.text(pl_x_2, pl_y_2, f"({panel_l_2})", transform=ax2.transAxes,
                                             fontfamily=panel_font_family, fontsize=panel_font_size,
                                             fontweight=panel_font_weight, fontstyle=panel_font_style,
                                             va='bottom', ha='right')

                                plt.tight_layout()
                                st.pyplot(fig2, dpi=300)
                                save_and_download(fig2, "Tau_Kinetics", pub_colorspace, "f2")
                                plt.close(fig2)

                # ================= FIGURE 3: EYRING =================
                if 'show_fig3' in locals() and show_fig3 and not kinetics_df.empty:
                    st.markdown("---")
                    st.subheader(f"⚛️ Figure 3: Eyring Plot")
                    active_k = kinetics_df[kinetics_df['Include']==True]
                    if not active_k.empty and len(active_k) >= 2:
                        k_engine_pub = KineticsEngine()
                        temps_list = active_k['Temp'].tolist()
                        taus_list  = active_k['Tau'].tolist()
                        fit_res_pub = k_engine_pub.fit_eyring(temps_list, taus_list)
                        if fit_res_pub:
                            c1, c2, c3 = st.columns(3)
                            c1.metric("ΔH‡", f"{fit_res_pub['dH']:.1f} ± {fit_res_pub['dH_std']:.1f} kJ/mol")
                            c2.metric("ΔS‡", f"{fit_res_pub['dS']:.1f} J/mol·K")
                            c3.metric("R²", f"{fit_res_pub.get('R2',0):.4f}")

                            with plt.rc_context({'font.family': eyr_tick_font if eyr_tick_font != 'Same as Label' else eyr_font_family, 'xtick.labelsize': eyr_tick_size, 'ytick.labelsize': eyr_tick_size, 'axes.unicode_minus': False}):
                                fig3, ax3 = plt.subplots(figsize=(fig_width / 2.54, fig_height / 2.54), facecolor='white')
                                ax3.grid(False)
                                for spine in ['top', 'bottom', 'left', 'right']:
                                    ax3.spines[spine].set_linewidth(1.0); ax3.spines[spine].set_color('black')
                                ax3.tick_params(axis='both', which='major', width=1.0, length=4, direction='in', top=eyr_mirror, right=eyr_mirror)
                                ax3.tick_params(axis='both', which='minor', width=0.8, length=2.5, direction='in', top=eyr_mirror, right=eyr_mirror)
                                ax3.xaxis.set_minor_locator(ticker.AutoMinorLocator())
                                ax3.yaxis.set_minor_locator(ticker.AutoMinorLocator())

                                x_data = fit_res_pub['Plot']['x']
                                y_data = fit_res_pub['Plot']['y']
                                ax3.scatter(x_data * 1000, y_data, s=eyr_marker_size**2, alpha=0.8, edgecolors='black', linewidth=0.8, color='steelblue', zorder=3)
                                x_range = np.linspace(x_data.min() * 0.95, x_data.max() * 1.05, 100)
                                y_fit = fit_res_pub['Params']['slope'] * x_range + fit_res_pub['Params']['intercept']
                                label_fit = r"$\Delta H^\ddagger = %.1f\ \mathrm{kJ\ mol}^{-1}$" % fit_res_pub['dH']
                                label_fit += "\n" + r"$\Delta S^\ddagger = %.1f\ \mathrm{J\ mol}^{-1}\mathrm{K}^{-1}$" % fit_res_pub['dS']
                                ax3.plot(x_range * 1000, y_fit, '--', color='red', linewidth=eyr_line_width, label=label_fit, zorder=2)

                                ax3.set_xlabel(r"$1000/T\ (\mathrm{K}^{-1})$", fontdict={'family': eyr_font_family, 'size': eyr_label_size, 'weight': eyr_label_weight, 'style': eyr_label_style})
                                ax3.set_ylabel(r"$\ln(\tau \cdot T)$", fontdict={'family': eyr_font_family, 'size': eyr_label_size, 'weight': eyr_label_weight, 'style': eyr_label_style})
                                if eyr_custom_lims:
                                    ax3.set_xlim(eyr_xmin, eyr_xmax)
                                    ax3.set_ylim(eyr_ymin, eyr_ymax)

                                apply_legend(ax3, eyr_leg_pos, eyr_leg_box, fontsize=eyr_leg_font_size, ncol=eyr_leg_ncol)
                                if panel_l_3:
                                    ax3.text(pl_x_3, pl_y_3, f"({panel_l_3})", transform=ax3.transAxes, fontfamily=panel_font_family, fontsize=panel_font_size, fontweight=panel_font_weight, fontstyle=panel_font_style, va='bottom', ha='right')

                                plt.tight_layout()
                                st.pyplot(fig3, dpi=300)
                                save_and_download(fig3, "Eyring", pub_colorspace, "f3")
                                plt.close(fig3)

                # ================= FIGURE 4: VAN T HOFF =================
                if 'show_fig4' in locals() and show_fig4 and not kinetics_df.empty:
                    st.markdown("---")
                    st.subheader(f"🌡️ Figure 4: Van 't Hoff Plot")
                    active_k = kinetics_df[kinetics_df['Include']==True]
                    if not active_k.empty and len(active_k) >= 2:
                        k_engine_pub = KineticsEngine()
                        temps_list = active_k['Temp'].tolist()
                        g0_map = {r['Temp']: r['Raw']['G0'] for r in active_res}
                        active_g0s = [g0_map.get(t, 1.0) for t in temps_list]
                        fit_res_pub = k_engine_pub.fit_van_t_hoff(temps_list, active_g0s)
                        if fit_res_pub:
                            c1, c2, c3 = st.columns(3)
                            c1.metric("ΔH_diss", f"{fit_res_pub['dH_diss']:.1f} kJ/mol")
                            c2.metric("ΔS_diss", f"{fit_res_pub['dS_diss']:.1f} J/mol·K")
                            c3.metric("R²", f"{fit_res_pub.get('R2',0):.4f}")

                            with plt.rc_context({'font.family': vh_tick_font if vh_tick_font != 'Same as Label' else vh_font_family, 'xtick.labelsize': vh_tick_size, 'ytick.labelsize': vh_tick_size, 'axes.unicode_minus': False}):
                                fig4, ax4 = plt.subplots(figsize=(fig_width / 2.54, fig_height / 2.54), facecolor='white')
                                ax4.grid(False)
                                for spine in ['top', 'bottom', 'left', 'right']:
                                    ax4.spines[spine].set_linewidth(1.0); ax4.spines[spine].set_color('black')
                                ax4.tick_params(axis='both', which='major', width=1.0, length=4, direction='in', top=vh_mirror, right=vh_mirror)
                                ax4.tick_params(axis='both', which='minor', width=0.8, length=2.5, direction='in', top=vh_mirror, right=vh_mirror)
                                ax4.xaxis.set_minor_locator(ticker.AutoMinorLocator())
                                if vh_y_scale != "Log": ax4.yaxis.set_minor_locator(ticker.AutoMinorLocator())
                                else:
                                    ax4.yaxis.set_major_locator(ticker.LogLocator(base=10.0))
                                    ax4.yaxis.set_minor_locator(ticker.LogLocator(base=10.0, subs=(2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0)))
                                    ax4.set_yscale('log')

                                x_data = fit_res_pub['Plot']['x']
                                y_data = fit_res_pub['Plot']['y']
                                ax4.scatter(x_data, y_data, s=vh_marker_size**2, alpha=0.8, edgecolors='black', linewidth=0.8, color='steelblue', zorder=3)
                                x_range = np.linspace(x_data.min() * 0.95, x_data.max() * 1.05, 100)
                                T_range = 1000.0 / x_range
                                exponent = -(fit_res_pub['dH_diss'] * 1000.0) / (8.314462 * T_range) + fit_res_pub['dS_diss'] / 8.314462
                                y_fit = fit_res_pub['G0_max'] / (1.0 + np.exp(np.clip(exponent, -50.0, 50.0)))
                                label_fit = r"$\Delta H_{diss} = %.1f\ \mathrm{kJ\ mol}^{-1}$" % fit_res_pub['dH_diss']
                                ax4.plot(x_range, y_fit, '--', color='red', linewidth=vh_line_width, label=label_fit, zorder=2)

                                ax4.set_xlabel(r"$1000/T\ (\mathrm{K}^{-1})$", fontdict={'family': vh_font_family, 'size': vh_label_size, 'weight': vh_label_weight, 'style': vh_label_style})
                                ax4.set_ylabel(r"$G_0$ (MPa)", fontdict={'family': vh_font_family, 'size': vh_label_size, 'weight': vh_label_weight, 'style': vh_label_style})
                                if vh_custom_lims:
                                    ax4.set_xlim(vh_xmin, vh_xmax)
                                    ax4.set_ylim(vh_ymin, vh_ymax)

                                apply_legend(ax4, vh_leg_pos, vh_leg_box, fontsize=vh_leg_font_size, ncol=vh_leg_ncol)
                                if panel_l_4:
                                    ax4.text(pl_x_4, pl_y_4, f"({panel_l_4})", transform=ax4.transAxes, fontfamily=panel_font_family, fontsize=panel_font_size, fontweight=panel_font_weight, fontstyle=panel_font_style, va='bottom', ha='right')

                                plt.tight_layout()
                                st.pyplot(fig4, dpi=300)
                                save_and_download(fig4, "Van_t_Hoff", pub_colorspace, "f4")
                                plt.close(fig4)
