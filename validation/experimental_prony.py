"""Reproducible experimental stability audit; never modifies or uploads input data.

Run with the application environment and an explicit workbook path. Outputs stay
in the supplied directory. The independent solver uses reference-time amplitudes
and log times, not the application's parameterization or initial guess.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
from scipy.optimize import least_squares

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from can_relax.core.analyzer import CurveAnalyzer
from can_relax.core.models import PRONY
from can_relax.io.parser import parse_curve_records
from can_relax.version import VERSION


def independent_fit(t, y, starts=None):
    dt = t - t[0]
    span = dt[-1]
    if starts is None:
        starts = [[a, np.log(span*f), np.log(span*s)]
                  for a in (.2, .5, .8) for f, s in ((.001, .1), (.01, 1), (.1, 10), (.3, .7))]
    solutions = []
    for start in starts:
        fit = least_squares(lambda p: p[0]*np.exp(-dt/np.exp(p[1]))
                            + (1-p[0])*np.exp(-dt/np.exp(p[2])) - y,
                            start, bounds=([0, np.log(1e-9), np.log(1e-9)],
                                           [1, np.log(1e12), np.log(1e12)]),
                            max_nfev=3000, ftol=1e-11, xtol=1e-11, gtol=1e-11)
        if fit.success and np.isfinite(fit.fun).all():
            a, lf, ls = fit.x
            if lf > ls:
                a, lf, ls = 1-a, ls, lf
            solutions.append({'rss': float(fit.fun @ fit.fun), 'a_reference': float(a),
                              'tau_fast_s': float(np.exp(lf)), 'tau_slow_s': float(np.exp(ls))})
    if not solutions:
        raise RuntimeError('Independent optimization failed for every start.')
    solutions.sort(key=lambda x: x['rss'])
    return solutions


def prediction(t, solution):
    dt = t-t[0]
    a = solution['a_reference']
    return a*np.exp(-dt/solution['tau_fast_s']) + (1-a)*np.exp(-dt/solution['tau_slow_s'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--bootstrap', type=int, default=100)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(20261122)
    report = {'software_version': VERSION, 'source_sha256': hashlib.sha256(args.source.read_bytes()).hexdigest(),
              'source_name': args.source.name, 'policy': 'Independent zero-plateau fits; Tg exclusion 50 C; origin 0 s; no manual exclusions',
              'method': '12 independent log-time starts on exactly the retained/downsampled application observations; sensitivity to full retained sampling and last 20% of time removed',
              'bootstrap': {'replicates': args.bootstrap, 'seed': 20261122,
                            'interpretation': 'Centered iid residual resampling, fixed reference and preprocessing. Conditional numerical sensitivity, not validated experimental confidence intervals.'},
              'excluded': [], 'curves': []}
    plots = []
    for record in parse_curve_records(args.source):
        result = CurveAnalyzer().fit_one_temp(record['Temp'], record['Data'], Tg=50, fit_model=PRONY)
        if not result['Valid']:
            report['excluded'].append({'temperature_C': record['Temp'], 'reason': result['Reason']})
            continue
        raw, app = result['Raw'], result['Fits'][PRONY]
        t, y = raw['t'], raw['g']
        solutions = independent_fit(t, y)
        best = solutions[0]
        near = [s for s in solutions if s['rss'] <= best['rss']*1.001 + 1e-12]
        fit_y = prediction(t, best)
        residual = y-fit_y
        residual -= residual.mean()
        start = [best['a_reference'], np.log(best['tau_fast_s']), np.log(best['tau_slow_s'])]
        bootstrap = []
        for _ in range(args.bootstrap):
            sample = fit_y+rng.choice(residual, len(y), replace=True)
            sample[0] = 1.  # The application's retained-reference ratio is fixed.
            bootstrap.append(independent_fit(t, sample, [start])[0])
        full = independent_fit(raw['full_t'], raw['full_g'])[0]
        keep = t <= t[0]+.8*(t[-1]-t[0])
        short = independent_fit(t[keep], y[keep])[0]
        row = {'temperature_C': record['Temp'], 'input_points': len(record['Data']),
               'retained_points': len(raw['full_t']), 'fit_points': len(t),
               'time_window_s': [float(t[0]), float(t[-1])],
               'app': {'tau_fast_s': float(app['popt'][1]), 'tau_slow_s': float(app['popt'][2]),
                       'G_fast_MPa': float(app['mode_moduli_MPa'][0]), 'G_slow_MPa': float(app['mode_moduli_MPa'][1]),
                       'r2': app['r2'], 'rss': float(np.sum(app['residuals']**2)), 'flags': app['flags']},
               'independent_best': best, 'converged_starts': len(solutions), 'near_best_starts': len(near),
               'near_best_tau_ranges_s': {k: [min(s[k] for s in near), max(s[k] for s in near)] for k in ('tau_fast_s','tau_slow_s')},
               'bootstrap_2_5_97_5_percentiles_s': {k: np.percentile([s[k] for s in bootstrap], [2.5,97.5]).tolist() for k in ('tau_fast_s','tau_slow_s')},
               'full_retained_sampling': full, 'first_80_percent_time_window': short,
               'residual_lag1_correlation': float(np.corrcoef((y-fit_y)[:-1], (y-fit_y)[1:])[0,1])}
        report['curves'].append(row)
        plots.append((record['Temp'], t, y, app['curve'], fit_y))
        print(json.dumps(row), flush=True)
    (args.output/'experimental-stability.json').write_text(json.dumps(report, indent=2, allow_nan=False), encoding='utf-8')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(len(plots), 2, figsize=(10, 2.2*len(plots)), squeeze=False)
    for ax, (temp, t, y, fitted, independent) in zip(axes, plots):
        ax[0].plot(t/60, y, '.', color='.6', label='Measurements')
        ax[0].plot(t/60, fitted, label='VitriFit')
        ax[0].plot(t/60, independent, '--', label='Independent solver')
        ax[0].set(title=f'{temp:g} °C', ylabel='G / G(reference)', xlabel='Elapsed time (min)')
        ax[1].plot(t/60, y-fitted, '.', label='Residuals')
        ax[1].axhline(0, color='.5', linewidth=.7)
        ax[1].set(ylabel='Measured − fitted', xlabel='Elapsed time (min)')
    axes[0,0].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(args.output/'experimental-fits-and-residuals.pdf')
    fig.savefig(args.output/'experimental-fits-and-residuals.png', dpi=140)
    plt.close(fig)


if __name__ == '__main__':
    main()
