"""
tab_virtual_lab.py
------------------
Renders the Virtual Lab tab (🧪) in the K-Vitrimer-Analysis app.

Extracted from app.py to keep app.py as a thin orchestration layer.
All dependencies are passed in as arguments to keep this module stateless.
"""
import io
import numpy as np
import streamlit as st
import plotly.graph_objects as go
import matplotlib.pyplot as plt

from can_relax.core.kinetics import KineticsEngine


def render(sim, PLOTLY_STYLE: dict):
    """
    Render the Virtual Lab tab.

    Parameters
    ----------
    sim : MaterialSimulator
        Shared simulator instance.
    PLOTLY_STYLE : dict
        Shared Plotly layout dict for visual consistency.
    """
    st.subheader("🧪 Virtual Lab")
    col_ctrl, col_dash = st.columns([0.3, 0.7])

    with col_ctrl:
        with st.container(border=True):
            mode = st.radio(
                "Mode",
                ["⚗️ Chemist", "📐 Engineering", "🎯 Target"],
                label_visibility="collapsed"
            )
            st.markdown("---")
            disable_G = mode.startswith("📐")
            G_modulus = st.number_input("Modulus G (MPa)", 0.01, 2000.0, 1.0, 0.1, disabled=disable_G)
            log_tau0 = st.slider("log(tau0)", -18, -3, -12)
            tau0 = 10 ** log_tau0
            disable_Ea = mode.startswith("🎯")
            Ea_sim = st.number_input("Ea (kJ/mol)", 10.0, 300.0, 90.0, disabled=disable_Ea)
            disable_Tv = mode.startswith("⚗️")
            Tv_sim = st.number_input("Tv (°C)", -100.0, 400.0, 120.0, disabled=disable_Tv)
            st.markdown("---")
            sim_model = st.selectbox("Model", ["Single_KWW", "Maxwell", "Dual_KWW"])
            beta_sim = st.slider("Beta", 0.2, 1.0, 0.8)
            Tg_sim = st.number_input("Tg (°C)", value=50.0)

            frac_val = 0.5
            factor_val = 50.0
            Ea2_sim = Ea_sim
            beta2_sim = beta_sim
            if sim_model == "Dual_KWW":
                Ea2_sim = st.number_input("Ea₂ (kJ/mol)", value=Ea_sim)
                frac_val = st.slider("Fast-mode fraction", 0.1, 0.9, 0.5)
                factor_val = st.number_input("τ₂/τ₁ separation factor", value=50.0)
            st.markdown("---")
            temp_input = st.text_input("Temperatures (°C)", "130, 140, 150, 160, 170")

    with col_dash:
        c_res1, c_res2 = st.columns([1, 1])
        R_GAS = 8.314462
        with c_res1:
            if mode.startswith("⚗️"):
                try:
                    term = np.log(1e6 / (G_modulus * tau0))
                    Tv_res = ((Ea_sim * 1000.0) / (R_GAS * term)) - 273.15 if term > 0 else 999
                except Exception:
                    Tv_res = 999
                st.metric("Calculated Tv", f"{Tv_res:.1f} °C")
                if Tv_res < 900:
                    Tv_sim = Tv_res
            elif mode.startswith("📐"):
                try:
                    G_res = 1e6 / (tau0 * np.exp((Ea_sim * 1000.0) / (R_GAS * (Tv_sim + 273.15))))
                except Exception:
                    G_res = 0.0
                st.metric("Required G", f"{G_res:.2f} MPa")
                if G_res > 0:
                    G_modulus = G_res
            elif mode.startswith("🎯"):
                try:
                    Ea_res = (R_GAS * (Tv_sim + 273.15) * np.log(1e6 / (G_modulus * tau0))) / 1000.0
                except Exception:
                    Ea_res = 0.0
                st.metric("Required Ea", f"{Ea_res:.1f} kJ/mol")
                if Ea_res > 0:
                    Ea_sim = Ea_res

        try:
            exp_temps = sorted([float(x.strip()) for x in temp_input.split(',') if x.strip()])
        except Exception:
            exp_temps = []

        if exp_temps:
            params = {
                'Ea': Ea_sim, 'Tv': Tv_sim, 'Tg': Tg_sim,
                'G_plateau': G_modulus, 'beta': beta_sim,
                'fraction_fast': frac_val, 'tau_factor': factor_val,
                'Ea_2': Ea2_sim, 'beta_2': beta2_sim
            }
            sim_results = []
            fitted_taus = []
            valid_temps = []

            for T in exp_temps:
                try:
                    t, g_true, _ = sim.simulate_curve(T, sim_model, params)
                    sim_results.append((T, t, g_true))
                    if T > Tg_sim:
                        try:
                            target = 0.36788 * g_true[0]
                            t_fit = np.interp(target, g_true[::-1], t[::-1])
                            if 1e-5 < t_fit < 1e12:
                                fitted_taus.append(t_fit)
                                valid_temps.append(T)
                        except Exception:
                            pass
                except Exception as e:
                    st.error(f"Failed to simulate curve for {T}°C: {e}")

            c_p1, c_p2 = st.columns(2)
            with c_p1:
                fig = go.Figure()
                colors = PLOTLY_STYLE["colorway"]
                for i, (T, t, g) in enumerate(sim_results):
                    fig.add_trace(go.Scatter(
                        x=t, y=g, mode='lines',
                        name=f"{T}°C",
                        line=dict(color=colors[i % len(colors)])
                    ))
                fig.update_xaxes(type="log", title="Time (s)")
                fig.update_yaxes(title="G(t) (MPa)")
                fig.update_layout(
                    **PLOTLY_STYLE,
                    margin=dict(l=20, r=20, t=10, b=20),
                    height=300,
                    showlegend=True,
                    legend=dict(font=dict(size=9))
                )
                st.plotly_chart(fig, width="stretch")
                st.session_state.sim_fig_relax = fig
                st.session_state.sim_results_cache = sim_results

            with c_p2:
                if len(valid_temps) >= 3:
                    inv_T = 1000.0 / (np.array(valid_temps) + 273.15)
                    ln_tau = np.log(np.array(fitted_taus))
                    k_engine = KineticsEngine()
                    fit_res = k_engine.fit_arrhenius(valid_temps, fitted_taus)
                    if fit_res:
                        slope = fit_res['Params']['slope'] / 1000.0
                        intercept = fit_res['Params']['intercept']
                        G_Pa = G_modulus * 1e6
                        tau_Tv = 1e12 / G_Pa
                        ln_tau_target = np.log(tau_Tv)
                        Tv_rec = (1000.0 / ((ln_tau_target - intercept) / slope)) - 273.15 if slope != 0 else 0

                        fig_k = go.Figure()
                        fig_k.add_trace(go.Scatter(
                            x=inv_T, y=ln_tau, mode='markers',
                            marker=dict(size=8, color=PLOTLY_STYLE["colorway"][0]),
                            name="Data"
                        ))
                        xr = np.linspace(min(inv_T) * 0.9, max(inv_T) * 1.1, 100)
                        fig_k.add_trace(go.Scatter(
                            x=xr, y=slope * xr + intercept, mode='lines',
                            line=dict(dash='dash', color=PLOTLY_STYLE["colorway"][1], width=2),
                            name=f"Eₐ={fit_res['Ea']:.1f} kJ/mol"
                        ))
                        fig_k.add_trace(go.Scatter(
                            x=[(1000.0 / (Tv_rec + 273.15))], y=[ln_tau_target], mode='markers',
                            marker=dict(size=14, color='gold', symbol='star', line=dict(color='black', width=1)),
                            name=f"Tᵥ={Tv_rec:.1f}°C"
                        ))
                        fig_k.update_layout(
                            **PLOTLY_STYLE,
                            xaxis_title="1000/T (K⁻¹)",
                            yaxis_title="ln(τ)",
                            margin=dict(l=20, r=20, t=10, b=20),
                            height=300,
                            legend=dict(font=dict(size=9))
                        )
                        st.plotly_chart(fig_k, width="stretch")
                        st.caption(f"✅ Recovered Tv: {Tv_rec:.1f} °C")
                        st.session_state.sim_fig_kinetics = fig_k
                        st.session_state.sim_kinetics_cache = {
                            'inv_T': inv_T, 'ln_tau': ln_tau,
                            'slope': slope, 'intercept': intercept,
                            'fit_res': fit_res,
                            'valid_temps': valid_temps, 'fitted_taus': fitted_taus,
                            'G_modulus': G_modulus
                        }

            # ── Export Settings ─────────────────────────────────────────
            st.markdown("---")
            st.subheader("📥 Export Simulation Plots")
            exp_c1, exp_c2, *_ = st.columns(4)
            with exp_c1:
                sim_fig_fmt = st.selectbox("Format", ["png", "bmp", "tiff", "pdf", "svg"], key="sim_fmt")
                sim_fig_dpi = st.number_input("DPI", 72, 1200, 300, 50, key="sim_dpi")
            with exp_c2:
                sim_fig_width = st.number_input("Width (in)", 2.0, 10.0, 3.5, 0.1, key="sim_width")
                sim_fig_height = st.number_input("Height (in)", 2.0, 10.0, 3.0, 0.1, key="sim_height")

            exp_col1, exp_col2 = st.columns(2)
            with exp_col1:
                if st.button("📥 Export Relaxation Curves", key="export_sim_relax"):
                    _export_relax(sim_results, sim_fig_fmt, sim_fig_dpi, sim_fig_width, sim_fig_height)

            with exp_col2:
                if st.button("📥 Export Arrhenius Plot", key="export_sim_arr"):
                    _export_arrhenius(valid_temps, fitted_taus, G_modulus,
                                      sim_fig_fmt, sim_fig_dpi, sim_fig_width, sim_fig_height)


