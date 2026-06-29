import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import io
from PIL import Image

def _initialize_session_state():
    default_df = pd.DataFrame({
        "Category": ["100/0", "70/30", "50/50", "30/70"],
        "Value": [365.0, 19.38, 7.79, 1.35],
        "Standard Deviation": [15.0, 4.2, 1.1, 0.25]
    })
    
    if "plotting_df" not in st.session_state:
        st.session_state.plotting_df = default_df.copy()
    
    if "plotting_colors" not in st.session_state:
        st.session_state.plotting_colors = {
            "100/0": "#ffcc99",
            "70/30": "#99cc99",
            "50/50": "#c2a6d9",
            "30/70": "#ffff99"
        }

def _render_data_input():
    with st.expander("📁 Data Entry & Upload", expanded=True):
        st.markdown("**1. Upload Excel / CSV file (Optional)**")
        uploaded_plot_file = st.file_uploader(
            "Upload data sheet",
            type=["csv", "xlsx"],
            help="Must have Category, Value, and Standard Deviation (or Error) columns",
            key="plot_uploader"
        )
        
        if uploaded_plot_file:
            try:
                if uploaded_plot_file.name.endswith(".csv"):
                    loaded_df = pd.read_csv(uploaded_plot_file)
                else:
                    loaded_df = pd.read_excel(uploaded_plot_file)
                
                std_cols = {}
                for col in loaded_df.columns:
                    c_lower = col.lower().strip()
                    if "cat" in c_lower: std_cols[col] = "Category"
                    elif "val" in c_lower or "y" == c_lower: std_cols[col] = "Value"
                    elif "err" in c_lower or "sd" in c_lower or "std" in c_lower or "dev" in c_lower: std_cols[col] = "Standard Deviation"
                
                loaded_df = loaded_df.rename(columns=std_cols)
                
                required_cols = ["Category", "Value", "Standard Deviation"]
                for col in required_cols:
                    if col not in loaded_df.columns:
                        if col == "Standard Deviation": loaded_df[col] = 0.0
                        elif col == "Category": loaded_df[col] = [f"Bar {i+1}" for i in range(len(loaded_df))]
                        else: loaded_df[col] = 1.0
                
                st.session_state.plotting_df = loaded_df[required_cols].copy()
                st.success("✅ File loaded successfully!")
            except Exception as e:
                st.error(f"Error loading file: {e}")

        st.markdown("**2. Edit Data Directly**")
        st.caption("Double-click cells to edit. Press Enter to confirm. You can also add or delete rows.")
        
        edited_df = st.data_editor(
            st.session_state.plotting_df,
            num_rows="dynamic",
            column_config={
                "Category": st.column_config.TextColumn("Category", help="X-axis category labels"),
                "Value": st.column_config.NumberColumn("Value (Y-axis)", help="Bar height value", format="%.4f"),
                "Standard Deviation": st.column_config.NumberColumn("Std Dev (Error)", help="Standard deviation / error bar size", min_value=0.0, format="%.4f")
            },
            hide_index=True,
            key="plot_editor"
        )
        st.session_state.plotting_df = edited_df

def _render_color_settings(categories):
    palette_cycle = ["#ffcc99", "#99cc99", "#c2a6d9", "#ffff99", "#636EFA", "#EF553B", "#00CC96", "#AB63FA"]
    for i, cat in enumerate(categories):
        if cat not in st.session_state.plotting_colors:
            st.session_state.plotting_colors[cat] = palette_cycle[i % len(palette_cycle)]

    with st.expander("🎨 Bar Colors", expanded=False):
        st.markdown("**Assign individual color to each category:**")
        color_cols = st.columns(2)
        for i, cat in enumerate(categories):
            col_idx = i % 2
            with color_cols[col_idx]:
                st.session_state.plotting_colors[cat] = st.color_picker(
                    f"Color for: {cat}",
                    value=st.session_state.plotting_colors[cat],
                    key=f"color_{cat}_{i}"
                )

