import numpy as np
from scipy.stats import linregress
from scipy.optimize import curve_fit

R_GAS = 8.314462  # J/mol*K
H_PLANCK = 6.62607015e-34  # J*s
K_BOLTZMANN = 1.380649e-23  # J/K
LN_H_OVER_KB = np.log(H_PLANCK / K_BOLTZMANN)  # ~ -23.759978

def predict_van_t_hoff(T_K, A, dH_diss, dS_diss):
    """Predict modulus: A [MPa/K], dH [J/mol], dS [J/(mol K)], T [K]."""
    T = np.asarray(T_K, dtype=float)
    exponent = -dH_diss / (R_GAS * T) + dS_diss / R_GAS
    return A * T * np.exp(-np.logaddexp(0.0, exponent))


def predict_coupled(T_K, ln_A, Ea, ln_C, B, T0):
    """Predict log(tau) stably; Ea [J/mol], temperatures and B [K]."""
    T = np.asarray(T_K, dtype=float)
    return np.logaddexp(ln_A + Ea / (R_GAS * T), ln_C + B / (T - T0))


def _validated_inputs(temps_C, values, minimum):
    """Require finite physical arrays and enough distinct temperatures."""
    try:
        temperatures = np.asarray(temps_C, dtype=float)
        values = np.asarray(values, dtype=float)
    except (TypeError, ValueError):
        return None
    if (temperatures.ndim != 1 or values.ndim != 1
            or temperatures.shape != values.shape or len(values) < minimum
            or not np.all(np.isfinite(temperatures)) or not np.all(np.isfinite(values))
            or np.any(temperatures <= -273.15) or np.any(values <= 0)
            or np.unique(temperatures).size < minimum):
        return None
    return temperatures + 273.15, values


