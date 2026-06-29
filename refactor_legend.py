import re
with open('can_relax/gui/tabs/tab_publication.py', 'r', encoding='utf-8') as f:
    code = f.read()

# 1. Update apply_legend to accept fontsize, ncol
code = code.replace(
    'def apply_legend(ax, pos, box):',
    'def apply_legend(ax, pos, box, fontsize=8, ncol=1):'
)
code = code.replace(
    'ax.legend(frameon=box, loc=l_pos, bbox_to_anchor=l_anchor)',
    'ax.legend(frameon=box, loc=l_pos, bbox_to_anchor=l_anchor, fontsize=fontsize, ncol=ncol, columnspacing=1.0, handletextpad=0.5)'
)

# 2. Update Legend UI for Fig 1 (Relaxation)
rel_leg_old = """                        show_rel_leg = st.checkbox("Show Legend", value=True, key="pub_relleg")
                        if show_rel_leg:
                            rel_leg_pos = st.selectbox("Position", ["Best (Auto)", "Upper Right", "Upper Left", "Lower Left", "Lower Right", "Right (Outside)"], key="pub_relpos")"""
rel_leg_new = """                        show_rel_leg = st.checkbox("Show Legend", value=True, key="pub_relleg")
                        if show_rel_leg:
                            rel_leg_pos = st.selectbox("Position", ["Best (Auto)", "Upper Right", "Upper Left", "Lower Left", "Lower Right", "Right (Outside)"], key="pub_relpos")
                            rnc1, rnc2 = st.columns(2)
                            with rnc1: rel_leg_ncol = st.number_input("Columns", 1, 10, 1, key="pub_relncol")
                            with rnc2: rel_leg_font_size = st.slider("Font Size", 4, 16, 8, key="pub_relfont")
                            rel_leg_box = st.checkbox("Box Border", value=False, key="pub_relbox")
                        else:
                            rel_leg_pos, rel_leg_font_size, rel_leg_box, rel_leg_ncol = "Best (Auto)", 8, False, 1"""
code = code.replace(rel_leg_old, rel_leg_new)

# Update apply_legend call for Fig 1
code = code.replace('apply_legend(ax1, rel_leg_pos, False)', 'apply_legend(ax1, rel_leg_pos, rel_leg_box, fontsize=rel_leg_font_size, ncol=rel_leg_ncol)')

# 3. Update Legend UI for Fig 2 (Tau Kinetics)
kin_leg_old = """                        show_kin_leg = st.checkbox("Show Legend ", value=True, key="pub_kinleg")
                        if show_kin_leg:
                            kin_leg_pos = st.selectbox("Position ", ["Best (Auto)", "Upper Right", "Upper Left", "Lower Left", "Lower Right", "Right (Outside)"], key="pub_kinpos")"""
kin_leg_new = """                        show_kin_leg = st.checkbox("Show Legend ", value=True, key="pub_kinleg")
                        if show_kin_leg:
                            kin_leg_pos = st.selectbox("Position ", ["Best (Auto)", "Upper Right", "Upper Left", "Lower Left", "Lower Right", "Right (Outside)"], key="pub_kinpos")
                            knc1, knc2 = st.columns(2)
                            with knc1: kin_leg_ncol = st.number_input("Columns ", 1, 10, 1, key="pub_kinncol")
                            with knc2: kin_leg_font_size = st.slider("Font Size ", 4, 16, 8, key="pub_kinfont")
                            kin_leg_box = st.checkbox("Box Border ", value=False, key="pub_kinbox")
                        else:
                            kin_leg_pos, kin_leg_font_size, kin_leg_box, kin_leg_ncol = "Best (Auto)", 8, False, 1"""
code = code.replace(kin_leg_old, kin_leg_new)

# Update apply_legend call for Fig 2
code = code.replace('apply_legend(ax2, kin_leg_pos, False)', 'apply_legend(ax2, kin_leg_pos, kin_leg_box, fontsize=kin_leg_font_size, ncol=kin_leg_ncol)')

# 4. Add UI controls to Eyring (Fig 3)
eyring_ui_old = """                # ==============================================================================
                # EYRING CONFIG
                # ==============================================================================
                with st.expander("⚛️ Fig 3: Eyring Kinetics", expanded=False):
                    show_fig3 = st.checkbox("Generate Fig 3 (Eyring)", value=False, key="sh_fig3")
                    if show_fig3:
                        f3_pan_c1, f3_pan_c2 = st.columns(2)
                        with f3_pan_c1: panel_l_3 = st.text_input("Panel Letter  ", "c", key="pl_3")
                        with f3_pan_c2:
                            pl_x_3 = st.number_input("X pos  ", -1.0, 2.0, -0.12, 0.01, key="plx_3")
                            pl_y_3 = st.number_input("Y pos  ", -1.0, 2.0, 1.02, 0.01, key="ply_3")"""