def _render_bar_styling():
    style = {}
    with st.expander("📐 Bar Styling", expanded=False):
        style['bar_width'] = st.slider("Bar Width (relative)", 0.1, 1.0, 0.6, 0.05, key="bar_width")
        style['bar_alpha'] = st.slider("Bar Opacity (Alpha)", 0.0, 1.0, 0.8, 0.05, key="bar_alpha")
        style['bar_edge_color'] = st.color_picker("Bar Border Color", value="#000000", key="bar_edge_color")
        style['bar_edge_width'] = st.slider("Bar Border Line Width", 0.0, 5.0, 1.0, 0.5, key="bar_edge_width")
        st.markdown("---")
        st.markdown("**Error Bars**")
        style['err_capsize'] = st.slider("Error Cap Width (points)", 0, 20, 5, key="err_capsize")
        style['err_thickness'] = st.slider("Error Line Thickness", 0.5, 5.0, 1.5, 0.5, key="err_thickness")
        style['err_color'] = st.color_picker("Error Bar Color", value="#333333", key="err_color")
    return style

def _render_axes_settings(df_data):
    axes = {}
    with st.expander("📈 Axes & Scales", expanded=False):
        axes['y_axis_scale'] = st.selectbox("Y-Axis Scale", ["Linear", "Log"], index=0, key="y_axis_scale")
        
        st.markdown("**Axes Limits**")
        custom_y_lims = st.checkbox("Manual Y-Axis Bounding", value=False, key="custom_y_lims")
        
        min_pos_val = df_data[df_data["Value"] > 0]["Value"].min() if not df_data[df_data["Value"] > 0].empty else 0.1
        max_val = df_data["Value"].max()
        if "Standard Deviation" in df_data.columns:
            max_val = (df_data["Value"] + df_data["Standard Deviation"]).max()
        
        if axes['y_axis_scale'] == "Log":
            auto_ymin = 10 ** np.floor(np.log10(min_pos_val)) if min_pos_val > 0 else 0.1
            auto_ymax = 10 ** np.ceil(np.log10(max_val)) if max_val > 0 else 10.0
        else:
            auto_ymin = 0.0
            auto_ymax = float(max_val * 1.1)

        if custom_y_lims:
            y_lim_cols = st.columns(2)
            with y_lim_cols[0]:
                axes['ymin_input'] = st.number_input("Y Min", value=float(auto_ymin), format="%.4f", key="ymin_input")
            with y_lim_cols[1]:
                axes['ymax_input'] = st.number_input("Y Max", value=float(auto_ymax), format="%.4f", key="ymax_input")
        else:
            axes['ymin_input'] = auto_ymin
            axes['ymax_input'] = auto_ymax

        st.markdown("---")
        st.markdown("**Ticks Control**")
        axes['tick_direction'] = st.selectbox("Tick Mark Direction", ["in", "out", "inout"], index=0, key="tick_direction")
        axes['tick_mirror'] = st.checkbox("Mirror Ticks to Top/Right", value=True, key="tick_mirror")
        axes['tick_length'] = st.slider("Major Tick Length (pt)", 1.0, 15.0, 4.0, 0.5, key="tick_length")
        axes['tick_width'] = st.slider("Major Tick Thickness (pt)", 0.5, 5.0, 1.0, 0.1, key="tick_width")
        
        st.markdown("**Spine Frame Style**")
        axes['box_frame'] = st.selectbox("Border Frame Type", ["Full Box", "L-shape (Bottom/Left only)"], index=0, key="box_frame")

        st.markdown("**Gridlines**")
        axes['grid_mode'] = st.selectbox("Gridlines", ["None", "Y-only", "X-only", "Both"], index=0, key="grid_mode")
        if axes['grid_mode'] != "None":
            axes['grid_color'] = st.color_picker("Gridline Color", value="#e0e0e0", key="grid_color")
            axes['grid_style'] = st.selectbox("Gridline Style", ["--", ":", "-"], index=0, key="grid_style")
        else:
            axes['grid_color'] = "#e0e0e0"
            axes['grid_style'] = "--"
    return axes

