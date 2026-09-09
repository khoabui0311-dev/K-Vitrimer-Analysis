"""Synthetic relaxation anchored to a Maxwell-equivalent threshold."""
import numpy as np
from can_relax.core.kinetics import R_GAS


class MaterialSimulator:
    def simulate_curve(self, T, model_name, p):
        """Return elapsed time, absolute modulus (MPa), and primary-mode tau.

        Tv anchors G*tau=10^12 Pa s for the primary mode. For KWW/dual KWW
        it is a characteristic-time convention, not a total-viscosity threshold.
        """
        if model_name not in ('Maxwell', 'Single_KWW', 'Dual_KWW'):
            raise ValueError(f"Model '{model_name}' is not implemented in the simulator.")
        temperature, anchor = float(T) + 273.15, float(p['Tv']) + 273.15
        modulus, energy = float(p['G_plateau']), float(p['Ea'])
        if (not np.isfinite([temperature, anchor, modulus, energy]).all()
                or min(temperature, anchor, modulus) <= 0 or energy < 0):
            raise ValueError('Require finite physical temperatures, positive modulus and nonnegative Ea.')

        def mode_time(ea, factor=1.):
            if not np.isfinite([ea, factor]).all() or ea < 0 or factor <= 0:
                raise ValueError('Mode energy must be nonnegative and separation factor positive.')
            log_tau = np.log(1e6) - np.log(modulus) + np.log(factor) + ea*1000/R_GAS*(1/temperature-1/anchor)
            if not np.isfinite(log_tau) or not -680 < log_tau < 680:
                raise ValueError('Relaxation time exceeds the numerical simulation range.')
            return np.exp(log_tau)

        def beta(value):
            if not np.isfinite(value) or not 0 < value <= 1:
                raise ValueError('KWW beta must lie in (0, 1].')
            return value

        tau = mode_time(energy)
        tau2 = tau
        if model_name == 'Dual_KWW':
            tau2 = mode_time(float(p.get('Ea_2', energy)), float(p.get('tau_factor', 10.)))
            fraction = float(p.get('fraction_fast', .5))
            if not np.isfinite(fraction) or not 0 <= fraction <= 1:
                raise ValueError('Mode fraction must lie in [0, 1].')
        t = np.geomspace(min(tau, tau2)*1e-3, max(tau, tau2)*100, 200)
        with np.errstate(over='ignore', under='ignore'):
            if model_name == 'Maxwell':
                g = modulus * np.exp(-t/tau)
            elif model_name == 'Single_KWW':
                g = modulus * np.exp(-(t/tau)**beta(p['beta']))
            else:
                g = modulus*(fraction*np.exp(-(t/tau)**beta(p['beta'])) +
                             (1-fraction)*np.exp(-(t/tau2)**beta(p.get('beta_2', p['beta']))))
        if not np.isfinite(t).all() or not np.isfinite(g).all():
            raise ValueError('Nonfinite simulation output.')
        return t, g, tau
