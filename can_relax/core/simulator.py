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
            elif model_name == 'Dual_KWW':
                # Fast mode uses primary Ea; slow mode uses Ea_2 and a tau_factor multiplier
                Ea_2 = p.get('Ea_2', p['Ea'])
                term_tv2 = np.exp((Ea_2*1000/R) * (1/(p['Tv']+273.15)))
                tau0_2 = tau_v / term_tv2
                term_t2 = np.exp((Ea_2*1000/R) * (1/(T+273.15)))
                tau_T2 = tau0_2 * term_t2 * p.get('tau_factor', 10.0)
                beta1 = p['beta']
                beta2 = p.get('beta_2', p['beta'])
                frac = p.get('fraction_fast', 0.5)
                g = p['G_plateau'] * (
                    frac * np.exp(-(t / tau_T) ** beta1) +
                    (1.0 - frac) * np.exp(-(t / tau_T2) ** beta2)
                )
            else:
                raise NotImplementedError(f"Model '{model_name}' is not implemented in the simulator.")
            
            return t, g, tau_T
        except Exception as e:
            raise ValueError(f"Simulation math error: {str(e)}") from e

