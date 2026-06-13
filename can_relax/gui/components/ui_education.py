import streamlit as st
import numpy as np
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import pandas as pd
import io

@st.cache_data
def get_kinetics_comparison_plot():
    T_range = np.linspace(40 + 273.15, 200 + 273.15, 200)
    T_C = T_range - 273.15
    tau_arr = np.exp(-30.0 + 90000.0 / (8.314 * T_range))
    h = 6.626e-34
    kB = 1.381e-23
    tau_eyring = (h / (kB * T_range)) * np.exp(85000.0 / (8.314 * T_range) - (-20.0 / 8.314))
    tau_vft = np.exp(-16.0 + 2000.0 / (T_range - 240.0))
    tau_coupled = 1e-11 * np.exp(80000.0 / (8.314 * T_range)) + 1e-4 * np.exp(1000.0 / (T_range - 260.0))

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.semilogy(T_C, tau_arr, '-', linewidth=2.5, label=r'Arrhenius ($E_a = 90$ kJ/mol)', color='#EF553B')
    ax.semilogy(T_C, tau_eyring, '--', linewidth=2.5, label=r'Eyring ($\Delta H^{\ddagger} = 85$ kJ/mol)', color='#00CC96')
    ax.semilogy(T_C, tau_vft, ':', linewidth=2.5, label=r'VFT ($B = 2000$ K)', color='#636EFA')
    ax.semilogy(T_C, tau_coupled, '-.', linewidth=2.5, label=r'Coupled WLF-Arrhenius', color='#AB63FA')
    ax.axvline(x=50, color='gray', linestyle='--', alpha=0.6, label=r'Approximate $T_{g}$ (50 °C)')
    
    ax.set_xlabel('Temperature (°C)', fontsize=12, fontweight='normal')
    ax.set_ylabel(r'Relaxation Time $\tau$ (s)', fontsize=12, fontweight='normal')
    ax.set_title('Comparison of Temperature Kinetics Models', fontsize=13, fontweight='normal')
    ax.grid(True, alpha=0.3, which='both')
    ax.legend(fontsize=8, loc='upper right')
    ax.tick_params(labelsize=10)
    ax.set_ylim([1e-3, 1e6])
    
    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()

@st.cache_data
def get_models_comparison_plot():
    t = np.logspace(-4, 2, 200)
    G0 = 1.0
    tau_m = 10.0
    tau_kww = 15.0
    beta_kww = 0.85
    tau1_dual = 5.0
    beta1_dual = 0.9
    tau2_dual = 100.0
    beta2_dual = 0.7
    f_dual = 0.4

    g_maxwell = G0 * np.exp(-t/tau_m)
    g_kww = G0 * np.exp(-(t/tau_kww)**beta_kww)
    g_dual = G0 * (f_dual * np.exp(-(t/tau1_dual)**beta1_dual) + (1-f_dual) * np.exp(-(t/tau2_dual)**beta2_dual))

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.loglog(t, g_maxwell, 'o-', linewidth=2.5, markersize=4, alpha=0.8, label=r'Maxwell ($\tau = 10$ s)')
    ax.loglog(t, g_kww, 's-', linewidth=2.5, markersize=4, alpha=0.8, label=r'Single-KWW ($\tau = 15$ s, $\beta = 0.85$)')
    ax.loglog(t, g_dual, '^-', linewidth=2.5, markersize=4, alpha=0.8, label=r'Dual-KWW ($\tau_{1} = 5$ s, $\tau_{2} = 100$ s)')
    ax.set_xlabel('Time (s)', fontsize=12, fontweight='normal')
    ax.set_ylabel(r'G(t) / $G_{0}$', fontsize=12, fontweight='normal')
    ax.set_title('Comparison of Relaxation Models', fontsize=13, fontweight='normal')
    ax.grid(True, alpha=0.3, which='both')
    ax.legend(fontsize=8, loc='upper right')
    ax.tick_params(labelsize=10)
    
    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()