def _render_annotations_settings(y_axis_scale):
    annots = {}
    with st.expander("🏷️ Bar Value Annotations", expanded=False):
        annots['show'] = st.checkbox("Show Values on Top of Bars", value=True, key="show_annotations")
        if annots['show']:
            annots['precision'] = st.slider("Decimal Places", 0, 4, 2, key="annot_precision")
            annots['font_size'] = st.number_input("Annotation Font Size", 4, 30, 10, key="annot_font_size")
            annots['color'] = st.color_picker("Annotation Font Color", value="#000000", key="annot_color")
            annots['offset'] = st.number_input(
                "Offset factor (above bar/error)", 
                value=1.02 if y_axis_scale == "Log" else 0.05,
                step=0.01,
                format="%.3f",
                help="Multiplier (e.g. 1.02 for Log) or addition (e.g. 0.05 for Linear) to shift labels above bars."
            )
    return annots

def _render_typography_settings():
    typo = {}
    with st.expander("🔤 Labels & Typography", expanded=False):
        typo['plot_title'] = st.text_input("Chart Title", "", key="plot_title")
        typo['x_label_text'] = st.text_input("X-Axis Label", "Category", key="x_label_text")
        typo['y_label_text'] = st.text_input("Y-Axis Label", "Value", key="y_label_text")
        
        st.markdown("---")
        st.markdown("**Fonts Settings**")
        typo['font_family'] = st.selectbox("Font Family", ["Arial", "Times New Roman", "Helvetica", "Courier New", "DejaVu Sans", "serif", "sans-serif"], key="font_family")
        
        f_cols = st.columns(2)
        with f_cols[0]:
            typo['lbl_size'] = st.number_input("Axis Label Font Size", 4, 30, 12, key="lbl_size")
            typo['lbl_weight'] = st.selectbox("Axis Label Weight", ["normal", "bold"], key="lbl_weight")
        with f_cols[1]:
            typo['tick_lbl_size'] = st.number_input("Tick Label Font Size", 4, 30, 10, key="tick_lbl_size")
            typo['tick_lbl_weight'] = st.selectbox("Tick Label Weight", ["normal", "bold"], key="tick_lbl_weight")

        st.markdown("**X-Axis Labels Rotation**")
        typo['x_lbl_rotation'] = st.selectbox("Rotate X Labels", [0, 30, 45, 90], index=0, key="x_lbl_rotation")
    return typo

def _render_export_settings():
    exp = {}
    with st.expander("📐 Figure Dimensions & Export", expanded=True):
        comp_preset = st.selectbox("Journal Dimensions Preset", [
            "ACS/RSC Single-Column (8.5 x 7.5 cm)",
            "ACS/RSC Double-Column (170 x 140 mm)",
            "Custom"
        ], key="plot_preset")
        
        if comp_preset == "ACS/RSC Single-Column (85 x 75 mm)" or comp_preset.startswith("ACS/RSC Single-Column"):
            default_w, default_h, disable_w_h = 8.5, 7.5, True
        elif comp_preset.startswith("ACS/RSC Double-Column"):
            default_w, default_h, disable_w_h = 17.0, 14.0, True
        else:
            default_w, default_h, disable_w_h = 12.7, 10.0, False

        sz_cols = st.columns(2)
        with sz_cols[0]:
            exp['fig_width_cm'] = st.number_input("Width (cm)", 1.0, 50.0, float(default_w), 0.1, disabled=disable_w_h, key="plot_w")
        with sz_cols[1]:
            exp['fig_height_cm'] = st.number_input("Height (cm)", 1.0, 50.0, float(default_h), 0.1, disabled=disable_w_h, key="plot_h")
        
        exp['panel_letter'] = st.text_input("Panel Letter (optional)", "", help="e.g. 'a', 'b', 'A'", key="plot_panel")
        exp['export_dpi'] = st.number_input("Export Resolution (DPI)", 72, 1200, 300, 50, key="plot_dpi")
        exp['colorspace_mode'] = st.selectbox("Color Space Mode", ["RGB", "CMYK (for Publication Print)"], key="plot_colorspace")
        exp['export_format'] = st.selectbox("Export Format", ["png", "pdf", "svg", "tiff", "jpg", "bmp"], key="plot_format")
    return exp

