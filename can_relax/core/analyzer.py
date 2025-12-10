import numpy as np
import pandas as pd
from scipy.optimize import curve_fit
from can_relax.core.models import Maxwell, SingleKWW, DualKWW
from can_relax.core.processing import DataProcessor
from can_relax.core.auto_engine import AutoEngine

class CurveAnalyzer:
    def __init__(self):
        self.processor = DataProcessor()
        self.auto = AutoEngine()
        self.models = {
            'Maxwell': Maxwell(),
            'Single_KWW': SingleKWW(),
            'Dual_KWW': DualKWW()
        }

    def _calculate_metrics(self, g_true, g_pred, n_params):
        rss = np.sum((g_true - g_pred)**2)
        n = len(g_true)
        ss_tot = np.sum((g_true - np.mean(g_true))**2)
        r2 = 1 - (rss / ss_tot) if ss_tot > 0 else 0
        rss = max(rss, 1e-15)
        aic = 2 * n_params + n * np.log(rss/n)
        if n > n_params + 1:
            aicc = aic + (2 * n_params * (n_params + 1)) / (n - n_params - 1)
        else:
            aicc = np.inf
        return r2, aicc

    def fit_one_temp(self, temp, df_raw, Tg=None):
        """
        Runs analysis for one temperature.
        If Tg is provided and temp < Tg, returns a 'Frozen' status.
        """
        # --- PHYSICS BARRIER CHECK ---
        if Tg is not None:
            if temp < Tg:
                return {
                    'Temp': temp,
                    'Valid': False,
                    'Reason': 'GLASSY / FROZEN (Below Tg)',
                    'Auto_Explanation': f"Temperature ({temp}°C) is below Tg ({Tg}°C). Material is glassy; no relaxation flow expected."
                }
        
        t_raw = df_raw['Time'].values
        g_raw = df_raw['Modulus'].values
        
        # 1. Processing
        t, g, G0 = self.processor.trim_curve(t_raw, g_raw)
        if t is None: 
            return {'Temp': temp, 'Valid': False, 'Reason': 'Data Quality (Too short/noisy)'}

        result = {
            'Temp': temp,
            'Valid': True,
            'Raw': {'t': t, 'g': g, 'G0': G0},
            'Fits': {}
        }
        
        # 2. Quality Check
        quality = self.auto.compute_signal_quality(t, g)
        result['Quality'] = quality

        # 3. Fit Models
        # Single KWW
        model_s = self.models['Single_KWW']
        try:
            popt_s, _ = curve_fit(model_s.func, t, g, p0=model_s.get_initial_guess(t, g), bounds=model_s.get_bounds(), maxfev=5000)
            pred_s = model_s.func(t, *popt_s)
            r2_s, aic_s = self._calculate_metrics(g, pred_s, 2)  # 2 params: tau, beta
            result['Fits']['Single_KWW'] = {'popt': popt_s, 'r2': r2_s, 'aic': aic_s, 'curve': pred_s}
        except: result['Fits']['Single_KWW'] = {'r2': 0, 'aic': np.inf, 'curve': g, 'popt': [np.nan, np.nan]}

        # Maxwell
        model_m = self.models['Maxwell']
        try:
            popt_m, _ = curve_fit(model_m.func, t, g, p0=model_m.get_initial_guess(t, g), bounds=model_m.get_bounds(), maxfev=5000)
            pred_m = model_m.func(t, *popt_m)
            r2_m, aic_m = self._calculate_metrics(g, pred_m, 1)  # 1 param: tau
            result['Fits']['Maxwell'] = {'popt': popt_m, 'r2': r2_m, 'aic': aic_m, 'curve': pred_m}
        except: result['Fits']['Maxwell'] = {'r2': 0, 'aic': np.inf, 'curve': g, 'popt': [np.nan]}

        # Dual KWW
        model_d = self.models['Dual_KWW']
        try:
            p0_d = model_d.get_initial_guess(t, g, popt_s)
            popt_d, _ = curve_fit(model_d.func, t, g, p0=p0_d, bounds=model_d.get_bounds(), maxfev=10000)
            pred_d = model_d.func(t, *popt_d)
            r2_d, aic_d = self._calculate_metrics(g, pred_d, 5)  # 5 params: A, tau1, beta1, tau2, beta2
            result['Fits']['Dual_KWW'] = {'popt': popt_d, 'r2': r2_d, 'aic': aic_d, 'curve': pred_d}
        except: result['Fits']['Dual_KWW'] = {'r2': 0, 'aic': np.inf, 'curve': g, 'popt': [np.nan]*5}

        # 4. Pick Best
        best_model = min(result['Fits'], key=lambda k: result['Fits'][k]['aic'])
        result['Best_Model'] = best_model
        
        # 5. Auto Explanation (With WLF Warning)
        best_r2 = result['Fits'][best_model]['r2']
        explanation = self.auto.generate_explanation(temp, best_model, best_r2, quality)
        
        if Tg is not None and (Tg <= temp < Tg + 20):
            explanation += "\n\n⚠️ **Note:** Temperature is near Tg. Dynamics may follow WLF (super-Arrhenius) rather than pure Arrhenius."
            
        result['Auto_Explanation'] = explanation
        
        return result