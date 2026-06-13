import numpy as np

class MaterialSimulator:
    def simulate_curve(self, T, model_name, p):
        """Simulate a relaxation curve at temperature T"""
        R = 8.314
        try:
            tau_v = 1e6 / p['G_plateau'] 
            term_tv = np.exp((p['Ea']*1000/R) * (1/(p['Tv']+273.15)))
            tau0 = tau_v / term_tv
            term_t = np.exp((p['Ea']*1000/R) * (1/(T+273.15)))
            tau_T = tau0 * term_t
            t = np.logspace(np.log10(tau_T)-3, np.log10(tau_T)+2, 100)
            
            if model_name == 'Maxwell':
                g = p['G_plateau'] * np.exp(-t/tau_T)
            elif model_name == 'Single_KWW':
                g = p['G_plateau'] * np.exp(-(t/tau_T)**p['beta'])
            else: g = t*0
            
            return t, g, tau_T
        except Exception as e:
            raise ValueError(f"Simulation math error: {str(e)}") from e
