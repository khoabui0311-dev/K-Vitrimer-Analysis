import numpy as np
from scipy.stats import linregress
from scipy.optimize import curve_fit

R_GAS = 8.314462  # J/mol*K
H_PLANCK = 6.62607015e-34  # J*s
K_BOLTZMANN = 1.380649e-23  # J/K
LN_H_OVER_KB = np.log(H_PLANCK / K_BOLTZMANN)  # ~ -23.759978

class KineticsEngine:
    def __init__(self):
        pass

    def fit_arrhenius(self, temps_C, taus):
        """
        Fits ln(tau) = ln(tau0) + Ea / (R * T)
        Returns: Ea (kJ/mol), R2, and fit curve.
        """
        if len(temps_C) < 2: return None

        T_K = np.array(temps_C) + 273.15
        inv_T = 1000.0 / T_K
        ln_tau = np.log(np.array(taus))

        # Linear regression: ln(tau) = slope * (1000/T) + intercept
        # Let's redo with standard 1/T for clarity
        inv_T_standard = 1.0 / T_K
        slope_std, intercept_std, r_std, p_val, stderr_std = linregress(inv_T_standard, ln_tau)
        
        Ea_J = slope_std * R_GAS
        Ea_kJ = Ea_J / 1000.0
        Ea_std_kJ = (stderr_std * R_GAS) / 1000.0
        
        return {
            "Type": "Arrhenius",
            "Ea": Ea_kJ,
            "Ea_std": Ea_std_kJ,
            "R2": r_std**2,
            "Params": {"slope": slope_std, "intercept": intercept_std},
            "Plot": {"x": inv_T_standard, "y": ln_tau, "y_pred": slope_std*inv_T_standard + intercept_std}
        }

    def fit_eyring(self, temps_C, taus):
        """
        Fits Eyring equation: ln(tau * T) = ln(h / kB) - dS / R + dH / (R * T)
        Returns: dH (kJ/mol), dS (J/mol*K), R2, and fit curve.
        """
        if len(temps_C) < 2: return None

        T_K = np.array(temps_C) + 273.15
        inv_T = 1.0 / T_K
        y_val = np.log(np.array(taus) * T_K)

        slope, intercept, r_val, _, stderr = linregress(inv_T, y_val)

        dH_J = slope * R_GAS
        dH_kJ = dH_J / 1000.0
        dH_std_kJ = (stderr * R_GAS) / 1000.0

        # intercept = LN_H_OVER_KB - dS / R  =>  dS = R * (LN_H_OVER_KB - intercept)
        dS = R_GAS * (LN_H_OVER_KB - intercept)

        return {
            "Type": "Eyring",
            "dH": dH_kJ,
            "dH_std": dH_std_kJ,
            "dS": dS,
            "R2": r_val**2,
            "Params": {"slope": slope, "intercept": intercept},
            "Plot": {"x": inv_T, "y": y_val, "y_pred": slope * inv_T + intercept}
        }

    def fit_van_t_hoff(self, temps_C, G0s):
        """
        Fits temperature dependence of plateau modulus G0 using Van 't Hoff:
        G0(T) = G0_max / (1 + exp(-dH_diss / (R * T) + dS_diss / R))
        Returns: dH_diss (kJ/mol), dS_diss (J/mol*K), G0_max (MPa/Pa), R2, and fit curve.
        """
        if len(temps_C) < 3: return None

        T_K = np.array(temps_C) + 273.15
        G0s = np.array(G0s)

        def van_t_hoff_func(T, A, dH, dS):
            exponent = -dH / (R_GAS * T) + dS / R_GAS
            exponent = np.clip(exponent, -50.0, 50.0)
            return (A * T) / (1.0 + np.exp(exponent))

        try:
            # Initial guess: G0_max roughly occurs at high T? No, A*T is the max.
            # So A ~ np.max(G0s) / np.min(T_K)
            A_p0 = float(np.max(G0s) / np.max(T_K) * 1.5)
            # Transesterification/bond dissociation typically has dH around 60-120 kJ/mol
            p0 = [A_p0, 80000.0, 150.0]
            bounds = (
                [np.max(G0s) / np.max(T_K) * 0.1, 0.0, -500.0],
                [np.max(G0s) / np.min(T_K) * 10.0, 500000.0, 500.0]
            )

            popt, _ = curve_fit(van_t_hoff_func, T_K, G0s, p0=p0, bounds=bounds, maxfev=5000)
            pred = van_t_hoff_func(T_K, *popt)

            ss_res = np.sum((G0s - pred)**2)
            ss_tot = np.sum((G0s - np.mean(G0s))**2)
            r2 = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

            return {
                "Type": "Van_t_Hoff",
                "A": popt[0],
                "dH_diss": popt[1] / 1000.0,  # to kJ/mol
                "dS_diss": popt[2],  # J/mol*K
                "R2": r2,
                "Params": {"G0_max": popt[0], "dH_diss": popt[1], "dS_diss": popt[2]},
                "Plot": {"x": 1000.0 / T_K, "y": G0s, "y_pred": pred}
            }
        except Exception as e:
            print(f"Van 't Hoff fit failed: {e}")
            return None

    def fit_vft(self, temps_C, taus):
        """
        Fits ln(tau) = A + B / (T - T0)
        """
        if len(temps_C) < 4: return None
        
        T_K = np.array(temps_C) + 273.15
        ln_tau = np.log(np.array(taus))
        
        def vft_func(T, A, B, T0):
            return A + B / (T - T0)
        
        # Bounds: T0 must be below min(T_K)
        try:
            p0 = [-10, 1000, T_K.min() - 50]
            bounds = ([-np.inf, 0, 0], [np.inf, np.inf, T_K.min() - 1])
            popt, _ = curve_fit(vft_func, T_K, ln_tau, p0=p0, bounds=bounds, maxfev=5000)
            
            # Calc R2
            pred = vft_func(T_K, *popt)
            ss_res = np.sum((ln_tau - pred)**2)
            ss_tot = np.sum((ln_tau - np.mean(ln_tau))**2)
            r2 = 1 - (ss_res / ss_tot)
            
            return {
                "Type": "VFT",
                "R2": r2,
                "Params": {"A": popt[0], "B": popt[1], "T0": popt[2]},
                "Plot": {"x": 1.0/T_K, "y": ln_tau, "y_pred": pred} # Plotted vs 1/T for comparison
            }
        except:
            return None

    def fit_coupled_kinetics(self, temps_C, taus, Tg=None):
        """
        Fits the coupled glassy-to-rubbery relaxation time model (Lin et al., 2025):
        tau(T) = A * exp(Ea / (R * T)) + C * exp(B / (T - T0))
        Fits ln(tau) = ln(A * exp(Ea / (R * T)) + C * exp(B / (T - T0)))
        T0 is fixed to Tg - 50 K (if Tg is provided) or fit with bounds.
        """
        if len(temps_C) < 4: return None

        T_K = np.array(temps_C) + 273.15
        ln_tau = np.log(np.array(taus))

        if Tg is not None:
            T0_val = 273.15 + (Tg - 50.0)
            # Ensure T0 is at least 5K below minimum experimental temperature
            T0_val = min(T0_val, T_K.min() - 5.0)
            
            def coupled_fixed_T0(T, ln_A, Ea, ln_C, B):
                term1 = np.exp(ln_A + Ea / (R_GAS * T))
                term2 = np.exp(ln_C + B / (T - T0_val))
                return np.log(term1 + term2)

            try:
                # Guesses: ln_A (chem), Ea (chem), ln_C (glass), B (glass VFT)
                p0 = [np.log(min(taus)) - 10, 80000.0, np.log(max(taus)), 1500.0]
                bounds = (
                    [-50.0, 1000.0, -50.0, 100.0],
                    [50.0, 300000.0, 50.0, 20000.0]
                )
                popt, _ = curve_fit(coupled_fixed_T0, T_K, ln_tau, p0=p0, bounds=bounds, maxfev=5000)
                pred = coupled_fixed_T0(T_K, *popt)

                ss_res = np.sum((ln_tau - pred)**2)
                ss_tot = np.sum((ln_tau - np.mean(ln_tau))**2)
                r2 = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

                return {
                    "Type": "Coupled",
                    "R2": r2,
                    "Ea_chem": popt[1] / 1000.0,  # to kJ/mol
                    "B_glass": popt[3],
                    "T0_glass": T0_val - 273.15,  # to °C
                    "Params": {"ln_A": popt[0], "Ea": popt[1], "ln_C": popt[2], "B": popt[3], "T0": T0_val},
                    "Plot": {"x": 1.0 / T_K, "y": ln_tau, "y_pred": pred}
                }
            except Exception as e:
                print(f"Coupled fixed-T0 fit failed: {e}")
                return None
        else:
            # Fit T0 as a parameter
            def coupled_free_T0(T, ln_A, Ea, ln_C, B, T0):
                term1 = np.exp(ln_A + Ea / (R_GAS * T))
                term2 = np.exp(np.clip(ln_C + B / (T - T0), -50, 50))
                return np.log(term1 + term2)

            try:
                p0 = [np.log(min(taus)) - 10, 80000.0, np.log(max(taus)), 1500.0, T_K.min() - 50.0]
                bounds = (
                    [-50.0, 1000.0, -50.0, 100.0, 100.0],
                    [50.0, 300000.0, 50.0, 20000.0, T_K.min() - 2.0]
                )
                popt, _ = curve_fit(coupled_free_T0, T_K, ln_tau, p0=p0, bounds=bounds, maxfev=10000)
                pred = coupled_free_T0(T_K, *popt)

                ss_res = np.sum((ln_tau - pred)**2)
                ss_tot = np.sum((ln_tau - np.mean(ln_tau))**2)
                r2 = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

                return {
                    "Type": "Coupled",
                    "R2": r2,
                    "Ea_chem": popt[1] / 1000.0,
                    "B_glass": popt[3],
                    "T0_glass": popt[4] - 273.15,
                    "Params": {"ln_A": popt[0], "Ea": popt[1], "ln_C": popt[2], "B": popt[3], "T0": popt[4]},
                    "Plot": {"x": 1.0 / T_K, "y": ln_tau, "y_pred": pred}
                }
            except Exception as e:
                print(f"Coupled free-T0 fit failed: {e}")
                return None