class KineticsEngine:
    def __init__(self):
        pass

    def fit_arrhenius(self, temps_C, taus):
        """
        Fits ln(tau) = ln(tau0) + Ea / (R * T)
        Returns: Ea (kJ/mol), R2, and fit curve.
        """
        inputs = _validated_inputs(temps_C, taus, 2)
        if inputs is None:
            return None
        T_K, taus = inputs
        inv_T = 1000.0 / T_K
        ln_tau = np.log(np.array(taus))

        # Linear regression: ln(tau) = slope * (1000/T) + intercept
        # Let's redo with standard 1/T for clarity
        inv_T_standard = 1.0 / T_K
        slope_std, intercept_std, r_std, p_val, stderr_std = linregress(inv_T_standard, ln_tau)
        
        Ea_J = slope_std * R_GAS
        Ea_kJ = Ea_J / 1000.0
        Ea_std_kJ = (stderr_std * R_GAS) / 1000.0 if len(taus) > 2 else np.nan
        
        return {
            "Type": "Arrhenius",
            "Warning": "Two observations: uncertainty cannot be estimated." if len(taus) == 2 else None,
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
        inputs = _validated_inputs(temps_C, taus, 2)
        if inputs is None:
            return None
        T_K, taus = inputs
        inv_T = 1.0 / T_K
        y_val = np.log(taus) + np.log(T_K)

        slope, intercept, r_val, _, stderr = linregress(inv_T, y_val)

        dH_J = slope * R_GAS
        dH_kJ = dH_J / 1000.0
        dH_std_kJ = (stderr * R_GAS) / 1000.0 if len(taus) > 2 else np.nan

        # intercept = LN_H_OVER_KB - dS / R  =>  dS = R * (LN_H_OVER_KB - intercept)
        dS = R_GAS * (LN_H_OVER_KB - intercept)

        return {
            "Type": "Eyring",
            "Warning": "Two observations: uncertainty cannot be estimated." if len(taus) == 2 else None,
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
        G0(T) = A*T / (1 + exp(-dH_diss / (R * T) + dS_diss / R))
        Returns: dH_diss (kJ/mol), dS_diss (J/mol*K), A (MPa/K), R2, and fit curve.
        """
        inputs = _validated_inputs(temps_C, G0s, 4)
        if inputs is None:
            return None
        T_K, G0s = inputs

        try:
            # A*T is the fully associated modulus envelope.
            A_p0 = float(np.max(G0s) / np.max(T_K) * 1.5)
            # Transesterification/bond dissociation typically has dH around 60-120 kJ/mol
            p0 = [A_p0, 80000.0, 150.0]
            bounds = (
                [np.max(G0s) / np.max(T_K) * 0.1, 0.0, -500.0],
                [np.max(G0s) / np.min(T_K) * 10.0, 500000.0, 500.0]
            )

            popt, _ = curve_fit(predict_van_t_hoff, T_K, G0s, p0=p0, bounds=bounds, maxfev=5000)
            pred = predict_van_t_hoff(T_K, *popt)
            if not np.all(np.isfinite(popt)) or not np.all(np.isfinite(pred)):
                return None

            ss_res = np.sum((G0s - pred)**2)
            ss_tot = np.sum((G0s - np.mean(G0s))**2)
            r2 = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

            return {
                "Type": "Van_t_Hoff",
                "A": popt[0],
                "dH_diss": popt[1] / 1000.0,  # to kJ/mol
                "dS_diss": popt[2],  # J/mol*K
                "R2": r2,
                "Units": {"A": "MPa/K", "dH_diss": "kJ/mol", "dS_diss": "J/(mol K)"},
                "Parameter_units": {"A": "MPa/K", "dH_diss": "J/mol", "dS_diss": "J/(mol K)"},
                "Params": {"A": popt[0], "dH_diss": popt[1], "dS_diss": popt[2]},
                "Plot": {"x": 1000.0 / T_K, "y": G0s, "y_pred": pred}
            }
        except Exception as e:
            print(f"Van 't Hoff fit failed: {e}")
            return None

    def fit_vft(self, temps_C, taus):
        """
        Fits ln(tau) = A + B / (T - T0)
        """
        inputs = _validated_inputs(temps_C, taus, 4)
        if inputs is None:
            return None
        T_K, taus = inputs
        ln_tau = np.log(taus)

        def vft_func(T, A, B, T0):
            return A + B / (T - T0)
        
        # Bounds: T0 must be below min(T_K)
        try:
            p0 = [-10, 1000, T_K.min() - 50]
            bounds = ([-np.inf, 0, 0], [np.inf, np.inf, T_K.min() - 1])
            popt, _ = curve_fit(vft_func, T_K, ln_tau, p0=p0, bounds=bounds, maxfev=5000)
            
            # Calc R2
            pred = vft_func(T_K, *popt)
            if not np.all(np.isfinite(popt)) or not np.all(np.isfinite(pred)):
                return None
            ss_res = np.sum((ln_tau - pred)**2)
            ss_tot = np.sum((ln_tau - np.mean(ln_tau))**2)
            r2 = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 0.0
            
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
        inputs = _validated_inputs(temps_C, taus, 5 if Tg is not None else 6)
        if inputs is None:
            return None
        T_K, taus = inputs
        ln_tau = np.log(taus)
        if Tg is not None:
            try:
                Tg = float(Tg)
            except (TypeError, ValueError):
                return None
            if not np.isfinite(Tg) or Tg <= -273.15:
                return None

        if Tg is not None:
            T0_val = 273.15 + (Tg - 50.0)
            # Ensure T0 is at least 5K below minimum experimental temperature
            T0_val = min(T0_val, T_K.min() - 5.0)
            
            def coupled_fixed_T0(T, ln_A, Ea, ln_C, B):
                return predict_coupled(T, ln_A, Ea, ln_C, B, T0_val)

            try:
                # Guesses: ln_A (chem), Ea (chem), ln_C (glass), B (glass VFT)
                p0 = [np.log(min(taus)) - 10, 80000.0, np.log(max(taus)), 1500.0]
                bounds = (
                    [-50.0, 1000.0, -50.0, 100.0],
                    [50.0, 300000.0, 50.0, 20000.0]
                )
                popt, _ = curve_fit(coupled_fixed_T0, T_K, ln_tau, p0=p0, bounds=bounds, maxfev=5000)
                pred = coupled_fixed_T0(T_K, *popt)
                if not np.all(np.isfinite(popt)) or not np.all(np.isfinite(pred)):
                    return None

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
                return predict_coupled(T, ln_A, Ea, ln_C, B, T0)

            try:
                p0 = [np.log(min(taus)) - 10, 80000.0, np.log(max(taus)), 1500.0, T_K.min() - 50.0]
                bounds = (
                    [-50.0, 1000.0, -50.0, 100.0, 100.0],
                    [50.0, 300000.0, 50.0, 20000.0, T_K.min() - 2.0]
                )
                popt, _ = curve_fit(coupled_free_T0, T_K, ln_tau, p0=p0, bounds=bounds, maxfev=10000)
                pred = coupled_free_T0(T_K, *popt)
                if not np.all(np.isfinite(popt)) or not np.all(np.isfinite(pred)):
                    return None

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