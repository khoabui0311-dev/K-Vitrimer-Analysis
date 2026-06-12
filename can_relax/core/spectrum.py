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

    def compute_continuous_spectrum(self, t, g, num_modes=50, alpha=0.1, optimize_alpha=False, subtract_G_eq=True):
        """
        Calculates H(tau) using Tikhonov Regularization (Ridge Regression).
        t: Time array (s)
        g: Modulus array (normalized G/G0 or absolute G)
        num_modes: Number of tau bins (resolution)
        alpha: Regularization strength (smoothness factor, ignored if optimize_alpha=True)
        optimize_alpha: If True, uses the L-curve corner method to find the optimal alpha.
        subtract_G_eq: If True, detects and subtracts the non-zero equilibration modulus tail value.
        """
        # 1. Detect and subtract G_eq (equilibration modulus tail)
        if subtract_G_eq:
            # Average of last 5% of data points as equilibration modulus
            tail_len = max(1, len(g) // 20)
            G_eq = float(max(0.0, np.mean(g[-tail_len:])))
            # Keep G_eq reasonable (not exceeding 90% of the initial modulus)
            if G_eq > g[0] * 0.9:
                G_eq = 0.0
            g_offset = g - G_eq
            # Normalize to the initial offset value for stable inversion
            G_init_offset = g_offset[0]
            if G_init_offset > 0.01:
                g_target = g_offset / G_init_offset
            else:
                g_target = g_offset
        else:
            G_eq = 0.0
            G_init_offset = 1.0
            g_target = g
            
        self.last_G_eq = G_eq
        self.last_G_init_offset = G_init_offset

        # 2. Define Tau Grid (Logarithmically spaced)
        tau_min = t.min() / 2.0
        tau_max = t.max() * 5.0
        tau_grid = np.logspace(np.log10(tau_min), np.log10(tau_max), num_modes)
        
        # 3. Build Kernel Matrix A_ij = exp(-t_i / tau_j)
        A = np.exp(-t[:, None] / tau_grid[None, :])
        
        # 4. Solve Inverse Problem with Regularization (Ridge with positive=True constraint)
        if optimize_alpha:
            alpha_grid = np.logspace(-5, 2, 40)
            residual_norms = []
            solution_norms = []
            H_grid = []
            
            for a in alpha_grid:
                solver = Ridge(alpha=a, positive=True, fit_intercept=False)
                solver.fit(A, g_target)
                H_val = solver.coef_
                
                # Solution norm ||H||_2
                sol_norm = np.linalg.norm(H_val)
                # Residual norm ||A*H - g_target||_2
                res_norm = np.linalg.norm(A.dot(H_val) - g_target)
                
                residual_norms.append(res_norm)
                solution_norms.append(sol_norm)
                H_grid.append(H_val)
                
            # Log-log coordinate transform for L-curve corner detection
            log_res = np.log10(np.array(residual_norms) + 1e-15)
            log_sol = np.log10(np.array(solution_norms) + 1e-15)
            
            # Use geometric maximum distance method (secant line distance)
            x1, y1 = log_res[0], log_sol[0]
            xN, yN = log_res[-1], log_sol[-1]
            
            best_idx = 0
            max_dist = -1.0
            
            a_coef = yN - y1
            b_coef = -(xN - x1)
            c_coef = xN * y1 - yN * x1
            denom = np.sqrt(a_coef**2 + b_coef**2)
            
            if denom > 1e-12:
                for idx in range(len(alpha_grid)):
                    dist = abs(a_coef * log_res[idx] + b_coef * log_sol[idx] + c_coef) / denom
                    if dist > max_dist:
                        max_dist = dist
                        best_idx = idx
            
            best_alpha = alpha_grid[best_idx]
            H_values = H_grid[best_idx]
            self.last_alpha = best_alpha
        else:
            solver = Ridge(alpha=alpha, positive=True, fit_intercept=False)
            solver.fit(A, g_target)
            H_values = solver.coef_
            self.last_alpha = alpha
            
        return tau_grid, H_values

    def get_weighted_avg_tau(self, tau_grid, H_values):
        """Calculates the dominant relaxation time from the spectrum."""
        if np.sum(H_values) == 0: return 0
        # Weighted log average
        log_tau = np.log10(tau_grid)
        avg_log_tau = np.average(log_tau, weights=H_values)
        return 10**avg_log_tau