def _plot_matplotlib(categories, values, std_devs, bar_colors, style, axes, annots, typo, exp):
    fig_mpl, ax_mpl = plt.subplots(figsize=(exp['fig_width_cm'] / 2.54, exp['fig_height_cm'] / 2.54), facecolor='white')
    ax_mpl.set_facecolor('white')
    
    if axes['grid_mode'] in ["Both", "Y-only"]:
        ax_mpl.grid(True, axis='y', color=axes['grid_color'], linestyle=axes['grid_style'], zorder=0)
    if axes['grid_mode'] in ["Both", "X-only"]:
        ax_mpl.grid(True, axis='x', color=axes['grid_color'], linestyle=axes['grid_style'], zorder=0)
    if axes['grid_mode'] == "None":
        ax_mpl.grid(False)

    bars = ax_mpl.bar(
        categories,
        values,
        yerr=std_devs,
        width=style['bar_width'],
        color=bar_colors,
        edgecolor=style['bar_edge_color'],
        linewidth=style['bar_edge_width'],
        alpha=style['bar_alpha'],
        capsize=style['err_capsize'],
        error_kw=dict(
            elinewidth=style['err_thickness'],
            capthick=style['err_thickness'],
            ecolor=style['err_color']
        ),
        zorder=3
    )
    
    if axes['y_axis_scale'] == "Log":
        ax_mpl.set_yscale("log")
    
    ax_mpl.set_ylim(axes['ymin_input'], axes['ymax_input'])

    if axes['box_frame'] == "Full Box":
        for spine in ['top', 'bottom', 'left', 'right']:
            ax_mpl.spines[spine].set_visible(True)
            ax_mpl.spines[spine].set_linewidth(1.0)
            ax_mpl.spines[spine].set_color('black')
    else:
        ax_mpl.spines['top'].set_visible(False)
        ax_mpl.spines['right'].set_visible(False)
        ax_mpl.spines['bottom'].set_visible(True)
        ax_mpl.spines['bottom'].set_linewidth(1.0)
        ax_mpl.spines['bottom'].set_color('black')
        ax_mpl.spines['left'].set_visible(True)
        ax_mpl.spines['left'].set_linewidth(1.0)
        ax_mpl.spines['left'].set_color('black')

    ax_mpl.tick_params(
        axis='both', which='major', direction=axes['tick_direction'],
        length=axes['tick_length'], width=axes['tick_width'], color='black',
        top=axes['tick_mirror'] if axes['box_frame'] == "Full Box" else False,
        right=axes['tick_mirror'] if axes['box_frame'] == "Full Box" else False
    )
    
    if axes['y_axis_scale'] == "Log":
        ax_mpl.tick_params(
            axis='y', which='minor', direction=axes['tick_direction'],
            length=axes['tick_length'] * 0.6, width=axes['tick_width'] * 0.8, color='black',
            right=axes['tick_mirror'] if axes['box_frame'] == "Full Box" else False
        )

    font_label = {'family': typo['font_family'], 'size': typo['lbl_size'], 'weight': typo['lbl_weight']}
    
    ax_mpl.set_xlabel(typo['x_label_text'], fontdict=font_label, labelpad=8)
    ax_mpl.set_ylabel(typo['y_label_text'], fontdict=font_label, labelpad=8)
    
    if typo['plot_title']:
        ax_mpl.set_title(typo['plot_title'], fontfamily=typo['font_family'], fontsize=typo['lbl_size'] + 2, fontweight='bold', pad=10)

    plt.xticks(rotation=typo['x_lbl_rotation'])

    for label in ax_mpl.get_xticklabels() + ax_mpl.get_yticklabels():
        label.set_family(typo['font_family'])
        label.set_size(typo['tick_lbl_size'])
        label.set_weight(typo['tick_lbl_weight'])

    if annots.get('show'):
        fmt_str = f"%.{annots['precision']}f"
        for bar, val, err in zip(bars, values, std_devs):
            h_offset = err if not np.isnan(err) else 0
            top_val = val + h_offset
            
            pos_y = top_val * annots['offset'] if axes['y_axis_scale'] == "Log" else top_val + annots['offset']
            if pos_y > axes['ymax_input']:
                pos_y = axes['ymax_input'] * 0.95 if axes['y_axis_scale'] == "Log" else axes['ymax_input'] - (axes['ymax_input'] * 0.05)

            ax_mpl.text(
                bar.get_x() + bar.get_width() / 2.0, pos_y, fmt_str % val,
                ha='center', va='bottom', fontsize=annots['font_size'],
                color=annots['color'], fontfamily=typo['font_family']
            )

    if exp['panel_letter']:
        ax_mpl.text(
            -0.12, 1.02, f"({exp['panel_letter']})", transform=ax_mpl.transAxes,
            fontfamily=typo['font_family'], fontsize=typo['lbl_size'] + 2,
            fontweight='bold', va='bottom', ha='right'
        )

    return fig_mpl

