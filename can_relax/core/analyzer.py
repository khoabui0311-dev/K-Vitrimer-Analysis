import numpy as np
import pandas as pd
from scipy.optimize import curve_fit
from typing import Dict, Any, Tuple, Optional
from can_relax.core.models import Maxwell, SingleKWW, DualKWW
from can_relax.core.processing import DataProcessor
from can_relax.core.auto_engine import AutoEngine

class CurveAnalyzer:
    def __init__(self) -> None:
        self.processor = DataProcessor()
        self.auto = AutoEngine()
        self.models = {
            'Maxwell': Maxwell(),
            'Single_KWW': SingleKWW(),
            'Dual_KWW': DualKWW()
        }

    def _calculate_metrics(self, g_true: np.ndarray, g_pred: np.ndarray, n_params: int) -> Tuple[float, float, float]:
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
        bic = n_params * np.log(n) + n * np.log(rss/n)
        return float(r2), float(aicc), float(bic)

    def fit_one_temp(self, temp: float, df_raw: pd.DataFrame, Tg: Optional[float] = None, fit_model: Optional[str] = None,
                     plateau_mode: str = 'Zero', fixed_plateau: float = 0.0) -> Dict[str, Any]:
        """
        Runs analysis for one temperature.
        If Tg is provided and temp < Tg, returns a 'Frozen' status.
        """
        if plateau_mode not in ('Zero', 'Fit', 'Fixed'):
            raise ValueError('Unknown plateau mode')
        if plateau_mode != 'Zero' and fit_model not in ('Maxwell', 'Single_KWW'):
            raise ValueError('Plateau fitting requires Maxwell or Single_KWW')
        if plateau_mode == 'Fixed' and (not np.isfinite(fixed_plateau) or fixed_plateau < 0):
            raise ValueError('Fixed plateau must be finite and nonnegative (MPa)')
        # --- PHYSICS BARRIER CHECK ---
        if Tg is not None:
            if temp < Tg:
                return {
                    'Temp': temp,
                    'Valid': False,
                    'Reason': 'GLASSY / FROZEN (Below Tg)',
                    'Auto_Explanation': f"Temperature ({temp}°C) is below Tg ({Tg}°C). Excluded by the selected below-Tg analysis policy."
                }
        
        t_raw = df_raw['Time'].values
        g_raw = df_raw['Modulus'].values
        
        # 1. Processing
        t_full, g_full, G0 = self.processor.trim_curve(t_raw, g_raw, max_points=None)
        if t_full is None:
            return {'Temp': temp, 'Valid': False, 'Reason': 'Data Quality (Too short/noisy)'}
        t, g = self.processor.downsample(t_full, g_full)
        if plateau_mode == 'Fixed' and fixed_plateau >= G0:
            return {'Temp': temp, 'Valid': False, 'Reason': 'Fixed plateau must be below the retained reference modulus'}

        result = {
            'Temp': temp,
            'Valid': True,
            'Raw': {'t': t, 'g': g, 'G0': G0, 'full_t': t_full, 'full_g': g_full},
            'Fits': {}
        }
        
        # 2. Quality Check
        quality = self.auto.compute_signal_quality(t, g)
        result['Quality'] = quality

        # Fit the measured ratio f(t)/f(t_ref), preserving the loading origin.
        from can_relax.core.models import conditional_relaxation
        models_to_fit = [fit_model] if fit_model is not None else list(self.models)
        if any(name not in self.models for name in models_to_fit):
            raise ValueError("Unknown relaxation model")
        result['Preprocessing'] = {
            'time_origin': 'elapsed_since_loading', 'reference_time': float(t[0]),
            'reference_modulus': G0, 'input_points': len(df_raw), 'retained_points': len(t),
            'retained_points_before_downsampling': len(t_full),
            'plateau_mode': plateau_mode, 'fixed_plateau_MPa': fixed_plateau if plateau_mode == 'Fixed' else None,
        }
        result['Warnings'] = []
        if t[0] > 0:
            result['Warnings'].append('Fit uses a retained-reference ratio; G0 is the observed reference modulus, not an inferred plateau.')
        for name in models_to_fit:
            model = self.models[name]
            n_params = len(model.get_initial_guess(t, g))
            base_count = n_params
            if plateau_mode == 'Fit':
                n_params += 1
            def prediction(x, *params):
                # q = G_inf / G(reference), not G_inf / G(0).
                q = params[-1] if plateau_mode == 'Fit' else (fixed_plateau / G0 if plateau_mode == 'Fixed' else 0.0)
                return q + (1-q) * conditional_relaxation(name, x, params[:base_count], t[0])
            try:
                guess = np.maximum(model.get_initial_guess(t, g), np.asarray(model.get_bounds()[0]) + 1e-8)
                bounds = model.get_bounds()
                if plateau_mode == 'Fit':
                    guess = np.r_[guess, np.clip(g[-1] * .8, .001, .95)]
                    bounds = (list(bounds[0]) + [0.0], list(bounds[1]) + [1.0 - 1e-9])
                popt, covariance = curve_fit(prediction, t, g, p0=guess,
                    bounds=bounds, maxfev=15000, x_scale='jac')
                if name == 'Dual_KWW' and popt[1] > popt[3]:
                    A, tau1, beta1, tau2, beta2 = popt
                    popt = np.array([1-A, tau2, beta2, tau1, beta1])
                    # Covariance ordering is transformed with the same mode permutation.
                    jac = np.zeros((5, 5)); jac[0, 0] = -1
                    jac[1, 3] = jac[2, 4] = jac[3, 1] = jac[4, 2] = 1
                    covariance = jac @ covariance @ jac.T
                pred = prediction(t, *popt)
                if not np.all(np.isfinite(popt)) or not np.all(np.isfinite(pred)):
                    raise ValueError('Nonfinite fit parameters or predictions')
                r2, aicc, bic = self._calculate_metrics(g, pred, n_params)
                q = float(popt[-1]) if plateau_mode == 'Fit' else (fixed_plateau/G0 if plateau_mode == 'Fixed' else 0.0)
                flags = []
                taus = [popt[1], popt[3]] if name == 'Dual_KWW' else [popt[0]]
                if any(tau < t[0] or tau > t[-1] for tau in taus):
                    flags.append('Tau outside measurement window; review before kinetics.')
                errors = np.sqrt(np.maximum(np.diag(covariance), 0))
                tau_indices = [1, 3] if name == 'Dual_KWW' else [0]
                if any(not np.isfinite(errors[i]) or errors[i] > .5*popt[i] for i in tau_indices):
                    flags.append('Tau has large local fit uncertainty.')
                if name == 'Dual_KWW' and min(popt[0], 1-popt[0]) < .05:
                    flags.append('Dual-KWW component below 5% amplitude; its time may be unresolved.')
                if plateau_mode == 'Fit':
                    if not np.isfinite(errors[-1]) or errors[-1] > .05:
                        flags.append('Plateau is poorly constrained by local fit uncertainty.')
                    if pred[-1] - q > .05*(1-q):
                        flags.append('Fitted plateau has not been approached within the measurement window.')
                result['Fits'][name] = {'success': True, 'popt': popt[:base_count], 'r2': r2,
                    'aic': aicc, 'bic': bic, 'curve': pred, 'covariance': covariance[:base_count, :base_count],
                    'full_covariance': covariance, 'n_params': n_params, 'residuals': g-pred,
                    'plateau_mode': plateau_mode, 'G_inf': q*G0,
                    'G_inf_std': float(errors[-1]*G0) if plateau_mode == 'Fit' else None,
                    'flags': flags}
            except (RuntimeError, ValueError, FloatingPointError) as exc:
                result['Fits'][name] = {'success': False, 'error': str(exc),
                    'r2': np.nan, 'aic': np.inf, 'bic': np.inf,
                    'curve': np.full_like(g, np.nan), 'popt': np.full(n_params, np.nan)}
        successful = [name for name, fit in result['Fits'].items() if fit['success']]
        if not successful:
            result.update(Valid=False, Best_Model=None, Reason='All requested fits failed',
                          Auto_Explanation='No successful fit; excluded from downstream analysis.')
            return result
        best_model = min(successful, key=lambda name: result['Fits'][name]['aic'])
        result['Best_Model'] = best_model
        result['Warnings'].extend(result['Fits'][best_model]['flags'])
        params = result['Fits'][best_model]['popt']
        taus = [params[1], params[3]] if best_model == 'Dual_KWW' else [params[0]]
        if any(tau < t[0] or tau > t[-1] for tau in taus):
            result['Warnings'].append('A fitted relaxation time lies outside the retained measurement window; parameter recovery may be weakly constrained.')

        # 5. Auto Explanation (With WLF Warning)
        if best_model in result['Fits'] and result['Fits'][best_model]['r2'] > 0:
            best_r2 = result['Fits'][best_model]['r2']
            explanation = self.auto.generate_explanation(temp, best_model, best_r2, quality)
        else:
            best_r2 = 0.0
            explanation = f"Model {best_model} fit was not computed or failed."
        
        if Tg is not None and (Tg <= temp < Tg + 20):
            explanation += "\n\n⚠️ **Note:** Temperature is near Tg. Dynamics may follow WLF (super-Arrhenius) rather than pure Arrhenius."
            
        result['Auto_Explanation'] = explanation
        
        return result
