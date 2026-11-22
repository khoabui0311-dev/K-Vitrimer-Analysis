"""Controlled sensitivity checks on fixed, retained observations."""
import numpy as np

from can_relax.core.analyzer import CurveAnalyzer
from can_relax.core.models import PRONY


METHOD = ('Each temperature is fitted independently. Compare the current fit with all retained '
          'observations before downsampling and with the earliest 80% and 60% of the current '
          'time span. Window checks use subsets of the current fit observations. The loading '
          'origin, reference modulus, point exclusions and plateau policy remain fixed. '
          'Automatic trimming is not repeated. Changes are sensitivity checks, not confidence '
          'intervals. A change above 20% is a review threshold, not a pass/fail validity test.')


def diagnostic_row(record, model):
    fit = record['Fits'][model]
    residual = fit.get('residual_diagnostics', {})
    optimization = fit.get('optimization') or {}
    return {
        'Curve': record['Curve_ID'], 'Temperature (°C)': record['Temp'],
        'Review': 'Review flagged' if fit['flags'] else 'Inspect results',
        'R²': fit['r2'], 'RMSE (normalized)': residual.get('rmse_normalized'),
        'Adjacent residual correlation': residual.get('lag1_correlation'),
        'Converged starts': optimization.get('converged_starts'),
        'Attempted starts': optimization.get('attempted_starts'),
        'Near-best starts': optimization.get('near_best_starts'),
        'Review notes': '; '.join(fit['flags']) or 'No screening flags; inspect residuals and sensitivity.',
    }


def check_prony_stability(record):
    """Return auditable alternatives; never overwrite the production fit or kinetics."""
    raw, baseline = record['Raw'], record['Fits'][PRONY]
    if not baseline.get('success'):
        raise ValueError('A successful two-Maxwell fit is required.')
    t, g = np.asarray(raw['t']), np.asarray(raw['g'])
    full_t, full_g = np.asarray(raw['full_t']), np.asarray(raw['full_g'])
    if full_t[0] != t[0] or full_g[0] != g[0]:
        raise ValueError('Full observations must share the original retained reference.')
    analyzer = CurveAnalyzer()
    scenarios = [('Current fit', t, g, 1.), ('All retained points', full_t, full_g, 1.)]
    for fraction in (.8, .6):
        keep = t <= t[0] + fraction * (t[-1] - t[0])
        scenarios.append((f'First {fraction:.0%} of time span', t[keep], g[keep], fraction))
    rows = []
    for label, times, values, fraction in scenarios:
        row = {'Curve': record['Curve_ID'], 'Temperature (°C)': record['Temp'],
               'Scenario': label, 'Points': len(times), 'Time-span fraction': fraction,
               'Reference time (s)': float(t[0]), 'Reference modulus (MPa)': raw['G0'],
               'Last observed time (s)': float(times[-1]), 'Plateau policy': baseline['plateau_mode']}
        try:
            if len(times) < 8:
                raise ValueError('Fewer than eight retained observations in this window.')
            if label == 'Current fit' or (np.array_equal(times, t) and np.array_equal(values, g)):
                fit = baseline
            else:
                alternative = analyzer.fit_retained(record['Temp'], times, values, raw['G0'], PRONY,
                    baseline['plateau_mode'], baseline['G_inf'] if baseline['plateau_mode'] == 'Fixed' else 0.)
                fit = alternative['Fits'][PRONY]
            if not fit['success']:
                raise ValueError(fit['error'])
            changes = (fit['popt'][1:3] / baseline['popt'][1:3] - 1) * 100
            moduli = fit['mode_moduli_MPa']
            row.update({'Status': 'Fitted', 'Fast fraction': float(fit['popt'][0]),
                        'Tau fast (s)': float(fit['popt'][1]), 'Tau slow (s)': float(fit['popt'][2]),
                        'G fast (MPa)': float(moduli[0]), 'G slow (MPa)': float(moduli[1]),
                        'Plateau (MPa)': fit['G_inf'], 'R²': fit['r2'],
                        'Fast change (%)': float(changes[0]), 'Slow change (%)': float(changes[1]),
                        'Above 20% review threshold': bool(np.max(np.abs(changes)) > 20),
                        'Review notes': '; '.join(fit['flags']),
                        'Converged starts': fit['optimization']['converged_starts'],
                        'Attempted starts': fit['optimization']['attempted_starts']})
        except (ValueError, RuntimeError, FloatingPointError) as exc:
            row.update(Status='Unavailable', **{'Review notes': str(exc)})
        rows.append(row)
    return {'curve_id': record['Curve_ID'], 'method': METHOD,
            'preprocessing': record['Preprocessing'], 'rows': rows}
