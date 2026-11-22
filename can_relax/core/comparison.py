"""Compare relaxation fits only when they use the same observations and plateau policy."""
import numpy as np
from can_relax.core.analyzer import CurveAnalyzer
from can_relax.core.models import PRONY

COMPARISON_MODELS = ('Maxwell', 'Single_KWW', PRONY)


def compare_models(temperature, data, Tg, plateau_mode, fixed_plateau):
    engine = CurveAnalyzer()
    results = {}
    reference = None
    rows = []
    for name in COMPARISON_MODELS:
        result = engine.fit_one_temp(temperature, data, Tg=Tg, fit_model=name,
                                     plateau_mode=plateau_mode, fixed_plateau=fixed_plateau)
        if not result['Valid']:
            rows.append({'Model': name, 'Status': result.get('Reason', 'Fit failed')})
            continue
        raw, fit = result['Raw'], result['Fits'][name]
        if reference is None:
            reference = raw
        elif not np.array_equal(reference['t'], raw['t']) or not np.array_equal(reference['g'], raw['g']):
            raise ValueError('Model comparison requires identical retained observations.')
        results[name] = result
        rows.append({'Model': name, 'Status': 'Review warnings' if fit['flags'] else 'Fitted',
                     'Points': len(raw['t']), 'Parameters': fit['n_params'],
                     'RMSE / reference modulus': float(np.sqrt(np.mean(fit['residuals'] ** 2))),
                     'R²': fit['r2'], 'AICc': fit['aic'], 'BIC': fit['bic'],
                     'Warnings': '; '.join(fit['flags'])})
    finite_scores = [row['AICc'] for row in rows if np.isfinite(row.get('AICc', np.inf))]
    for row in rows:
        score = row.get('AICc', np.inf)
        row['ΔAICc'] = float(score - min(finite_scores)) if finite_scores and np.isfinite(score) else None
    return {'results': results, 'rows': rows}
