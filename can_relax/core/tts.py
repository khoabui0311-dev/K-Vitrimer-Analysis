# -*- coding: utf-8 -*-
"""
Created on Thu Dec  4 15:33:24 2025

@author: khoab
"""

import numpy as np
from scipy.interpolate import interp1d

class TTSEngine:
    def __init__(self):
        pass

    def generate_mastercurve(self, results, ref_temp=None):
        """
        Shifts curves horizontally to create a Mastercurve.
        Shift Factor a_T = tau(T) / tau(T_ref)
        """
        if not results: return None
        
        # 1. Sort results by Temperature
        sorted_res = sorted(results, key=lambda x: x['Temp'])
        
        # 2. Pick Reference Temperature (middle temp usually best, or user defined)
        if ref_temp is None:
            # Default to the one in the middle
            mid_idx = len(sorted_res) // 2
            ref_res = sorted_res[mid_idx]
        else:
            # Find closest
            ref_res = min(sorted_res, key=lambda x: abs(x['Temp'] - ref_temp))
            
        T_ref = ref_res['Temp']
        
        # Get Ref Tau (from the Best Model fit)
        # We need a robust Tau. Let's extract Tau from the fit parameters.
        def get_tau(res):
            best = res['Best_Model']
            popt = res['Fits'][best]['popt']
            if best == 'Maxwell': return popt[1]
            if best == 'Single_KWW': return popt[1]
            if best == 'Dual_KWW': return popt[2] # Tau1 (fast) usually dominates shift
            return 1.0

        tau_ref = get_tau(ref_res)
        
        master_t = []
        master_g = []
        shift_factors = {}
        
        for res in sorted_res:
            T = res['Temp']
            tau = get_tau(res)
            
            # Calculate Shift Factor a_T
            aT = tau / tau_ref
            shift_factors[T] = aT
            
            # Shift Time: t_master = t / aT
            # Logarithmic shift: log(t) - log(aT)
            t_shifted = res['Raw']['t'] / aT
            g_raw = res['Raw']['g']
            
            master_t.append(t_shifted)
            master_g.append(g_raw)
            
        # Concatenate
        full_t = np.concatenate(master_t)
        full_g = np.concatenate(master_g)
        
        # Sort for plotting
        sort_idx = np.argsort(full_t)
        
        return {
            "T_ref": T_ref,
            "Master_t": full_t[sort_idx],
            "Master_g": full_g[sort_idx],
            "Shifts": shift_factors
        }