eyring_ui_new = eyring_ui_old + """
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
                            eyr_leg_pos, eyr_leg_font_size, eyr_leg_box, eyr_leg_ncol = "Best (Auto)", 8, False, 1"""
code = code.replace(eyring_ui_old, eyring_ui_new)

# Update apply_legend call for Fig 3
code = code.replace('apply_legend(ax3, "Best (Auto)", False)', 'apply_legend(ax3, eyr_leg_pos, eyr_leg_box, fontsize=eyr_leg_font_size, ncol=eyr_leg_ncol)')


# 5. Add UI controls to Van t Hoff (Fig 4)
vh_ui_old = """                # ==============================================================================
                # VAN T HOFF CONFIG
                # ==============================================================================
                with st.expander("🌡️ Fig 4: Van 't Hoff (Decrosslinking)", expanded=False):
                    show_fig4 = st.checkbox("Generate Fig 4 (Van 't Hoff)", value=False, key="sh_fig4")
                    if show_fig4:
                        f4_pan_c1, f4_pan_c2 = st.columns(2)
                        with f4_pan_c1: panel_l_4 = st.text_input("Panel Letter   ", "d", key="pl_4")
                        with f4_pan_c2:
                            pl_x_4 = st.number_input("X pos   ", -1.0, 2.0, -0.12, 0.01, key="plx_4")
                            pl_y_4 = st.number_input("Y pos   ", -1.0, 2.0, 1.02, 0.01, key="ply_4")"""

vh_ui_new = vh_ui_old + """
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
                            with vy1: vh_ymin = st.number_input("Y Min", value=0.0, format="%.4f", key="vh_ymin")
                            with vy2: vh_ymax = st.number_input("Y Max", value=1.0, format="%.4f", key="vh_ymax")
                        show_vh_leg = st.checkbox("Show Legend ", value=True, key="vh_leg")
                        if show_vh_leg:
                            vh_leg_pos = st.selectbox("Position ", ["Best (Auto)", "Upper Right", "Upper Left", "Lower Left", "Lower Right", "Right (Outside)"], key="vh_legpos")
                            vnc1, vnc2 = st.columns(2)
                            with vnc1: vh_leg_ncol = st.number_input("Columns ", 1, 10, 1, key="vh_legncol")
                            with vnc2: vh_leg_font_size = st.slider("Font Size ", 4, 16, 8, key="vh_legfont")
                            vh_leg_box = st.checkbox("Box Border ", value=False, key="vh_legbox")
                        else:
                            vh_leg_pos, vh_leg_font_size, vh_leg_box, vh_leg_ncol = "Best (Auto)", 8, False, 1"""
code = code.replace(vh_ui_old, vh_ui_new)

# Update apply_legend call for Fig 4
code = code.replace('apply_legend(ax4, "Best (Auto)", False)', 'apply_legend(ax4, vh_leg_pos, vh_leg_box, fontsize=vh_leg_font_size, ncol=vh_leg_ncol)')


# Finally, also inject styling variables properly into plotting routines for Fig 3 and Fig 4:
# Fig 3
fig3_rc_old = "{'font.family': rel_font_family, 'axes.unicode_minus': False}"
fig3_rc_new = "{'font.family': eyr_tick_font if eyr_tick_font != 'Same as Label' else eyr_font_family, 'xtick.labelsize': eyr_tick_size, 'ytick.labelsize': eyr_tick_size, 'axes.unicode_minus': False}"
code = code.replace(fig3_rc_old, fig3_rc_new)

fig3_plot_old = "ax3.scatter(x_data * 1000, y_data, s=16, alpha=0.8, edgecolors='black', linewidth=0.8, color='steelblue', zorder=3)"
fig3_plot_new = "ax3.scatter(x_data * 1000, y_data, s=eyr_marker_size**2, alpha=0.8, edgecolors='black', linewidth=0.8, color='steelblue', zorder=3)"
code = code.replace(fig3_plot_old, fig3_plot_new)

fig3_plot2_old = "ax3.plot(x_range * 1000, y_fit, '--', color='red', linewidth=1.5, label=label_fit, zorder=2)"
fig3_plot2_new = "ax3.plot(x_range * 1000, y_fit, '--', color='red', linewidth=eyr_line_width, label=label_fit, zorder=2)"
code = code.replace(fig3_plot2_old, fig3_plot2_new)

