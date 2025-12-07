# -*- coding: utf-8 -*-
"""
Created on Sat Dec  6 14:03:52 2025

@author: khoab
"""

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge, Lasso
from scipy.interpolate import interp1d

class SpectrumAnalyzer:
    def __init__(self):
        pass

    def compute_continuous_spectrum(self, t, g, num_modes=100, alpha=0.1):
        """
        Calculates H(tau) using Tikhonov Regularization (Ridge Regression).
        t: Time array (s)
        g: Modulus array (normalized G/G0)
        num_modes: Number of tau bins (resolution)
        alpha: Regularization strength (smoothness factor)
        """
        # 1. Define Tau Grid (Logarithmically spaced)
        # Range: slightly wider than experimental time window
        tau_min = t.min() / 2
        tau_max = t.max() * 5
        tau_grid = np.logspace(np.log10(tau_min), np.log10(tau_max), num_modes)
        
        # 2. Build Kernel Matrix (The "Dictionary")
        # G(t) ~ Sum [ H_i * exp(-t/tau_i) ]
        # A_ij = exp(-t_i / tau_j)
        A = np.exp(-t[:, None] / tau_grid[None, :])
        
        # 3. Solve Inverse Problem with Regularization (Ridge)
        # Minimize ||Ag - H||^2 + alpha * ||H||^2
        # Constraint: H >= 0 (Positive coeff only allows physical relaxation)
        
        # Using Lasso (L1) for sparsity or Ridge (L2) for smoothness. 
        # Ridge is better for continuous spectra.
        # We use positive=True to enforce physics.
        solver = Ridge(alpha=alpha, positive=True, fit_intercept=False)
        solver.fit(A, g)
        
        H_values = solver.coef_
        
        return tau_grid, H_values

    def get_weighted_avg_tau(self, tau_grid, H_values):
        """Calculates the dominant relaxation time from the spectrum."""
        if np.sum(H_values) == 0: return 0
        # Weighted log average
        log_tau = np.log10(tau_grid)
        avg_log_tau = np.average(log_tau, weights=H_values)
        return 10**avg_log_tau