def _export_relax(sim_results, fmt, dpi, width, height):
    if not sim_results:
        st.warning("Generate simulation first")
        return
    fig_mpl, ax_mpl = plt.subplots(figsize=(width, height))
    colors = plt.cm.tab10(np.linspace(0, 1, len(sim_results)))
    for i, (T, t, g) in enumerate(sim_results):
        g_norm = g / g[0] if g[0] > 0 else g
        ax_mpl.plot(t, g_norm, linewidth=2, label=f"{T}°C", color=colors[i])
    ax_mpl.set_xscale('log')
    ax_mpl.set_xlabel("Time (s)", fontsize=12)
    ax_mpl.set_ylabel("G(t) / G₀", fontsize=12)
    ax_mpl.grid(True, alpha=0.3, linestyle='--')
    ax_mpl.legend(frameon=True, fontsize=8)
    ax_mpl.tick_params(labelsize=10)
    plt.tight_layout()
    buf = io.BytesIO()
    if fmt.lower() in ['bmp', 'tiff']:
        buf_tmp = io.BytesIO()
        fig_mpl.savefig(buf_tmp, format='png', dpi=dpi, bbox_inches='tight')
        buf_tmp.seek(0)
        from PIL import Image
        Image.open(buf_tmp).save(buf, format=fmt.upper())
    else:
        fig_mpl.savefig(buf, format=fmt, dpi=dpi, bbox_inches='tight')
    buf.seek(0)
    st.download_button("⬇️ Download Relaxation", buf, f"Simulation_Relaxation.{fmt}", key="dl_sim_relax")
    plt.close(fig_mpl)


