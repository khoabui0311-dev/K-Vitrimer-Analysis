import numpy as np
from scipy.stats import linregress
from scipy.optimize import curve_fit

R_GAS = 8.314462  # J/mol*K

class KineticsEngine:
    def __init__(self):
        pass

    def fit_arrhenius(self, temps_C, taus):
        """
        Fits ln(tau) = ln(tau0) + Ea / (R * T)
        Returns: Ea (kJ/mol), R2, and fit curve.
        """
        if len(temps_C) < 3: return None

        T_K = np.array(temps_C) + 273.15
        inv_T = 1000.0 / T_K
        ln_tau = np.log(np.array(taus))

        # Linear regression: ln(tau) = slope * (1000/T) + intercept
        slope, intercept, r_val, _, _ = linregress(inv_T, ln_tau)
        
        # Ea = slope * R * 1000 (because we used 1000/T) -> No wait
        # Formula: ln(tau) = (Ea/R) * (1/T)
        # Our X is 1000/T. So slope = (Ea/R)/1000. 
        # Actually simplest way: slope of ln(tau) vs 1/T is Ea/R.
        
        # Let's redo with standard 1/T for clarity
        inv_T_standard = 1.0 / T_K
        slope_std, intercept_std, r_std, _, _ = linregress(inv_T_standard, ln_tau)
        
        Ea_J = slope_std * R_GAS
        Ea_kJ = Ea_J / 1000.0
        
        return {
            "Type": "Arrhenius",
            "Ea": Ea_kJ,
            "R2": r_std**2,
            "Params": {"slope": slope_std, "intercept": intercept_std},
            "Plot": {"x": inv_T_standard, "y": ln_tau, "y_pred": slope_std*inv_T_standard + intercept_std}
        }

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