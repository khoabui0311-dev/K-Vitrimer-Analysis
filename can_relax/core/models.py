import numpy as np

class Maxwell:
    def func(self, t, tau):
        # Safety: Prevent division by zero
        tau = max(tau, 1e-12)
        # Data is pre-normalized, so G0=1.0
        return np.exp(-(t / tau))

    def get_initial_guess(self, t, g):
        # Estimate tau where g drops to 1/e
        idx = (np.abs(g - 0.368)).argmin()
        tau_guess = t[idx] if idx < len(t) else t[-1]
        return [tau_guess]

    def get_bounds(self):
        # Tau only (data is pre-normalized)
        return ([1e-9], [1e12])

class SingleKWW:
    def func(self, t, tau, beta):
        # Safety: Take abs(t) to prevent negative power errors during fitting
        t_safe = np.abs(t)
        tau = max(tau, 1e-12)
        # Data is pre-normalized, so G0=1.0
        return np.exp(-((t_safe / tau) ** beta))

    def get_initial_guess(self, t, g):
        idx = (np.abs(g - 0.368)).argmin()
        tau_guess = t[idx] if idx < len(t) else t[-1]
        return [tau_guess, 0.5] # tau, beta

    def get_bounds(self):
        return ([1e-9, 0.1], [1e12, 1.0])

class DualKWW:
    def func(self, t, A, tau1, beta1, tau2, beta2):
        t_safe = np.abs(t)
        tau1 = max(tau1, 1e-12)
        tau2 = max(tau2, 1e-12)
        
        term1 = A * np.exp(-((t_safe / tau1) ** beta1))
        term2 = (1 - A) * np.exp(-((t_safe / tau2) ** beta2))
        # Data is pre-normalized, so G0=1.0
        return term1 + term2

    def get_initial_guess(self, t, g):
        # Guess: Tau1 is early, Tau2 is late
        tau1 = t[len(t)//4]
        tau2 = t[3*len(t)//4]
        return [0.5, tau1, 0.8, tau2, 0.5]

    def get_bounds(self):
        # A, tau1, beta1, tau2, beta2 (no G0)
        return (
            [0.0, 1e-9, 0.1, 1e-9, 0.1], 
            [1.0, 1e12, 1.0, 1e12, 1.0]
        )