fig3_labels_old = r'''                                ax3.set_xlabel(r"$1000/T\ (\mathrm{K}^{-1})$", fontdict={'family': rel_font_family, 'size':12})
                                ax3.set_ylabel(r"$\ln(\tau \cdot T)$", fontdict={'family': rel_font_family, 'size':12})'''
fig3_labels_new = r'''                                ax3.set_xlabel(r"$1000/T\ (\mathrm{K}^{-1})$", fontdict={'family': eyr_font_family, 'size': eyr_label_size, 'weight': eyr_label_weight, 'style': eyr_label_style})
                                ax3.set_ylabel(r"$\ln(\tau \cdot T)$", fontdict={'family': eyr_font_family, 'size': eyr_label_size, 'weight': eyr_label_weight, 'style': eyr_label_style})
                                if eyr_custom_lims:
                                    ax3.set_xlim(eyr_xmin, eyr_xmax)
                                    ax3.set_ylim(eyr_ymin, eyr_ymax)'''
code = code.replace(fig3_labels_old, fig3_labels_new)

code = code.replace("ax3.tick_params(axis='both', which='major', width=1.0, length=4, direction='in')",
                    "ax3.tick_params(axis='both', which='major', width=1.0, length=4, direction='in', top=eyr_mirror, right=eyr_mirror)")
code = code.replace("ax3.tick_params(axis='both', which='minor', width=0.8, length=2.5, direction='in')",
                    "ax3.tick_params(axis='both', which='minor', width=0.8, length=2.5, direction='in', top=eyr_mirror, right=eyr_mirror)")


# Fig 4
fig4_rc_old = "{'font.family': rel_font_family, 'axes.unicode_minus': False}"
fig4_rc_new = "{'font.family': vh_tick_font if vh_tick_font != 'Same as Label' else vh_font_family, 'xtick.labelsize': vh_tick_size, 'ytick.labelsize': vh_tick_size, 'axes.unicode_minus': False}"
code = code.replace(fig4_rc_old, fig4_rc_new)

fig4_plot_old = "ax4.scatter(x_data * 1000, y_data, s=16, alpha=0.8, edgecolors='black', linewidth=0.8, color='steelblue', zorder=3)"
fig4_plot_new = "ax4.scatter(x_data * 1000, y_data, s=vh_marker_size**2, alpha=0.8, edgecolors='black', linewidth=0.8, color='steelblue', zorder=3)"
code = code.replace(fig4_plot_old, fig4_plot_new)

fig4_plot2_old = "ax4.plot(x_range * 1000, y_fit, '--', color='red', linewidth=1.5, label=label_fit, zorder=2)"
fig4_plot2_new = "ax4.plot(x_range * 1000, y_fit, '--', color='red', linewidth=vh_line_width, label=label_fit, zorder=2)"
code = code.replace(fig4_plot2_old, fig4_plot2_new)

fig4_labels_old = r'''                                ax4.set_xlabel(r"$1000/T\ (\mathrm{K}^{-1})$", fontdict={'family': rel_font_family, 'size':12})
                                ax4.set_ylabel(r"$G_0$ (MPa)", fontdict={'family': rel_font_family, 'size':12})'''
fig4_labels_new = r'''                                ax4.set_xlabel(r"$1000/T\ (\mathrm{K}^{-1})$", fontdict={'family': vh_font_family, 'size': vh_label_size, 'weight': vh_label_weight, 'style': vh_label_style})
                                ax4.set_ylabel(r"$G_0$ (MPa)", fontdict={'family': vh_font_family, 'size': vh_label_size, 'weight': vh_label_weight, 'style': vh_label_style})
                                if vh_custom_lims:
                                    ax4.set_xlim(vh_xmin, vh_xmax)
                                    ax4.set_ylim(vh_ymin, vh_ymax)'''
code = code.replace(fig4_labels_old, fig4_labels_new)

code = code.replace("ax4.tick_params(axis='both', which='major', width=1.0, length=4, direction='in')",
                    "ax4.tick_params(axis='both', which='major', width=1.0, length=4, direction='in', top=vh_mirror, right=vh_mirror)")
code = code.replace("ax4.tick_params(axis='both', which='minor', width=0.8, length=2.5, direction='in')",
                    "ax4.tick_params(axis='both', which='minor', width=0.8, length=2.5, direction='in', top=vh_mirror, right=vh_mirror)")


with open('can_relax/gui/tabs/tab_publication.py', 'w', encoding='utf-8') as f:
    f.write(code)
