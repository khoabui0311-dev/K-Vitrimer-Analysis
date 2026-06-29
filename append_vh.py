vh_code = """
            with comp_tab_vh:
                st.subheader("\U0001f4c8 Van 't Hoff Comparison Plot")
                col_plot_vh, col_settings_vh = st.columns([3, 1])
                
                with col_settings_vh:
                    st.markdown("**Export Settings:**")
                    vh_comp_fmt = st.selectbox("Format", ["png", "jpeg", "bmp", "tiff", "pdf", "svg"], key="vh_comp_fmt")
                    vh_comp_dpi = st.number_input("DPI", 72, 1200, 300, 50, key="vh_comp_dpi")
                    
                    with st.expander("\U0001f4dd Legend Settings", expanded=False):
                        show_vh_comp_legend = st.checkbox("Show Legend", value=True, key="vh_comp_legend")
                        vh_comp_leg_pos = st.selectbox("Position", ["best", "upper right", "upper left", "lower left", "lower right", "right (outside)"], key="vh_comp_leg_pos")
                        vh_comp_leg_fontsize = st.slider("Font Size", 4, 20, 8, key="vh_comp_leg_fontsize")
                        vh_comp_leg_box = st.checkbox("Box Border", value=True, key="vh_comp_leg_box")
                    
                    with st.expander("\U0001f4d0 Figure Dimensions", expanded=True):
                        vh_comp_width = st.number_input("Width (cm)", 1.0, 40.0, 12.7, 0.1, key="vh_comp_w")
                        vh_comp_height = st.number_input("Height (cm)", 1.0, 40.0, 10.0, 0.1, key="vh_comp_h")
                    
                    with st.expander("\U0001f524 Axis Typography", expanded=False):
                        vh_comp_font_family = st.selectbox("Font Family", ["Arial", "Times New Roman", "Courier New", "DejaVu Sans"], key="vh_comp_font_family")
                        st.markdown("**Axis Label Font**")
                        vh_comp_lbl_sz = st.number_input("Label Size", 4, 30, 12, key="vh_comp_lbl_sz")
                        st.markdown("**Axis Number Font**")
                        vh_comp_tick_size = st.number_input("Number Size", 4, 30, 10, key="vh_comp_tick_sz")
                
                with col_plot_vh:
                    import matplotlib.pyplot as plt
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
                            
                            label_fit = f"{name}: \u0394H = {vh_fit['dH_diss']:.1f} kJ/mol"
                            ax_vh.plot(x_range, y_fit, '--', color=color, linewidth=1.5, label=label_fit, zorder=2)
                        
                        ax_vh.set_yscale('log')
                        ax_vh.set_xlabel(r"$1000/T\\ (\\mathrm{K}^{-1})$", fontdict={'family': vh_comp_font_family, 'size': vh_comp_lbl_sz})
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
                            st.download_button(f"\U0001f4e5 Download Van 't Hoff Figure ({vh_comp_fmt})", buf_vh, f"Van_t_Hoff_Comparison.{fmt_lower}", mime=f"image/{fmt_lower}" if fmt_lower != 'pdf' else 'application/pdf', key="dl_vh_plot")
"""

with open('can_relax/gui/tabs/tab_comparison.py', 'a', encoding='utf-8') as f:
    f.write(vh_code)

print("Van t Hoff code appended successfully.")
