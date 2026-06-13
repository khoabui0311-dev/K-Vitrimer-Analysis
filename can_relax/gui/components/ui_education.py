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
            st.header("📚 Educational & Scientific Foundation")

            edu_tabs = st.tabs([
                "🔬 Relaxation Models",
                "🌡️ Temperature Kinetics",
                "🧪 Vitrimer Chemistry",
                "📊 Model Comparison",
                "📖 References"
            ])

            # ====== TAB 1: RELAXATION MODELS ======
            with edu_tabs[0]:
                st.subheader("Stress Relaxation Models")

                st.markdown("""
                When a material is subjected to **constant strain** $\\varepsilon_0$, the stress decays over time. 
                The **relaxation modulus** describes this decay:

                $$G(t) = \\frac{\\sigma(t)}{\\varepsilon_0}$$

                Different materials exhibit different relaxation behaviors, described by mathematical models below.
                """)

                # Maxwell Model
                st.markdown("#### 1️⃣ Maxwell Model")
                st.latex(r"G(t) = G_0 \exp\left(-\frac{t}{\tau}\right)")
                st.markdown("""
                **Physical Interpretation:**
                - Single relaxation time $\\tau$
                - Assumes liquid-like behavior with one dominant relaxation process
                - Characteristic time: material relaxes to 37% ($1/e \\approx 0.368$) of initial value at $t = \\tau$

                **Parameters:**
                - $G_0$: Initial modulus (Pa)
                - $\\tau$: Relaxation time (s)

                **Applications:**
                - Simple polymers above glass transition
                - Newtonian liquids
                - First-order approximation for complex systems

                **Limitations:**
                - Assumes instantaneous strain response (no elasticity before relaxation)
                - Real polymers show broader distribution of relaxation times
                """)

                # KWW Model
                st.markdown("#### 2️⃣ Kohlrausch-Williams-Watts (KWW) Model")
                st.latex(r"G(t) = G_0 \exp\left[-\left(\frac{t}{\tau}\right)^{\beta}\right]")
                st.markdown("""
                **Physical Interpretation:**
                - **Stretched exponential** captures heterogeneous relaxation
                - $\\beta$ parameter quantifies non-exponential behavior
                - Accounts for **distribution of relaxation times** (polydispersity)

                **Parameters:**
                - $G_0$: Initial modulus (Pa)
                - $\\tau$: Characteristic time (s)
                - $\\beta$: Stretching exponent (0 < $\\beta$ ≤ 1)

                **Interpretation of $\\beta$:**
                | $\\beta$ | Meaning | Example |
                |---------|---------|---------|
                | $\\beta = 1.0$ | Single relaxation time (recovers Maxwell) | Ideal liquid |
                | $0.7 < \\beta < 1.0$ | Narrow distribution | Linear polymers |
                | $0.4 < \\beta < 0.7$ | Broad distribution | Branched polymers |
                | $\\beta < 0.4$ | Very broad distribution | Glassy polymers |

                **Applications:**
                - Amorphous polymers
                - Complex fluids
                - Glassy systems
                - Better fit for real experimental data
                """)

                # Dual KWW Model
                st.markdown("#### 3️⃣ Dual-Mode KWW (Prony-like) Model")
                st.latex(r"G(t) = G_0 \left[ f \exp\left[-\left(\frac{t}{\tau_1}\right)^{\beta_1}\right] + (1-f) \exp\left[-\left(\frac{t}{\tau_2}\right)^{\beta_2}\right] \right]")
                st.markdown("""
                **Physical Interpretation:**
                - **Superposition** of two independent relaxation processes
                - Fast mode ($\\tau_1$, $\\beta_1$): Local chain motion / exchange reactions
                - Slow mode ($\\tau_2$, $\\beta_2$): Cooperative relaxation / long-chain effects

                **Parameters:**
                - $f$: Fraction of fast mode (0 < $f$ < 1)
                - $\\tau_1, \\tau_2$: Time scales (s)
                - $\\beta_1, \\beta_2$: Stretching exponents

                **Physical Basis:**
                - **Vitrimers**: Fast mode = transesterification kinetics
                - **Block copolymers**: Fast = block motion, Slow = interface dynamics
                - **Filled polymers**: Fast = matrix, Slow = filler-matrix interaction

                **Advantages:**
                - Captures complex multi-scale dynamics
                - Better R² fit for polydisperse systems
                - Physically meaningful separation of processes
                """)

                # Continuous spectrum & Tikhonov regularization
                st.markdown("#### 4️⃣ Continuous Relaxation Spectrum & Regularization")
                st.markdown(r"""
                Instead of assuming discrete relaxation times, complex polymer networks are often best described by a **continuous relaxation spectrum** $H(\tau)$, representing the density of relaxation processes at scale $\tau$:
                
                $$G(t) = G_{eq} + \int_{-\infty}^{\infty} H(\tau) \exp\left(-\frac{t}{\tau}\right) d\ln\tau$$
                
                Solving for $H(\tau)$ from experimental stress relaxation data $G(t)$ is a mathematically **ill-posed inverse problem** (equivalent to an inverse Laplace transform). Small noise in $G(t)$ can cause wild, unphysical oscillations in $H(\tau)$.
                
                To solve this robustly, **CAN-Relax** implements **Tikhonov Regularization (Ridge Regression)** with a non-negativity constraint:
                
                $$\min_H \|A H - g\|_2^2 + \alpha \|H\|_2^2 \quad \text{subject to } H \ge 0$$
                
                Where:
                - $A_{ij} = \exp(-t_i / \tau_j)$ is the kernel matrix.
                - $g$ is the target modulus vector.
                - $\alpha$ is the regularization parameter controlling the trade-off between fitting error and spectrum smoothness.
                
                **L-Curve Corner Optimization:**
                To determine the optimal $\alpha$, we employ the **L-curve method** (Hansen et al.). By plotting the solution norm ($\|H\|_2$) versus the residual norm ($\|A H - g\|_2$) on a log-log scale for a wide range of $\alpha$, a characteristic L-shaped curve is obtained. The optimal $\alpha$ corresponds to the **corner of maximum curvature**, which represents the ideal balance between overfitting (too small $\alpha$, leading to noise artifacts) and underfitting (too large $\alpha$, over-smoothing the spectrum).
                
                **Equilibration Modulus ($G_{eq}$) Subtraction:**
                A critical requirement for regularization is that the modulus decays to zero at infinite time. In networks containing permanent cross-links, or in incomplete experiments, the modulus decays to a non-zero plateau ($G_{eq} > 0$). Failing to subtract this baseline violates the kernel assumptions, causing massive baseline artifacts at long relaxation times in the spectrum. 
                
                **Our strategy**: We automatically calculate the mean of the last 5% of data points as $G_{eq}$ and subtract it prior to the regularized inversion:
                
                $$g_{target}(t) = G(t) - G_{eq}$$
                
                This aligns directly with the methodology described in *Wink et al., ACS Polym. Au 2026*.

                **Short-Time Loading Transients & Machinery Artifacts (Staircase Curve):**
                During the very early stage of a stress relaxation test (typically $t < 0.5 - 1.0$ s), the rheometer motor requires a finite rise time to apply the step strain. Consequently, this phase does not reflect true stress relaxation but rather the dynamics of the deformation process. In addition, transducer quantization limits and feedback control loops at these short timescales often introduce step-like oscillations, presenting as a "staircase" pattern.
                
                **Impact on Continuous Spectrum**: Inverting raw relaxation data to extract $H(\tau)$ is a highly ill-posed problem. High-frequency noise or staircase patterns at short times violate the assumption of a perfect step strain starting at $t=0$, causing the Tikhonov inversion to generate false, high-intensity spectral artifacts at extremely short timescales ($\tau < 0.1$ s).
                
                **Our Strategy (Short-Time Cutoff)**: To remove these machinery artifacts, **CAN-Relax** provides a **Short-Time Cutoff (s)** sidebar input. Users can filter out these early corrupt data points, yielding cleaner and physically representative relaxation spectra.
                
                **Normalization Consistency**: The data processing pipeline handles the cropped time series dynamically: it finds the peak modulus in the remaining range as the new $G_0$, shifts the initial time to $0.01$ s (retaining numerical stability on logarithmic time axes), and re-normalizes the curve accordingly.
                """)

                st.info("✅ **CAN-Relax Implements**: Maxwell, Single-KWW, Dual-KWW, and Continuous Tikhonov Relaxation Spectrum with L-curve optimization and G_eq subtraction.")

            # ====== TAB 2: TEMPERATURE KINETICS ======
            with edu_tabs[1]:
                st.subheader("Temperature-Dependent Relaxation Kinetics")

                st.markdown("""
                Relaxation times are **highly temperature-dependent**. Different models describe this behavior:
                """)

                # Arrhenius
                st.markdown("#### 🔴 Arrhenius Model (High Temperature)")
                st.latex(r"\tau(T) = \tau_0 \exp\left(\frac{E_a}{R T}\right)")
                st.markdown("""
                **Linear form** (most useful for analysis):
                $$\\ln(\\tau) = \\ln(\\tau_0) + \\frac{E_a}{R T}$$

                Or equivalently:
                $$\\ln(\\tau) = \\ln(\\tau_0) + \\frac{E_a}{R} \\left(\\frac{1}{T}\\right)$$

                **Plot:** $\\ln(\\tau)$ vs $1000/T$ gives **linear slope** $= E_a / (1000 R)$

                **Parameters:**
                - $E_a$: Activation energy (kJ/mol) — typical range: 20-300 kJ/mol
                - $\\tau_0$: Pre-exponential factor (s)
                - $R = 8.314$ J/(mol·K): Gas constant
                - $T$: Absolute temperature (K)

                **Typical Ranges:**
                | Material Class | $E_a$ (kJ/mol) | Valid T Range |
                |---|---|---|
                | Silicone polymers | 30-60 | $T_g + 50°C$ and above |
                | Epoxy vitrimers | 80-150 | $T_g + 40°C$ and above |
                | Polyethylene | 80-120 | Rubbery plateau region |
                | Cross-linked polymers | 100-200 | Above network Tg |

                **When to use:**
                - Data well above glass transition ($T \\gtrsim T_g + 50°C$)
                - Linear Arrhenius plot
                - Temperature range doesn't approach $T_g$
                """)

                # VFT
                st.markdown("#### 🔵 Vogel-Fulcher-Tammann (VFT) Model (Near Glass Transition)")
                st.latex(r"\ln(\tau) = \ln(\tau_0) + \frac{B}{T - T_0}")
                st.markdown("""
                **Physical Meaning:**
                - $T_0$: **Ideal glass transition temperature** (usually $T_0 \\approx T_g - 50$°C)
                - Accounts for **non-linear curvature** near $T_g$
                - Relaxation time → ∞ as $T$ → $T_0$ (system "freezes")

                **Parameters:**
                - $\\tau_0$: Pre-exponential factor (s)
                - $B$: Steepness parameter (K) — larger $B$ = steeper rise near $T_g$
                - $T_0$: Ideal glass temperature (K)

                **When to use:**
                - Data spanning across and near $T_g$
                - Curved Arrhenius plot
                - Strongly temperature-sensitive materials (vitrimers, polymer blends)
                """)

                # Eyring
                st.markdown("#### 🟢 Eyring Model (Transition State Theory)")
                st.latex(r"\ln(\tau \cdot T) = \ln\left(\frac{h}{k_B}\right) - \frac{\Delta S^{\ddagger}}{R} + \frac{\Delta H^{\ddagger}}{R T}")
                st.markdown(r"""
                **Physical Interpretation:**
                - Based on **Transition State Theory** (TST), assuming that stress relaxation rate ($1/\tau$) is governed by the chemical exchange rate.
                - Relates relaxation kinetics directly to thermodynamic activation parameters.

                **Parameters:**
                - $\Delta H^{\ddagger}$: Activation enthalpy (kJ/mol) — the energy barrier required to reach the transition state.
                - $\Delta S^{\ddagger}$: Activation entropy (J/mol·K) — measures structural changes (ordering/disordering) when forming the transition state.
                - $h = 6.626 \times 10^{-34}$ J·s: Planck constant.
                - $k_B = 1.381 \times 10^{-23}$ J/K: Boltzmann constant.
                - $R = 8.314$ J/(mol·K): Gas constant.

                **Mechanism Diagnosis via Activation Entropy ($\Delta S^{\ddagger}$):**
                - **$\Delta S^{\ddagger} < 0$ (Negative)**: Indicates an **associative mechanism** (e.g., transesterification, transamination). The transition state involves coordination of active groups, leading to a more ordered, structurally constrained state.
                - **$\Delta S^{\ddagger} > 0$ (Positive)**: Indicates a **dissociative mechanism** (e.g., Diels-Alder, boronic ester cleavage). The transition state is more disordered due to bond-breaking before bond-reforming.
                """)

                # Van 't Hoff
                st.markdown("#### 🟣 Van 't Hoff Model (Decrosslinking Thermodynamics)")
                st.latex(r"G_0(T) = \frac{G_{0,\max}}{1 + \exp\left(-\frac{\Delta H_d}{R T} + \frac{\Delta S_d}{R}\right)}")
                st.markdown(r"""
                **Physical Interpretation:**
                - Describes the **thermal dissociation of cross-links** in dissociative CANs (e.g., Diels-Alder networks).
                - Models the decrease of the rubbery plateau modulus ($G_0$ or $E_0$) in **MPa** as a function of temperature due to network decrosslinking.

                **Parameters:**
                - $G_{0,\max}$: Maximum plateau modulus (MPa) at low temperatures where all dynamic cross-links are intact.
                - $\Delta H_d$: Enthalpy of bond dissociation (kJ/mol).
                - $\Delta S_d$: Entropy of bond dissociation (J/mol·K).
                """)

                # Coupled WLF-Arrhenius
                st.markdown("#### 🟤 Coupled WLF-Arrhenius Model")
                st.latex(r"\tau(T) = A \exp\left(\frac{E_{a,chem}}{R T}\right) + C \exp\left(\frac{B}{T - T_0}\right)")
                st.markdown(r"""
                **Physical Interpretation:**
                - Captures **both regimes** in covalent adaptable networks:
                  1. Glass transition dynamics at low temperatures (cooperative motion described by the VFT/WLF term).
                  2. Chemical bond exchange dynamics at high temperatures (Arrhenius term).
                - Fits the complete temperature range, avoiding the typical overestimation of relaxation times when using pure Arrhenius near $T_g$.

                **Parameters:**
                - $E_{a,chem}$: Activation energy of the chemical bond exchange (kJ/mol).
                - $B, T_0$: Vogel-Fulcher-Tammann parameters describing glass dynamics.
                - $A, C$: Pre-exponential scaling constants.
                """)

                st.markdown("#### 🎯 Comparison Plot: Temperature Kinetics Models")
                st.image(get_kinetics_comparison_plot(), width=700)

                st.markdown("""
                **Key Observations:**
                - **Arrhenius & Eyring**: Linear behavior in semi-log plots, representing single active barrier kinetics. Excellent at high temperatures ($T \gg T_g$).
                - **VFT**: Exhibits strong upward curvature as the temperature approaches $T_g$ due to cooperative glassy dynamics.
                - **Coupled WLF-Arrhenius**: Combines both regimes. It matches the VFT curve near $T_g$ and transitions smoothly into the linear Arrhenius regime at high temperatures.
                """)

            # ====== TAB 3: VITRIMER CHEMISTRY ======
            with edu_tabs[2]:
                st.subheader("Vitrimer Exchange Kinetics & Mechanisms")

                st.markdown("""
                **Vitrimers** are dynamic polymers with exchangeable cross-links. Unlike traditional cross-linked polymers,
                they can flow and be reprocessed through **transesterification or other exchange reactions**.
                """)

                st.markdown("#### 🔄 Common Exchange Mechanisms")

                col1, col2 = st.columns(2)

                with col1:
                    st.markdown("**1. Transesterification (Ester Exchange)**")
                    st.latex(r"R_1-C(=O)-O-R_2 + R_3-OH \rightleftharpoons R_1-C(=O)-O-R_3 + R_2-OH")
                    st.markdown("""
                    - **Catalyst**: Usually acid, base, or metal catalysts
                    - **Example materials**: Epoxy-anhydride, polyester
                    - **Temperature range**: 100-200°C
                    - **Kinetics**: Typically 1st or 2nd order
                    """)

                with col2:
                    st.markdown("**2. Disulfide Exchange (Bond Exchange)**")
                    st.latex(r"R-S-S-R' + R''-SH \rightleftharpoons R-S-S-R'' + R'-SH")
                    st.markdown("""
                    - **Catalyst**: Disulfide-containing species
                    - **Example materials**: Polysulfide-based vitrimers
                    - **Temperature range**: 80-150°C
                    - **Kinetics**: Nucleophilic substitution
                    """)

                st.markdown("#### ⚛️ Relaxation Mechanism in Vitrimers")
                st.markdown("""
                **Two-timescale process:**

                1. **Short timescale** ($\\tau_1 \\sim$ ms-s): Glassy/rubbery relaxation (no chain motion)
                2. **Long timescale** ($\\tau_2 \\sim$ s-hours): **Exchange-induced flow**

                The **Dual-KWW model** captures this:
                - Fast component ($\\tau_1, \\beta_1$): Inherent polymer relaxation
                - Slow component ($\\tau_2, \\beta_2$): Stress relaxation due to bond exchange

                **Key insight**: $\\tau_2$ is **kinetically controlled** by reaction rates, not just molecular weight!

                $$\\tau_2 \\propto \\frac{1}{k_{exchange}} \\propto \\exp\\left(\\frac{E_a}{RT}\\right)$$

                This explains why vitrimers show **VFT-like or Arrhenius behavior** despite being amorphous.
                """)

                st.markdown("#### 📊 Vitrimer vs Thermoset vs Thermoplastic")

                comparison_df = pd.DataFrame({
                    'Property': ['Reversibility', 'Reprocessability', 'Stress Relaxation', 'Typical τ@T_g+50', 'Model Fit'],
                    'Thermoset': ['❌ Irreversible', '❌ Cannot remold', '🔴 No relaxation', '$\\infty$ (frozen)', 'N/A'],
                    'Vitrimer': ['✅ Reversible exchange', '✅ Can remold', '🟡 Slow (hrs)', '100-10000 s', 'Dual-KWW'],
                    'Thermoplastic': ['✅ Reversible chain', '✅ Can remold', '✅ Fast (mins)', '1-100 s', 'Single-KWW']
                })

                st.dataframe(comparison_df, hide_index=True, width='stretch')

                st.markdown("""
                **Temperature Effect on Vitrimer Exchange:**

                $$k_{exchange}(T) = k_0 \\exp\\left(-\\frac{E_{a,exchange}}{RT}\\right)$$

                - **Low T** ($T < T_{exchange}$): Exchange frozen, behaves like thermoset
                - **Mid T** ($T_{exchange} < T < T_g + 50°C$): Slow exchange, plastic behavior
                - **High T** ($T > T_g + 50°C$): Fast exchange, liquid-like behavior
                """)

                # CAN Characterization Strategy
                st.markdown("### 🧭 CAN Characterization Strategy in CAN-Relax")
                st.markdown(r"""
                Our software implements the recommended characterization workflow detailed in the scientific literature (*Berne et al., ACS Polym. Au 2025*):
                
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
    (Arrhenius, Eyring, VFT, Coupled)
                │
                ▼
       [Parameter Estimation]
  (Ea, ΔH‡, ΔS‡, and BIC selection)
                ```
                
                1. **Linear Viscoelastic Region (LVE) & MPa Modulus**: Stress relaxation tests are conducted under constant small strain. Initial plateau modulus values ($G_0$/$E_0$) are processed and reported in **MPa**.
                2. **G_eq Subtraction**: If dynamic networks contain permanent cross-links or measurements are truncated, the stress decays to a non-zero equilibration plateau ($G_{eq}$). We subtract this tail value before inverting the spectrum to avoid long-time spectral baseline artifacts.
                3. **Parallel Analysis Tracks**: 
                   * **Parametric Model Fitting**: Users fit discrete phenomenological models (Maxwell, Single-KWW, or Dual-KWW) to explicitly extract the characteristic relaxation time ($\tau^*$).
                   * **Continuous Spectrum Diagnostics**: In parallel, the continuous relaxation spectrum $H(\tau)$ is extracted via Ridge regression with Hansen's L-curve corner optimization. This serves as a diagnostic tool to verify the number of relaxation modes and mathematically warn about incomplete relaxation, but is *not* the model used to extract $\tau^*$ for kinetic fitting.
                4. **Temperature-dependent Kinetics**: The relaxation times $\tau(T)$ from the parametric models are analyzed using Arrhenius or Eyring (Transition State Theory) models to diagnose chemical mechanisms, or Vogel-Fulcher-Tammann (VFT) / Coupled WLF-Arrhenius models to study glass dynamics.
                5. **Decrosslinking analysis**: The temperature-dependent modulus $G_0(T)$ is analyzed using the Van 't Hoff equation to model network dissociation thermodynamics.
                """)

            # ====== TAB 4: MODEL COMPARISON ======
            with edu_tabs[3]:
                st.subheader("Comparing Relaxation Models: Examples & Decision Tree")

                st.markdown("#### 📊 When to Use Which Model?")

                decision_tree = """
                ```
                START: Relaxation curve analysis
                │
                ├─ Is R² for Maxwell > 0.95?
                │  ├─ YES → Use MAXWELL
                │  │        (Simple liquid-like behavior)
                │  │
                │  └─ NO → Continue...
                │
                ├─ Is R² for Single-KWW > 0.98?
                │  ├─ YES → Use SINGLE-KWW
                │  │        (Monodisperse relaxation)
                │  │        Check β: if β > 0.85 → nearly exponential
                │  │              if β < 0.75 → broad distribution
                │  │
                │  └─ NO → Continue...
                │
                └─ Use DUAL-KWW
                   (Multiple relaxation mechanisms detected)
                   Interpret: Fast mode + Slow mode
                              (e.g., glassy + exchange in vitrimer)
                ```
                """
                st.code(decision_tree, language=None)

                st.markdown("#### 🔬 Simulated Examples: Model Comparison")
                st.image(get_models_comparison_plot(), width=800)

                st.markdown("""
                **Observations from Example:**
                - **Maxwell** (red): Simplest, single exponential decay
                - **Single-KWW** (blue): Stretched exponential, slight curvature on log-log plot
                - **Dual-KWW** (green): Two distinct timescales visible, strong multi-slope behavior

                **How to Recognize:**
                - **Single-slope on log-log plot** → Maxwell or Single-KWW
                - **Clear change in slope** → Dual-KWW (indicates multiple processes)
                - **β value interpretation**: β < 0.8 suggests significant polydispersity
                """)

                st.markdown("#### ⚖️ Automated Kinetics Model Selection (BIC & AICc)")
                st.markdown(r"""
                When analyzing temperature-dependent kinetics, more complex models with more parameters (e.g., VFT with 3 parameters or Coupled WLF-Arrhenius with 5 parameters) will always give lower residuals than simpler models (e.g., Arrhenius or Eyring with 2 parameters). However, this can lead to **overfitting**.
                
                To balance goodness-of-fit with model complexity, **CAN-Relax** computes two statistical criteria:
                
                * **Bayesian Information Criterion (BIC)**:
                  $$BIC = n \ln\left(\frac{\text{RSS}}{n}\right) + k \ln(n)$$
                
                * **Akaike Information Criterion with Correction for Small Sample Sizes (AICc)**:
                  $$AICc = n \ln\left(\frac{\text{RSS}}{n}\right) + 2k + \frac{2k(k+1)}{n-k-1}$$
                
                Where:
                - $n$: Number of experimental temperature points.
                - $k$: Number of model parameters (Arrhenius = 2, Eyring = 2, VFT = 3, Van 't Hoff = 3, Coupled = 5).
                - $RSS$: Residual Sum of Squares of the fit.
                
                **Decision Strategy**:
                The model that minimizes the BIC (or AICc) is identified as the statistically optimal choice. This ensures that the 5-parameter Coupled model is only recommended if it provides a massive improvement in fit quality compared to the 2-parameter Arrhenius or Eyring models.
                """)

            # ====== TAB 5: REFERENCES ======
            with edu_tabs[4]:
                st.subheader("Scientific References & Literature")

                st.markdown("""
                ### 📚 Foundational Papers on Relaxation Models

                **KWW (Stretched Exponential):**
                1. Kohlrausch, R. (1847). "Theorie des elektrischen Rückstandes." *Poggendorff's Ann. Phys. Chem.* 91(2), 179-214.
                   - Original stretched exponential discovery

                2. Williams, G., & Watts, D. C. (1970). "Non-symmetrical dielectric relaxation behaviour arising from a simple empirical decay function." *Trans. Faraday Soc.* 66, 80-85.
                   - Modern formulation as "KWW function"

                3. Phillips, J. C. (1996). "Stretched exponential relaxation in molecular and electronic glasses." *Rep. Prog. Phys.* 59(9), 1133.
                   - Theoretical justification and applications

                ### 🧪 Vitrimer Chemistry & Design

                **Seminal Vitrimer Papers:**
                4. Denissen, W., Winne, J. M., & Du Prez, F. E. (2016). "Vitrimers: permanent organic networks with glass-like fluidity." *Chem. Sci.* 7(1), 30-38.
                   - Landmark paper introducing concept

                5. Montarnal, D., et al. (2011). "Silica-like malleable materials from permanent organic polymers." *Science* 334(6058), 965-968.
                   - Original transesterification-based vitrimer

                6. Guerre, M., Taplan, C., Winne, J. M., & Du Prez, F. E. (2020). "Vitrimers: directing chemical reactivity to control material properties." *Chem. Sci.* 11(19), 4855-4870.
                   - Recent comprehensive review

                ### 🌡️ Temperature-Dependent Kinetics

                7. Arrhenius, S. (1889). "Über die Dissociationswärme und den Einfluss der Temperatur auf den Ausschlag des galvanischen Elements." *Z. Phys. Chem.* 4, 96-116.
                   - Classical Arrhenius equation

                8. Vogel, H. (1921). "The temperature dependence law for the viscosity of fluids." *Phys. Z.* 22, 645-646.
                   - VFT model introduction

                9. Fulcher, G. S. (1925). "Analysis of recent measurements of the viscosity of glasses." *J. Am. Ceram. Soc.* 8(6), 339-355.
                   - VFT formulation

                10. Böhmer, R., et al. (1993). "Nonexponential relaxations in strong and fragile glass formers." *J. Chem. Phys.* 99(5), 4201-4209.
                    - Fragility concept and VFT analysis

                ### 📊 Rheology & Polymer Physics

                11. Ferry, J. D. (1980). *Viscoelastic Properties of Polymers* (3rd ed.). Wiley.
                    - Classic textbook on polymer relaxation

                12. Menard, K. P. (2008). *Dynamic Mechanical Analysis: A Practical Introduction* (2nd ed.). CRC Press.
                    - Experimental techniques and analysis

                13. Larson, R. G. (1999). *The Structure and Rheology of Complex Fluids*. Oxford University Press.
                    - Comprehensive theory

                ### 🧬 Advanced Topics: Vitrimer Dynamics

                15. Zheng, N., et al. (2017). "Catalyst-free thermoset polyurethane with permanent shape reconfigurability and highly tunable triple-shape memory performance." *ACS Macro Lett.* 6(3), 326-330.

                16. Stukalin, E. B., et al. (2013). "Self-healing of unentangled polymer networks with reversible bonds." *Macromolecules* 46(18), 7525-7541.

                ### 📘 Key Reference Guidelines for CAN Characterization

                17. **Berne, D., Laviéville, S., Leclerc, E., Caillol, S., Ladmiral, V., & Bakkali-Hassani, C. (2025).** "How to Characterize Covalent Adaptable Networks: A User Guide." *ACS Polym. Au* 5, 214-240.
                    - Detailed guidelines on DMA, stress relaxation, Arrhenius, and Eyring analysis.

                18. **Wink, R., Geerars, O. B., Heuts, J. P. A., & Sijbesma, R. P. (2026).** "A Practical User Guide to Stress Relaxation Spectra of Dynamic Covalent Networks." *ACS Polym. Au* 6(2), 107-116.
                    - Practical tutorial on Tikhonov regularization, Hansen's L-curve, and equilibration modulus (G_eq) baseline correction.

                19. **Lin, Y., et al. (2025).** "A Coupled Glassy-to-Rubbery Relaxation Model for Covalent Adaptable Networks." *Macromolecules* 58, 2341-2350.
                    - Proposing the coupled VFT-Arrhenius model for wide temperature range analysis.

                ---

                ### 🌐 Online Resources

                - **NIST Polymer Database**: https://www.nist.gov/mml/polymers
                - **Matminer Materials Database**: https://hackingmaterials.lbl.gov/matminer/
                - **OpenScience resources**: Preprints and data repositories

                ### 💡 Key Takeaways

                ✅ **Maxwell model** = baseline (single time scale)  
                ✅ **KWW model** = stretching exponent captures polydispersity  
                ✅ **Dual-KWW model** = multiple concurrent processes  
                ✅ **Arrhenius & Eyring** = simple, works far above $T_g$; Eyring yields activation enthalpy/entropy  
                ✅ **VFT & Coupled** = better near $T_g$ (captures cooperative glassy dynamics)  
                ✅ **Van 't Hoff** = describes thermal dissociation of plateau modulus in MPa  
                ✅ **Tikhonov regularization** = extracts continuous relaxation spectrum $H(\tau)$ with L-curve corner detection and $G_{eq}$ subtraction  
                """)
