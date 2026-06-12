import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import io
from PIL import Image

def render_plotting_tab(tab_plotting):
    with tab_plotting:
        # Create subtabs under Plotting tab
        sub_bar, = st.tabs(["📊 Bar Chart Plotting"])
        
        with sub_bar:
            st.header("📊 Scientific Bar Chart Plotting")
            st.markdown("Design publication-ready, high-resolution bar charts with precise layout and scaling controls.")

            # Initialize Default Data in Session State
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

            # ── Layout: Controls on the Left (1/3) | Previews on the Right (2/3) ──
            col_ctrl, col_preview = st.columns([1, 2], gap="large")

            with col_ctrl:
                st.subheader("⚙️ Settings")

                # ── 1. Data Input ──
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
                            
                            # Standardize column names
                            std_cols = {}
                            for col in loaded_df.columns:
                                c_lower = col.lower().strip()
                                if "cat" in c_lower:
                                    std_cols[col] = "Category"
                                elif "val" in c_lower or "y" == c_lower:
                                    std_cols[col] = "Value"
                                elif "err" in c_lower or "sd" in c_lower or "std" in c_lower or "dev" in c_lower:
                                    std_cols[col] = "Standard Deviation"
                            
                            loaded_df = loaded_df.rename(columns=std_cols)
                            
                            # Keep only required columns and fill missing
                            required_cols = ["Category", "Value", "Standard Deviation"]
                            for col in required_cols:
                                if col not in loaded_df.columns:
                                    if col == "Standard Deviation":
                                        loaded_df[col] = 0.0
                                    elif col == "Category":
                                        loaded_df[col] = [f"Bar {i+1}" for i in range(len(loaded_df))]
                                    else:
                                        loaded_df[col] = 1.0
                            
                            st.session_state.plotting_df = loaded_df[required_cols].copy()
                            st.success("✅ File loaded successfully!")
                        except Exception as e:
                            st.error(f"Error loading file: {e}")

                    st.markdown("**2. Edit Data Directly**")
                    st.caption("Double-click cells to edit. Press Enter to confirm. You can also add or delete rows.")
                    
                    # Interactive editor
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
                    
                    # Update session state with edited df
                    st.session_state.plotting_df = edited_df

                # Ensure we have data to plot
                df_data = st.session_state.plotting_df.dropna(subset=["Category"])
                if df_data.empty:
                    st.warning("⚠️ No data available to plot. Please add rows in the Data Entry tab.")
                    return

                # Get unique categories for color assignments
                categories = df_data["Category"].tolist()
                
                # Update colors dict for new categories
                palette_cycle = ["#ffcc99", "#99cc99", "#c2a6d9", "#ffff99", "#636EFA", "#EF553B", "#00CC96", "#AB63FA"]
                for i, cat in enumerate(categories):
                    if cat not in st.session_state.plotting_colors:
                        st.session_state.plotting_colors[cat] = palette_cycle[i % len(palette_cycle)]

                # ── 2. Color Settings ──
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

                # ── 3. Bar Style Settings ──
                with st.expander("📐 Bar Styling", expanded=False):
                    bar_width = st.slider("Bar Width (relative)", 0.1, 1.0, 0.6, 0.05, key="bar_width")
                    bar_alpha = st.slider("Bar Opacity (Alpha)", 0.0, 1.0, 0.8, 0.05, key="bar_alpha")
                    bar_edge_color = st.color_picker("Bar Border Color", value="#000000", key="bar_edge_color")
                    bar_edge_width = st.slider("Bar Border Line Width", 0.0, 5.0, 1.0, 0.5, key="bar_edge_width")
                    st.markdown("---")
                    st.markdown("**Error Bars**")
                    err_capsize = st.slider("Error Cap Width (points)", 0, 20, 5, key="err_capsize")
                    err_thickness = st.slider("Error Line Thickness", 0.5, 5.0, 1.5, 0.5, key="err_thickness")
                    err_color = st.color_picker("Error Bar Color", value="#333333", key="err_color")

                # ── 4. Axes & Scale Settings ──
                with st.expander("📈 Axes & Scales", expanded=False):
                    y_axis_scale = st.selectbox("Y-Axis Scale", ["Linear", "Log"], index=0, key="y_axis_scale")
                    
                    st.markdown("**Axes Limits**")
                    custom_y_lims = st.checkbox("Manual Y-Axis Bounding", value=False, key="custom_y_lims")
                    
                    # Calculate safe bounds for Y axis
                    min_pos_val = df_data[df_data["Value"] > 0]["Value"].min() if not df_data[df_data["Value"] > 0].empty else 0.1
                    max_val = df_data["Value"].max()
                    # Add error factor
                    if "Standard Deviation" in df_data.columns:
                        max_val = (df_data["Value"] + df_data["Standard Deviation"]).max()
                    
                    if y_axis_scale == "Log":
                        auto_ymin = 10 ** np.floor(np.log10(min_pos_val)) if min_pos_val > 0 else 0.1
                        auto_ymax = 10 ** np.ceil(np.log10(max_val)) if max_val > 0 else 10.0
                    else:
                        auto_ymin = 0.0
                        auto_ymax = float(max_val * 1.1)

                    if custom_y_lims:
                        y_lim_cols = st.columns(2)
                        with y_lim_cols[0]:
                            ymin_input = st.number_input("Y Min", value=float(auto_ymin), format="%.4f", key="ymin_input")
                        with y_lim_cols[1]:
                            ymax_input = st.number_input("Y Max", value=float(auto_ymax), format="%.4f", key="ymax_input")
                    else:
                        ymin_input = auto_ymin
                        ymax_input = auto_ymax

                    st.markdown("---")
                    st.markdown("**Ticks Control**")
                    tick_direction = st.selectbox("Tick Mark Direction", ["in", "out", "inout"], index=0, key="tick_direction")
                    tick_mirror = st.checkbox("Mirror Ticks to Top/Right", value=True, key="tick_mirror")
                    tick_length = st.slider("Major Tick Length (pt)", 1.0, 15.0, 4.0, 0.5, key="tick_length")
                    tick_width = st.slider("Major Tick Thickness (pt)", 0.5, 5.0, 1.0, 0.1, key="tick_width")
                    
                    st.markdown("**Spine Frame Style**")
                    box_frame = st.selectbox("Border Frame Type", ["Full Box", "L-shape (Bottom/Left only)"], index=0, key="box_frame")

                    st.markdown("**Gridlines**")
                    grid_mode = st.selectbox("Gridlines", ["None", "Y-only", "X-only", "Both"], index=0, key="grid_mode")
                    if grid_mode != "None":
                        grid_color = st.color_picker("Gridline Color", value="#e0e0e0", key="grid_color")
                        grid_style = st.selectbox("Gridline Style", ["--", ":", "-"], index=0, key="grid_style")

                # ── 5. Value Annotations on Bars ──
                with st.expander("🏷️ Bar Value Annotations", expanded=False):
                    show_annotations = st.checkbox("Show Values on Top of Bars", value=True, key="show_annotations")
                    if show_annotations:
                        annot_precision = st.slider("Decimal Places", 0, 4, 2, key="annot_precision")
                        annot_font_size = st.number_input("Annotation Font Size", 4, 30, 10, key="annot_font_size")
                        annot_color = st.color_picker("Annotation Font Color", value="#000000", key="annot_color")
                        annot_offset = st.number_input(
                            "Offset factor (above bar/error)", 
                            value=1.02 if y_axis_scale == "Log" else 0.05,
                            step=0.01,
                            format="%.3f",
                            help="Multiplier (e.g. 1.02 for Log) or addition (e.g. 0.05 for Linear) to shift labels above bars."
                        )

                # ── 6. Typography ──
                with st.expander("🔤 Labels & Typography", expanded=False):
                    plot_title = st.text_input("Chart Title", "", key="plot_title")
                    x_label_text = st.text_input("X-Axis Label", "Category", key="x_label_text")
                    y_label_text = st.text_input("Y-Axis Label", "Value", key="y_label_text")
                    
                    st.markdown("---")
                    st.markdown("**Fonts Settings**")
                    font_family = st.selectbox("Font Family", ["Arial", "Times New Roman", "Helvetica", "Courier New", "DejaVu Sans", "serif", "sans-serif"], key="font_family")
                    
                    f_cols = st.columns(2)
                    with f_cols[0]:
                        lbl_size = st.number_input("Axis Label Font Size", 4, 30, 12, key="lbl_size")
                        lbl_weight = st.selectbox("Axis Label Weight", ["bold", "normal"], key="lbl_weight")
                    with f_cols[1]:
                        tick_lbl_size = st.number_input("Tick Label Font Size", 4, 30, 10, key="tick_lbl_size")
                        tick_lbl_weight = st.selectbox("Tick Label Weight", ["normal", "bold"], key="tick_lbl_weight")

                    st.markdown("**X-Axis Labels Rotation**")
                    x_lbl_rotation = st.selectbox("Rotate X Labels", [0, 30, 45, 90], index=0, key="x_lbl_rotation")

                # ── 7. Figure Size & Export Formats ──
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
                        fig_width_cm = st.number_input("Width (cm)", 1.0, 50.0, float(default_w), 0.1, disabled=disable_w_h, key="plot_w")
                    with sz_cols[1]:
                        fig_height_cm = st.number_input("Height (cm)", 1.0, 50.0, float(default_h), 0.1, disabled=disable_w_h, key="plot_h")
                    
                    panel_letter = st.text_input("Panel Letter (optional)", "", help="e.g. 'a', 'b', 'A'", key="plot_panel")
                    export_dpi = st.number_input("Export Resolution (DPI)", 72, 1200, 300, 50, key="plot_dpi")
                    colorspace_mode = st.selectbox("Color Space Mode", ["RGB", "CMYK (for Publication Print)"], key="plot_colorspace")
                    export_format = st.selectbox("Export Format", ["png", "pdf", "svg", "tiff", "jpg", "bmp"], key="plot_format")

            with col_preview:
                st.subheader("📝 Previews")
                
                # Tabs for previews
                t_plotly, t_matplotlib = st.tabs(["📊 Interactive Plot (Plotly)", "📝 Publication Figure Preview (Matplotlib)"])

                # Colors list aligned to categories
                bar_colors = [st.session_state.plotting_colors[cat] for cat in categories]
                
                # Check for Log scale negative values warning
                values = df_data["Value"].tolist()
                std_devs = df_data["Standard Deviation"].fillna(0.0).tolist()
                
                has_zero_or_negative = any(val <= 0 for val in values)
                if y_axis_scale == "Log" and has_zero_or_negative:
                    st.warning("⚠️ Warning: Y-Axis is set to Log scale, but your dataset contains zero or negative values. Zero and negative values cannot be displayed on log scales.")

                # ── Tab 1: Plotly Interactive Plot ──
                with t_plotly:
                    fig_pl = go.Figure()
                    
                    # Convert error bars to plotly structure
                    error_y_dict = dict(
                        type='data',
                        array=std_devs,
                        visible=True,
                        thickness=err_thickness,
                        width=err_capsize,
                        color=err_color
                    )
                    
                    fig_pl.add_trace(go.Bar(
                        x=categories,
                        y=values,
                        error_y=error_y_dict,
                        marker=dict(
                            color=bar_colors,
                            line=dict(color=bar_edge_color, width=bar_edge_width),
                            opacity=bar_alpha
                        ),
                        width=bar_width * 0.8,
                        name="Data"
                    ))
                    
                    y_axis_type = "log" if y_axis_scale == "Log" else "linear"
                    fig_pl.update_yaxes(
                        type=y_axis_type,
                        title=y_label_text,
                        range=[np.log10(ymin_input), np.log10(ymax_input)] if y_axis_scale == "Log" else [ymin_input, ymax_input],
                        exponentformat='power'
                    )
                    
                    fig_pl.update_xaxes(title=x_label_text, tickangle=x_lbl_rotation)
                    
                    fig_pl.update_layout(
                        title=plot_title if plot_title else None,
                        height=500,
                        margin=dict(l=40, r=20, t=40, b=40),
                        showlegend=False,
                        template="plotly_white"
                    )
                    
                    st.plotly_chart(fig_pl, width='stretch')

                # ── Tab 2: Matplotlib Publication Preview ──
                with t_matplotlib:
                    # Create Matplotlib Figure
                    fig_mpl, ax_mpl = plt.subplots(figsize=(fig_width_cm / 2.54, fig_height_cm / 2.54), facecolor='white')
                    ax_mpl.set_facecolor('white')
                    
                    # Grid settings
                    if grid_mode == "Both" or grid_mode == "Y-only":
                        ax_mpl.grid(True, axis='y', color=grid_color, linestyle=grid_style, zorder=0)
                    if grid_mode == "Both" or grid_mode == "X-only":
                        ax_mpl.grid(True, axis='x', color=grid_color, linestyle=grid_style, zorder=0)
                    if grid_mode == "None":
                        ax_mpl.grid(False)

                    # Bar plot execution
                    bars = ax_mpl.bar(
                        categories,
                        values,
                        yerr=std_devs,
                        width=bar_width,
                        color=bar_colors,
                        edgecolor=bar_edge_color,
                        linewidth=bar_edge_width,
                        alpha=bar_alpha,
                        capsize=err_capsize,
                        error_kw=dict(
                            elinewidth=err_thickness,
                            capthick=err_thickness,
                            ecolor=err_color
                        ),
                        zorder=3
                    )
                    
                    if y_axis_scale == "Log":
                        ax_mpl.set_yscale("log")
                    
                    ax_mpl.set_ylim(ymin_input, ymax_input)

                    # Spines border styling
                    if box_frame == "Full Box":
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

                    # Ticks parameters
                    ax_mpl.tick_params(
                        axis='both',
                        which='major',
                        direction=tick_direction,
                        length=tick_length,
                        width=tick_width,
                        color='black',
                        top=tick_mirror if box_frame == "Full Box" else False,
                        right=tick_mirror if box_frame == "Full Box" else False
                    )
                    
                    # Log minor ticks parameters
                    if y_axis_scale == "Log":
                        ax_mpl.tick_params(
                            axis='y',
                            which='minor',
                            direction=tick_direction,
                            length=tick_length * 0.6,
                            width=tick_width * 0.8,
                            color='black',
                            right=tick_mirror if box_frame == "Full Box" else False
                        )

                    # Apply fonts to labels and title
                    font_label = {
                        'family': font_family,
                        'size': lbl_size,
                        'weight': lbl_weight
                    }
                    
                    ax_mpl.set_xlabel(x_label_text, fontdict=font_label, labelpad=8)
                    ax_mpl.set_ylabel(y_label_text, fontdict=font_label, labelpad=8)
                    
                    if plot_title:
                        ax_mpl.set_title(plot_title, fontfamily=font_family, fontsize=lbl_size + 2, fontweight='bold', pad=10)

                    # Rotate X labels
                    plt.xticks(rotation=x_lbl_rotation)

                    # Tick font custom styles
                    for label in ax_mpl.get_xticklabels():
                        label.set_family(font_family)
                        label.set_size(tick_lbl_size)
                        label.set_weight(tick_lbl_weight)
                    for label in ax_mpl.get_yticklabels():
                        label.set_family(font_family)
                        label.set_size(tick_lbl_size)
                        label.set_weight(tick_lbl_weight)

                    # Value annotations on top of bars
                    if show_annotations:
                        fmt_str = f"%.{annot_precision}f"
                        for bar, val, err in zip(bars, values, std_devs):
                            # Error height offset
                            h_offset = err if not np.isnan(err) else 0
                            top_val = val + h_offset
                            
                            # Position calculation
                            if y_axis_scale == "Log":
                                # In log, offset is multiplicative
                                pos_y = top_val * annot_offset
                            else:
                                # In linear, offset is additive
                                pos_y = top_val + annot_offset

                            # Safe guard for very small values or log bounds
                            if pos_y > ymax_input:
                                pos_y = ymax_input * 0.95 if y_axis_scale == "Log" else ymax_input - (ymax_input * 0.05)

                            ax_mpl.text(
                                bar.get_x() + bar.get_width() / 2.0,
                                pos_y,
                                fmt_str % val,
                                ha='center',
                                va='bottom',
                                fontsize=annot_font_size,
                                color=annot_color,
                                fontfamily=font_family
                            )

                    # Panel Letter
                    if panel_letter:
                        ax_mpl.text(
                            -0.12, 1.02,
                            f"({panel_letter})",
                            transform=ax_mpl.transAxes,
                            fontfamily=font_family,
                            fontsize=lbl_size + 2,
                            fontweight='bold',
                            va='bottom',
                            ha='right'
                        )

                    # Preview render
                    plt.tight_layout()
                    st.pyplot(fig_mpl, dpi=150, bbox_inches='tight')

                # ── Export & Downloads Panel ──
                st.markdown("---")
                st.subheader("📥 Export Figure")
                
                # Check target file download setup
                btn_export = st.button("Generate Downloadable Files", type="primary", width='stretch', key="btn_export_figs")
                
                if btn_export:
                    # Rerender figure with export-level specifications
                    fig_exp, ax_exp = plt.subplots(figsize=(fig_width_cm / 2.54, fig_height_cm / 2.54), facecolor='white')
                    ax_exp.set_facecolor('white')
                    
                    if grid_mode == "Both" or grid_mode == "Y-only":
                        ax_exp.grid(True, axis='y', color=grid_color, linestyle=grid_style, zorder=0)
                    if grid_mode == "Both" or grid_mode == "X-only":
                        ax_exp.grid(True, axis='x', color=grid_color, linestyle=grid_style, zorder=0)

                    # Draw bars
                    exp_bars = ax_exp.bar(
                        categories,
                        values,
                        yerr=std_devs,
                        width=bar_width,
                        color=bar_colors,
                        edgecolor=bar_edge_color,
                        linewidth=bar_edge_width,
                        alpha=bar_alpha,
                        capsize=err_capsize,
                        error_kw=dict(
                            elinewidth=err_thickness,
                            capthick=err_thickness,
                            ecolor=err_color
                        ),
                        zorder=3
                    )
                    
                    if y_axis_scale == "Log":
                        ax_exp.set_yscale("log")
                    ax_exp.set_ylim(ymin_input, ymax_input)

                    # Frame styling
                    if box_frame == "Full Box":
                        for spine in ['top', 'bottom', 'left', 'right']:
                            ax_exp.spines[spine].set_visible(True)
                            ax_exp.spines[spine].set_linewidth(1.0)
                            ax_exp.spines[spine].set_color('black')
                    else:
                        ax_exp.spines['top'].set_visible(False)
                        ax_exp.spines['right'].set_visible(False)
                        ax_exp.spines['bottom'].set_visible(True)
                        ax_exp.spines['bottom'].set_linewidth(1.0)
                        ax_exp.spines['left'].set_visible(True)
                        ax_exp.spines['left'].set_linewidth(1.0)

                    ax_exp.tick_params(
                        axis='both',
                        which='major',
                        direction=tick_direction,
                        length=tick_length,
                        width=tick_width,
                        color='black',
                        top=tick_mirror if box_frame == "Full Box" else False,
                        right=tick_mirror if box_frame == "Full Box" else False
                    )
                    
                    if y_axis_scale == "Log":
                        ax_exp.tick_params(
                            axis='y',
                            which='minor',
                            direction=tick_direction,
                            length=tick_length * 0.6,
                            width=tick_width * 0.8,
                            color='black',
                            right=tick_mirror if box_frame == "Full Box" else False
                        )

                    ax_exp.set_xlabel(x_label_text, fontdict=font_label, labelpad=8)
                    ax_exp.set_ylabel(y_label_text, fontdict=font_label, labelpad=8)
                    if plot_title:
                        ax_exp.set_title(plot_title, fontfamily=font_family, fontsize=lbl_size + 2, fontweight='bold', pad=10)

                    plt.xticks(rotation=x_lbl_rotation)

                    # Custom fonts
                    for label in ax_exp.get_xticklabels():
                        label.set_family(font_family)
                        label.set_size(tick_lbl_size)
                        label.set_weight(tick_lbl_weight)
                    for label in ax_exp.get_yticklabels():
                        label.set_family(font_family)
                        label.set_size(tick_lbl_size)
                        label.set_weight(tick_lbl_weight)

                    # Annotation tags
                    if show_annotations:
                        fmt_str = f"%.{annot_precision}f"
                        for bar, val, err in zip(exp_bars, values, std_devs):
                            h_offset = err if not np.isnan(err) else 0
                            top_val = val + h_offset
                            
                            if y_axis_scale == "Log":
                                pos_y = top_val * annot_offset
                            else:
                                pos_y = top_val + annot_offset

                            if pos_y > ymax_input:
                                pos_y = ymax_input * 0.95 if y_axis_scale == "Log" else ymax_input - (ymax_input * 0.05)

                            ax_exp.text(
                                bar.get_x() + bar.get_width() / 2.0,
                                pos_y,
                                fmt_str % val,
                                ha='center',
                                va='bottom',
                                fontsize=annot_font_size,
                                color=annot_color,
                                fontfamily=font_family
                            )

                    # Panel tagging
                    if panel_letter:
                        ax_exp.text(
                            -0.12, 1.02,
                            f"({panel_letter})",
                            transform=ax_exp.transAxes,
                            fontfamily=font_family,
                            fontsize=lbl_size + 2,
                            fontweight='bold',
                            va='bottom',
                            ha='right'
                        )

                    plt.tight_layout()

                    # Save figure bytes based on colorspace & format
                    buf = io.BytesIO()
                    fmt_lower = export_format.lower()
                    
                    if colorspace_mode.startswith("CMYK"):
                        # CMYK PDF / TIFF / JPEG flow
                        # 1. Save as high-res PNG bytes
                        buf_png_tmp = io.BytesIO()
                        fig_exp.savefig(buf_png_tmp, format='png', dpi=export_dpi, bbox_inches='tight')
                        buf_png_tmp.seek(0)
                        
                        # 2. Convert to CMYK using Pillow
                        img_rgb = Image.open(buf_png_tmp)
                        img_cmyk = img_rgb.convert('CMYK')
                        
                        # 3. Save as target format in CMYK
                        if fmt_lower == "pdf":
                            img_cmyk.save(buf, format='PDF', dpi=(export_dpi, export_dpi))
                            mime_type = "application/pdf"
                        elif fmt_lower == "tiff":
                            img_cmyk.save(buf, format='TIFF', dpi=(export_dpi, export_dpi), compression='tiff_lzw')
                            mime_type = "image/tiff"
                        elif fmt_lower in ["jpg", "jpeg"]:
                            img_cmyk.save(buf, format='JPEG', dpi=(export_dpi, export_dpi), quality=95)
                            mime_type = "image/jpeg"
                        else:
                            # PNG/SVG don't support CMYK natively, fall back to RGB PNG
                            img_rgb.save(buf, format='PNG', dpi=(export_dpi, export_dpi))
                            fmt_lower = "png"
                            mime_type = "image/png"
                            st.info("ℹ️ Note: PNG does not support CMYK natively. Saved as RGB PNG.")
                    else:
                        # Standard RGB flow
                        if fmt_lower == "pdf":
                            fig_exp.savefig(buf, format='pdf', bbox_inches='tight')
                            mime_type = "application/pdf"
                        elif fmt_lower == "svg":
                            fig_exp.savefig(buf, format='svg', bbox_inches='tight')
                            mime_type = "image/svg+xml"
                        elif fmt_lower in ["png", "jpg", "jpeg", "bmp", "tiff"]:
                            fig_exp.savefig(buf, format=fmt_lower, dpi=export_dpi, bbox_inches='tight')
                            mime_type = f"image/{fmt_lower}"

                    buf.seek(0)
                    plt.close(fig_exp)
                    plt.close(fig_mpl)
                    
                    filename = f"bar_chart_plot.{fmt_lower}"
                    
                    # Download button
                    st.download_button(
                        label=f"⬇️ Download Figure ({export_format.upper()} - {colorspace_mode})",
                        data=buf,
                        file_name=filename,
                        mime=mime_type,
                        width='stretch'
                    )
                    st.success(f"🎉 Plot successfully generated! Click above to download `{filename}`.")
                else:
                    plt.close(fig_mpl)