def render_plotting_tab(tab_plotting):
    with tab_plotting:
        sub_bar, = st.tabs(["📊 Bar Chart Plotting"])
        
        with sub_bar:
            st.header("📊 Scientific Bar Chart Plotting")
            st.markdown("Design publication-ready, high-resolution bar charts with precise layout and scaling controls.")

            _initialize_session_state()
            col_ctrl, col_preview = st.columns([1, 2], gap="large")

            with col_ctrl:
                st.subheader("⚙️ Settings")
                _render_data_input()
                
                df_data = st.session_state.plotting_df.dropna(subset=["Category"])
                if df_data.empty:
                    st.warning("⚠️ No data available to plot. Please add rows in the Data Entry tab.")
                    return

                categories = df_data["Category"].tolist()
                _render_color_settings(categories)
                
                style = _render_bar_styling()
                axes = _render_axes_settings(df_data)
                annots = _render_annotations_settings(axes['y_axis_scale'])
                typo = _render_typography_settings()
                exp = _render_export_settings()

            with col_preview:
                st.subheader("📝 Previews")
                t_plotly, t_matplotlib = st.tabs(["📊 Interactive Plot (Plotly)", "📝 Publication Figure Preview (Matplotlib)"])

                bar_colors = [st.session_state.plotting_colors[cat] for cat in categories]
                values = df_data["Value"].tolist()
                std_devs = df_data["Standard Deviation"].fillna(0.0).tolist()
                
                has_zero_or_negative = any(val <= 0 for val in values)
                if axes['y_axis_scale'] == "Log" and has_zero_or_negative:
                    st.warning("⚠️ Warning: Y-Axis is set to Log scale, but your dataset contains zero or negative values. Zero and negative values cannot be displayed on log scales.")

                with t_plotly:
                    fig_pl = go.Figure()
                    error_y_dict = dict(type='data', array=std_devs, visible=True, thickness=style['err_thickness'], width=style['err_capsize'], color=style['err_color'])
                    fig_pl.add_trace(go.Bar(
                        x=categories, y=values, error_y=error_y_dict,
                        marker=dict(color=bar_colors, line=dict(color=style['bar_edge_color'], width=style['bar_edge_width']), opacity=style['bar_alpha']),
                        width=style['bar_width'] * 0.8, name="Data"
                    ))
                    fig_pl.update_yaxes(type="log" if axes['y_axis_scale'] == "Log" else "linear", title=typo['y_label_text'], range=[np.log10(axes['ymin_input']), np.log10(axes['ymax_input'])] if axes['y_axis_scale'] == "Log" else [axes['ymin_input'], axes['ymax_input']], exponentformat='power')
                    fig_pl.update_xaxes(title=typo['x_label_text'], tickangle=typo['x_lbl_rotation'])
                    fig_pl.update_layout(title=typo['plot_title'] if typo['plot_title'] else None, height=500, margin=dict(l=40, r=20, t=40, b=40), showlegend=False, template="plotly_white")
                    st.plotly_chart(fig_pl, width='stretch')

                with t_matplotlib:
                    fig_mpl = _plot_matplotlib(categories, values, std_devs, bar_colors, style, axes, annots, typo, exp)
                    plt.tight_layout()
                    st.pyplot(fig_mpl, dpi=150, bbox_inches='tight')

                st.markdown("---")
                st.subheader("📥 Export Figure")
                btn_export = st.button("Generate Downloadable Files", type="primary", width='stretch', key="btn_export_figs")
                
                if btn_export:
                    fig_exp = _plot_matplotlib(categories, values, std_devs, bar_colors, style, axes, annots, typo, exp)
                    plt.tight_layout()
                    buf = io.BytesIO()
                    fmt_lower = exp['export_format'].lower()
                    
                    if exp['colorspace_mode'].startswith("CMYK"):
                        buf_png_tmp = io.BytesIO()
                        fig_exp.savefig(buf_png_tmp, format='png', dpi=exp['export_dpi'], bbox_inches='tight')
                        buf_png_tmp.seek(0)
                        img_cmyk = Image.open(buf_png_tmp).convert('CMYK')
                        if fmt_lower == "pdf":
                            img_cmyk.save(buf, format='PDF', dpi=(exp['export_dpi'], exp['export_dpi']))
                            mime_type = "application/pdf"
                        elif fmt_lower == "tiff":
                            img_cmyk.save(buf, format='TIFF', dpi=(exp['export_dpi'], exp['export_dpi']), compression='tiff_lzw')
                            mime_type = "image/tiff"
                        elif fmt_lower in ["jpg", "jpeg"]:
                            img_cmyk.save(buf, format='JPEG', dpi=(exp['export_dpi'], exp['export_dpi']), quality=95)
                            mime_type = "image/jpeg"
                        else:
                            Image.open(buf_png_tmp).save(buf, format='PNG', dpi=(exp['export_dpi'], exp['export_dpi']))
                            fmt_lower = "png"
                            mime_type = "image/png"
                            st.info("ℹ️ Note: PNG does not support CMYK natively. Saved as RGB PNG.")
                    else:
                        if fmt_lower == "pdf":
                            fig_exp.savefig(buf, format='pdf', bbox_inches='tight')
                            mime_type = "application/pdf"
                        elif fmt_lower == "svg":
                            fig_exp.savefig(buf, format='svg', bbox_inches='tight')
                            mime_type = "image/svg+xml"
                        else:
                            fig_exp.savefig(buf, format=fmt_lower, dpi=exp['export_dpi'], bbox_inches='tight')
                            mime_type = f"image/{fmt_lower}"

                    buf.seek(0)
                    plt.close(fig_exp)
                    plt.close(fig_mpl)
                    
                    filename = f"bar_chart_plot.{fmt_lower}"
                    st.download_button(label=f"⬇️ Download Figure ({exp['export_format'].upper()} - {exp['colorspace_mode']})", data=buf, file_name=filename, mime=mime_type, width='stretch')
                    st.success(f"🎉 Plot successfully generated! Click above to download `{filename}`.")
                else:
                    plt.close(fig_mpl)
