import streamlit as st
import numpy as np
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import pandas as pd
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

                st.info("✅ **CAN-Relax Implements**: Maxwell, Single-KWW, and Dual-KWW models with automatic model selection")

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

                **Comparison:**
                | Property | Arrhenius | VFT |
                |---|---|---|
                | **Valid range** | $T \\gg T_g$ | $T_0 < T < T_g + 100°C$ |
                | **Shape** | Linear in semi-log | Curved |
                | **Parameters** | 2 ($E_a$, $\\tau_0$) | 3 ($B$, $T_0$, $\\tau_0$) |
                | **Physics** | Simple activation | Complex cooperative motion |
                """)

                st.markdown("#### 🎯 Comparison Plot: Arrhenius vs VFT")

                # Generate comparison plot
                T_range = np.linspace(300, 450, 100)
                tau_arr = np.exp(np.log(1e-6) + (80000/8.314) * (1/T_range - 1/373.15))
                tau_vft = np.exp(np.log(1e-6) + 2000/(T_range - 323.15))

                fig_comp, ax_comp = plt.subplots(figsize=(8, 5))
                ax_comp.semilogy(T_range - 273.15, tau_arr, 'o-', linewidth=2.5, markersize=4, label='Arrhenius ($E_a = 80$ kJ/mol)', color='#EF553B')
                ax_comp.semilogy(T_range - 273.15, tau_vft, 's-', linewidth=2.5, markersize=4, label='VFT ($B = 2000$ K)', color='#636EFA')
                ax_comp.axvline(x=50, color='gray', linestyle='--', alpha=0.6, label='Approximate $T_g$')
                ax_comp.set_xlabel('Temperature (°C)', fontsize=12, fontweight='bold')
                ax_comp.set_ylabel('Relaxation Time τ (s)', fontsize=12, fontweight='bold')
                ax_comp.set_title('Temperature Dependence: Arrhenius vs VFT', fontsize=13, fontweight='bold')
                ax_comp.grid(True, alpha=0.3, which='both')
                ax_comp.legend(fontsize=11, loc='upper left')
                ax_comp.set_ylim([1e-8, 1e4])
                plt.tight_layout()
                st.pyplot(fig_comp)

                st.markdown("""
                **Key Observations:**
                - VFT shows **stronger curvature** near $T_g$ (50°C in this example)
                - Arrhenius remains linear across the entire range
                - For **vitrimers near exchange threshold**, VFT is more appropriate
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

                # Create synthetic data comparing models
                t = np.logspace(-4, 2, 200)

                # Parameters
                G0 = 1.0
                tau_m = 10.0
                tau_kww = 15.0
                beta_kww = 0.85
                tau1_dual = 5.0
                beta1_dual = 0.9
                tau2_dual = 100.0
                beta2_dual = 0.7
                f_dual = 0.4

                # Generate curves
                g_maxwell = G0 * np.exp(-t/tau_m)
                g_kww = G0 * np.exp(-(t/tau_kww)**beta_kww)
                g_dual = G0 * (f_dual * np.exp(-(t/tau1_dual)**beta1_dual) + (1-f_dual) * np.exp(-(t/tau2_dual)**beta2_dual))

                fig_models, ax_models = plt.subplots(figsize=(10, 6))
                ax_models.loglog(t, g_maxwell, 'o-', linewidth=2.5, markersize=4, alpha=0.8, label='Maxwell ($τ=10$ s)')
                ax_models.loglog(t, g_kww, 's-', linewidth=2.5, markersize=4, alpha=0.8, label=f'Single-KWW ($τ=15$ s, $β=0.85$)')
                ax_models.loglog(t, g_dual, '^-', linewidth=2.5, markersize=4, alpha=0.8, label=f'Dual-KWW ($τ_1=5$, $τ_2=100$ s)')
                ax_models.set_xlabel('Time (s)', fontsize=12, fontweight='bold')
                ax_models.set_ylabel('G(t) / G₀', fontsize=12, fontweight='bold')
                ax_models.set_title('Comparison of Relaxation Models', fontsize=13, fontweight='bold')
                ax_models.grid(True, alpha=0.3, which='both')
                ax_models.legend(fontsize=11, loc='upper right')
                plt.tight_layout()
                st.pyplot(fig_models)

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

                ### 🔍 Time-Temperature Superposition

                14. Williams, M. L., et al. (1955). "The temperature dependence of relaxation mechanisms in amorphous polymers and other glass-forming liquids." *J. Am. Chem. Soc.* 77(14), 3701-3707.
                    - WLF equation and TTS principle

                ### 🧬 Advanced Topics: Vitrimer Dynamics

                15. Zheng, N., et al. (2017). "Catalyst-free thermoset polyurethane with permanent shape reconfigurability and highly tunable triple-shape memory performance." *ACS Macro Lett.* 6(3), 326-330.

                16. Stukalin, E. B., et al. (2013). "Self-healing of unentangled polymer networks with reversible bonds." *Macromolecules* 46(18), 7525-7541.

                ---

                ### 🌐 Online Resources

                - **NIST Polymer Database**: https://www.nist.gov/mml/polymers
                - **Matminer Materials Database**: https://hackingmaterials.lbl.gov/matminer/
                - **OpenScience resources**: Preprints and data repositories

                ### 💡 Key Takeaways

                ✅ **Maxwell model** = baseline (single time scale)  
                ✅ **KWW model** = stretching exponent captures polydispersity  
                ✅ **Dual-KWW model** = multiple concurrent processes  
                ✅ **Arrhenius** = simple, works far above $T_g$  
                ✅ **VFT** = better near $T_g$ (dynamic/vitrimer systems)  
                ✅ **Vitrimers** = exchangeable bonds enable reprocessing  

                """)