def _export_arrhenius(valid_temps, fitted_taus, G_modulus, fmt, dpi, width, height):
    if len(valid_temps) < 3:
        st.warning("Need at least 3 temperatures for Arrhenius export")
        return
    inv_T = 1000.0 / (np.array(valid_temps) + 273.15)
    ln_tau = np.log(np.array(fitted_taus))
    k_engine = KineticsEngine()
    fit_res = k_engine.fit_arrhenius(valid_temps, fitted_taus)
    if not fit_res:
        st.error("Arrhenius fit failed.")
        return
    slope = fit_res['Params']['slope'] / 1000.0
    intercept = fit_res['Params']['intercept']
    r_sq = fit_res['R2']
    Ea_rec = fit_res['Ea']
    G_Pa = G_modulus * 1e6
    tau_Tv = 1e12 / G_Pa
    ln_tau_target = np.log(tau_Tv)
    Tv_rec = (1000.0 / ((ln_tau_target - intercept) / slope)) - 273.15 if slope != 0 else 0

    fig_arr = plt.figure(figsize=(width, height))
    ax_arr = fig_arr.add_subplot(111)
    ax_arr.scatter(inv_T, ln_tau, s=80, alpha=0.8, edgecolors='black', linewidth=1.5, color='steelblue', zorder=3)
    x_range = np.linspace(min(inv_T) * 0.9, max(inv_T) * 1.1, 100)
    y_fit = slope * x_range + intercept
    ax_arr.plot(x_range, y_fit, '--', color='red', linewidth=2,
                label=f'Eₐ = {Ea_rec:.1f} kJ/mol\nR² = {r_sq:.4f}', zorder=2)
    Tv_x = (ln_tau_target - intercept) / slope
    ax_arr.plot([Tv_x], [ln_tau_target], marker='*', markersize=18,
                color='gold', markeredgecolor='black', markeredgewidth=1.5,
                label=f'Tᵥ = {Tv_rec:.1f}°C', zorder=4)
    ax_arr.set_xlabel("1000/T (K⁻¹)", fontsize=12)
    ax_arr.set_ylabel("ln(τ)", fontsize=12)
    ax_arr.grid(True, alpha=0.3, linestyle='--')
    ax_arr.legend(frameon=True, fontsize=8)
    ax_arr.tick_params(labelsize=10)
    plt.tight_layout()
    buf = io.BytesIO()
    if fmt.lower() in ['bmp', 'tiff']:
        buf_tmp = io.BytesIO()
        fig_arr.savefig(buf_tmp, format='png', dpi=dpi, bbox_inches='tight')
        buf_tmp.seek(0)
        from PIL import Image
        Image.open(buf_tmp).save(buf, format=fmt.upper())
    else:
        fig_arr.savefig(buf, format=fmt, dpi=dpi, bbox_inches='tight')
    buf.seek(0)
    st.download_button("⬇️ Download Arrhenius", buf, f"Simulation_Arrhenius.{fmt}", key="dl_sim_arr")
    plt.close(fig_arr)
