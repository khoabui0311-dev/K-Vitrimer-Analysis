import numpy as np


PRONY = 'Two-Maxwell (Prony)'
TAU_INDICES = {'Maxwell': (0,), 'Single_KWW': (0,), 'Dual_KWW': (1, 3), PRONY: (1, 2)}


def prony_log_decay(t, fraction, tau_fast, tau_slow):
    with np.errstate(divide='ignore'):
        return np.logaddexp(np.log(fraction) - t/tau_fast,
                            np.log1p(-fraction) - t/tau_slow)


class TwoMaxwell:
    """Two parallel Maxwell arms; fraction is of relaxing modulus at loading."""

    def func(self, t, fraction, tau_fast, tau_slow):
        return np.exp(prony_log_decay(np.asarray(t), fraction, tau_fast, tau_slow))

    def get_initial_guess(self, t, g):
        # Seed on decay levels, not row indices (sampling may be linear or logarithmic).
        dt = t - t[0]
        positive = dt[dt > 0]
        if not len(positive):
            raise ValueError('Two Maxwell modes require a nonzero measurement window.')
        lo = positive[0]
        fast = max(lo, dt[np.argmin(np.abs(g - .85))])
        slow = max(3 * fast, dt[np.argmin(np.abs(g - .2))])
        return [.5, np.clip(fast, 1e-9, 1e12), np.clip(slow, 1e-9, 1e12)]

    def get_bounds(self):
        return ([0., 1e-9, 1e-9], [1., 1e12, 1e12])


def conditional_relaxation(name, t, params, reference_time):
    """Predict G(t)/G(reference_time) in log space without resetting physical time."""
    t = np.asarray(t, dtype=float)
    def log_decay(x):
        if name == PRONY:
            return prony_log_decay(x, *params)
        if name == 'Maxwell':
            return -x / params[0]
        if name == 'Single_KWW':
            return -(x / params[0]) ** params[1]
        if name == 'Dual_KWW':
            A, tau1, beta1, tau2, beta2 = params
            with np.errstate(divide='ignore'):
                return np.logaddexp(np.log(A) - (x/tau1)**beta1,
                                    np.log1p(-A) - (x/tau2)**beta2)
        raise ValueError('Unknown relaxation model')
    return np.exp(log_decay(t) - log_decay(np.asarray(reference_time)))

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