def render_education_tab(tab_education):
    with tab_education:
        st.header("📚 User Guide & Scientific Cheat Sheet")
        st.markdown("A quick-reference guide for selecting models and interpreting results in CAN-Relax.")

        edu_tabs = st.tabs([
            "📈 Relaxation Models",
            "🔥 Kinetics Analysis",
            "🔍 Tikhonov Spectrum",
            "🧪 Vitrimer Chemistry",
            "📚 References"
        ])

        # ====== TAB 1: RELAXATION MODELS ======
        with edu_tabs[0]:
            st.subheader("Which Model Should I Choose?")
            st.markdown("Use this guide to select the right phenomenological model for your time-domain stress relaxation data ($G(t)$).")
            
            # Decision Tree
            st.info("💡 **Quick Rule:** If the Maxwell R² > 0.95, stick with Maxwell. If you see a clear 'kink' or two distinct slopes on a log-log plot, you need Dual-KWW.")
            
            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown("#### 1️⃣ Maxwell")
                st.caption("Single relaxation time")
                st.markdown("- **Best for**: Ideal liquids, simple polymers far above $T_g$.")
                st.markdown("- **Visual Cue**: A perfectly straight line on a log-linear plot.")
                with st.expander("Show Math & Params"):
                    st.latex(r"G(t) = G_0 \exp\left(-\frac{t}{\tau}\right)")
                    st.markdown("**$\\tau$**: Time to reach 37% of initial stress.")
            
            with c2:
                st.markdown("#### 2️⃣ Single-KWW")
                st.caption("Stretched exponential")
                st.markdown("- **Best for**: Polydisperse networks, glassy polymers.")
                st.markdown("- **Visual Cue**: Gentle curvature on a log-linear plot.")
                with st.expander("Show Math & Params"):
                    st.latex(r"G(t) = G_0 \exp\left[-\left(\frac{t}{\tau}\right)^{\beta}\right]")
                    st.markdown("**$\\beta$**: Stretching exponent. $\\beta=1$ is Maxwell. $\\beta < 0.7$ means a very broad distribution.")
            
            with c3:
                st.markdown("#### 3️⃣ Dual-KWW")
                st.caption("Two distinct timescales")
                st.markdown("- **Best for**: Vitrimers (exchange + glassy), phase-separated blends.")
                st.markdown("- **Visual Cue**: Two distinct drops or a 'step' in the curve.")
                with st.expander("Show Math & Params"):
                    st.latex(r"G(t) \propto f \exp\left[-\left(\frac{t}{\tau_1}\right)^{\beta_1}\right] + (1-f) \exp\left[-\left(\frac{t}{\tau_2}\right)^{\beta_2}\right]")
                    st.markdown("**$f$**: Fraction of the fast mode.")
            
            st.markdown("---")
            st.markdown("#### 🎯 Visual Comparison")
            st.image(get_models_comparison_plot(), width=700)

        # ====== TAB 2: KINETICS ======
        with edu_tabs[1]:
            st.subheader("Interpreting Temperature Kinetics")
            st.markdown("Once you extract $\\tau^*$ from your relaxation curves across different temperatures, how do you model the kinetics?")

            # Model Cards
            st.markdown("#### The Big Three Models")
            k1, k2, k3 = st.columns(3)
            with k1:
                st.markdown("##### 🔴 Arrhenius")
                st.markdown("**Regime:** High Temp ($T \gg T_g$)")
                st.markdown("**Insight:** Yields Activation Energy ($E_a$).")
                with st.expander("Show Equation"):
                    st.latex(r"\ln(\tau) = \ln(\tau_0) + \frac{E_a}{R T}")
            with k2:
                st.markdown("##### 🟢 Eyring (TST)")
                st.markdown("**Regime:** High Temp ($T \gg T_g$)")
                st.markdown("**Insight:** Yields Enthalpy ($\Delta H^\ddagger$) and Entropy ($\Delta S^\ddagger$).")
                with st.expander("Show Equation"):
                    st.latex(r"\ln(\tau T) = \dots + \frac{\Delta H^{\ddagger}}{R T} - \frac{\Delta S^{\ddagger}}{R}")
            with k3:
                st.markdown("##### 🔵 VFT / Coupled")
                st.markdown("**Regime:** Near $T_g$")
                st.markdown("**Insight:** Captures cooperative glassy freezing.")
                with st.expander("Show Equation"):
                    st.latex(r"\ln(\tau) = A + \frac{B}{T - T_0}")
            
            st.markdown("---")
            st.markdown("#### 🧠 Cheat Sheet: Interpreting Eyring Entropy ($\Delta S^\ddagger$)")
            e1, e2 = st.columns(2)
            with e1:
                st.success("**Negative ($\Delta S^\ddagger < 0$) = Associative**")
                st.markdown("The transition state is highly constrained. Characteristic of transesterification or transamination where bonds form *before* breaking.")
            with e2:
                st.warning("**Positive ($\Delta S^\ddagger > 0$) = Dissociative**")
                st.markdown("The transition state is disordered. Characteristic of Diels-Alder or boronic esters where bonds break *before* forming.")

            st.markdown("---")
            st.markdown("#### 🎯 Visual Comparison")
            st.image(get_kinetics_comparison_plot(), width=700)

            st.markdown("---")
            st.markdown("#### ⚖️ Automated Selection (BIC)")
            st.info("The software automatically recommends the best kinetic model using the **Bayesian Information Criterion (BIC)**. This prevents overfitting by penalizing complex models (like the 5-parameter Coupled model) unless they provide a massively better fit than simpler ones.")

        # ====== TAB 3: TIKHONOV ======
        with edu_tabs[2]:
            st.subheader("The Tikhonov Spectrum & Diagnostics")
            
            st.markdown(r"""
            Instead of forcing data into a predefined equation, the **Continuous Relaxation Spectrum** $H(\tau)$ mathematically unfolds the $G(t)$ curve into a continuous distribution using Ridge Regression (Tikhonov Inversion).
            """)

            st.info("💡 **Note:** In CAN-Relax, Tikhonov is used strictly as a **parallel visual diagnostic tool**, not for extracting $\\tau^*$ for kinetics.")

            t1, t2 = st.columns(2)
            with t1:
                st.markdown("#### ⚠️ Incomplete Relaxation Warning")
                st.markdown("If your experiment was stopped too early, the dominant peak $\\tau_{dom}$ might lie outside your data window. The spectrum automatically calculates this peak and throws a warning if it approaches $t_{max}$, preventing you from interpreting truncated data as a full peak.")
                
            with t2:
                st.markdown("#### 📉 The $G_{eq}$ Subtraction")
                st.markdown("For inversion to work, the modulus must decay to zero. If your material has permanent cross-links, it plateaus at $G_{eq} > 0$. We automatically subtract the final 5% tail ($G_{eq}$) to prevent massive baseline artifacts at long times.")

            st.markdown("#### 🧭 The Workflow Architecture")
            st.markdown("""
            ```text
            [Raw Stress Relaxation G(t) in MPa]
                           │
                           ▼
           [Pre-processing: G_eq Subtraction]
                           │
            ┌──────────────┴──────────────┐
            ▼                             ▼
     [Parametric Fit]            [Tikhonov Inversion]
 (Maxwell, KWW, Dual-KWW)        (Continuous H(τ))
            │                             │
            ▼                             ▼
      [Extract τ*]              [Visual Diagnostics & Warnings]
            │                   (Peak counting, Truncation limits)
            ▼
    [Kinetics Model Fitting]
            ```
            """)

        # ====== TAB 4: CHEMISTRY ======
        with edu_tabs[3]:
            st.subheader("Vitrimer Chemistry Quick Reference")
            
            comparison_df = pd.DataFrame({
                'Property': ['Reversibility', 'Reprocessability', 'Stress Relaxation', 'Typical τ @ Tg+50', 'Suggested Model'],
                'Thermoset': ['❌ Irreversible', '❌ Cannot remold', '🔴 None (Plateaus)', '∞ (Frozen)', 'N/A'],
                'Vitrimer': ['✅ Exchange', '✅ Can remold', '🟡 Slow (Hours)', '100 - 10,000 s', 'Dual-KWW / Single-KWW'],
                'Thermoplastic': ['✅ Chain Flow', '✅ Can remold', '✅ Fast (Mins)', '1 - 100 s', 'Maxwell / Single-KWW']
            })
            st.dataframe(comparison_df, hide_index=True, use_container_width=True)

            c1, c2 = st.columns(2)
            with c1:
                st.markdown("#### 🔄 Associative (Vitrimers)")
                st.markdown("- **Mechanism:** Cross-link density remains constant during exchange.")
                st.markdown("- **Examples:** Epoxy-acid, Polyhydroxyurethanes.")
                st.markdown("- **Rheology:** Gradual viscosity drop (Arrhenius).")
            with c2:
                st.markdown("#### ✂️ Dissociative (CANs)")
                st.markdown("- **Mechanism:** Bonds break entirely before reforming.")
                st.markdown("- **Examples:** Diels-Alder, Dissociative urethanes.")
                st.markdown("- **Rheology:** Sudden viscosity drop. Use the **Van 't Hoff** model on $G_0$ to track decrosslinking.")

        # ====== TAB 5: REFERENCES ======
        with edu_tabs[4]:
            st.subheader("Literature & Citations")
            
            st.markdown("#### 📘 CAN Characterization Guidelines")
            st.markdown("1. **Berne, D., et al. (2025).** *How to Characterize Covalent Adaptable Networks: A User Guide.* ACS Polym. Au. [Detailed guidelines on Arrhenius/Eyring analysis]")
            st.markdown("2. **Wink, R., et al. (2026).** *A Practical User Guide to Stress Relaxation Spectra.* ACS Polym. Au. [Tikhonov regularization and L-curve corner detection]")
            
            st.markdown("#### 🧪 Vitrimer Fundamentals")
            st.markdown("3. **Montarnal, D., et al. (2011).** *Silica-like malleable materials from permanent organic polymers.* Science.")
            st.markdown("4. **Denissen, W., et al. (2016).** *Vitrimers: permanent organic networks with glass-like fluidity.* Chem. Sci.")
            
            st.markdown("#### 📈 Mathematical Models")
            st.markdown("5. **Kohlrausch, R. (1847).** *Theorie des elektrischen Rückstandes.* Poggendorff's Ann. Phys. Chem. [KWW Stretched Exponential]")
            st.markdown("6. **Eyring, H. (1935).** *The Activated Complex in Chemical Reactions.* J. Chem. Phys. [Transition State Theory]")
            st.markdown("7. **Lin, Y., et al. (2025).** *A Coupled Glassy-to-Rubbery Relaxation Model for Covalent Adaptable Networks.* Macromolecules.")
