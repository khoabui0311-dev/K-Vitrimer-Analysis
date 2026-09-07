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

    def generate_mastercurve(self, results, ref_temp=None, ref_curve_id=None):
        """
        Shifts curves horizontally to create a Mastercurve.
        Shift Factor a_T = tau(T) / tau(T_ref)
        Average all replicates at ref_temp unless ref_curve_id explicitly selects one.
        """
        if not results: return None
        for res in results:
            fit = res.get('Fits', {}).get(res.get('Best_Model'), {})
            if not res.get('Valid', False) or not fit.get('success', False):
                raise ValueError('Mastercurve requires successful fits for every selected curve')
            if not np.all(np.isfinite(fit['popt'])):
                raise ValueError('Mastercurve requires finite parameters')

        # 1. Sort results by Temperature
        sorted_res = sorted(results, key=lambda x: x['Temp'])

        # 2. Pick Reference Temperature (middle temp usually best, or user defined)
        if ref_temp is None and ref_curve_id is None:
            # Default to the one in the middle
            mid_idx = len(sorted_res) // 2
            ref_temp = sorted_res[mid_idx]['Temp']

        T_ref = ref_temp

        # Get Ref Tau (from the Best Model fit)
        # We need a robust Tau. Let's extract Tau from the fit parameters.
        def get_tau(res):
            best = res['Best_Model']
            popt = res['Fits'][best]['popt']
            if best == 'Maxwell': return popt[0]
            if best == 'Single_KWW': return popt[0]
            # Dual_KWW: popt = [A, tau1, beta1, tau2, beta2]
            # We use tau2 (slow mode, index 3) as the canonical network exchange time.
            # tau1 is guaranteed < tau2 after the label-switching fix in analyzer.py.
            # This is consistent with the Kinetics tab which also uses popt[3].
            if best == 'Dual_KWW': return popt[3]
            raise ValueError('Unknown relaxation model')

        if ref_curve_id is not None:
            ref_results = [r for r in sorted_res if r.get('Curve_ID') == ref_curve_id]
            if len(ref_results) != 1:
                raise ValueError('Reference curve ID must identify exactly one selected curve')
            if ref_temp is not None and ref_results[0]['Temp'] != ref_temp:
                raise ValueError('Reference curve does not match the reference temperature')
            T_ref = ref_results[0]['Temp']
        else:
            ref_results = [r for r in sorted_res if r['Temp'] == T_ref]
        if not ref_results:
            raise ValueError(f'Reference temperature {T_ref} not found in results')

        tau_refs = [get_tau(r) for r in ref_results]
        if any(tau <= 0 or not np.isfinite(tau) for tau in tau_refs):
            raise ValueError('Every reference relaxation time must be finite and positive')
        tau_ref = float(np.mean(tau_refs))

        if tau_ref <= 0 or not np.isfinite(tau_ref):
            raise ValueError('Reference relaxation time must be finite and positive')

        master_t = []
        master_g = []
        shift_factors = {}

        for res in sorted_res:
            T = res['Temp']
            tau = get_tau(res)
            if tau <= 0 or not np.isfinite(tau):
                raise ValueError('Relaxation times must be finite and positive')

            # Calculate Shift Factor a_T
            aT = tau / tau_ref
            curve_id = res.get('Curve_ID', str(T))
            if curve_id in shift_factors:
                raise ValueError('Each replicate must have a unique curve identifier')
            shift_factors[curve_id] = aT

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
            "Tau_ref": tau_ref,
            "Reference_mode": 'curve' if ref_curve_id is not None else 'arithmetic_mean',
            "Reference_curve_ids": [r.get('Curve_ID', str(r['Temp'])) for r in ref_results],
            "Master_t": full_t[sort_idx],
            "Master_g": full_g[sort_idx],
            "Shifts": shift_factors
        }
