"""Run from the project root with .venv/Scripts/python.exe.

Synthetic counterexamples, not experimental validation. Writes review artifacts only.
"""
from pathlib import Path
import sys
import json
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import numpy as np
import pandas as pd
from scipy.special import gamma
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from can_relax.core.spectrum import SpectrumAnalyzer
from can_relax.core.kinetics import KineticsEngine, R_GAS
from can_relax.core.analyzer import CurveAnalyzer

out = {}
fig, axes = plt.subplots(1, 2, figsize=(10, 4), layout='constrained')
t = np.geomspace(.01, 300, 200)
g = np.exp(-t/1000)
out['spectrum_truncated_maxwell'] = []
axes[0].semilogx(t, g, color='black', label='True decay; tau = 1000 s')
for subtract in [False, True]:
    engine = SpectrumAnalyzer()
    grid, weights = engine.compute_continuous_spectrum(t, g, optimize_alpha=True, subtract_G_eq=subtract)
    mean = engine.get_weighted_avg_tau(grid, weights)
    out['spectrum_truncated_maxwell'].append({
        'subtract': subtract, 'true_tau': 1000, 'window': 300,
        'estimated_Geq': engine.last_G_eq, 'geometric_mean_tau': float(mean),
        'peak_tau': float(grid[np.argmax(weights)]), 'relative_rmse': engine.last_relative_rmse,
        'warning_triggered': bool(mean > .8*t[-1]), 'alpha': float(engine.last_alpha)})
    axes[1].semilogx(grid, weights, label=f'Tail subtraction: {subtract}')
    if subtract:
        axes[0].axhline(engine.last_G_eq, color='tab:orange', linestyle='--', label='Inferred equilibrium (true value = 0)')
axes[0].set(xlabel='Elapsed time (s)', ylabel='Normalized modulus', title='Incomplete measurement misread as a plateau')
axes[1].axvline(1000, color='black', linestyle=':', label='True tau')
axes[1].set(xlabel='Mode relaxation time (s)', ylabel='Discrete modal weight', title='Baseline choice changes inferred spectrum')
for ax in axes:
    ax.legend(fontsize=8)
fig.savefig(Path(__file__).with_name('baseline_counterexample.png'), dpi=180)
plt.close(fig)

taus = [50., 200.]
values = [float(np.exp(-np.sqrt(100*(tau/50)/tau) + np.sqrt(30/tau))) for tau in taus]
out['tts_normalization'] = {'first_measured_time': 30, 'reference_tau': 50, 'taus': taus,
    'shifted_time': 100, 'shifted_normalized_moduli': values,
    'absolute_vertical_mismatch': abs(values[0]-values[1])}

temperatures = np.linspace(100, 180, 9)
T_K = temperatures + 273.15
tau = 100*np.exp(80000/R_GAS*(1/T_K-1/393.15))
observed = .01*T_K*np.exp(-30/tau)
fit = KineticsEngine().fit_van_t_hoff(temperatures, observed)
out['false_dissociation'] = {'true_modulus': '0.01*T_K, no dissociation', 'elapsed_start': 30,
    'temperatures_C': temperatures.tolist(), 'reference_moduli': observed.tolist(),
    'fit': {k: float(fit[k]) for k in ['A','dH_diss','dS_diss','R2']} if fit else None}

factor = float(gamma(3))
out['viscosity'] = {'beta': .5, 'eta_over_Gtau': factor, 'reported_Tv_C': 100,
    'corrected_Tv_C_constant_shape': float(1/(1/373.15-R_GAS/80000*np.log(factor))-273.15)}
t = np.geomspace(.01, 1000, 200)
result = CurveAnalyzer().fit_one_temp(150, pd.DataFrame({'Time': t, 'Modulus': .3+.7*np.exp(-t/10)}))
out['plateau_fit'] = {'truth': '0.3+0.7*exp(-t/10)', 'best_model': result['Best_Model'],
    'fits': {k: {'popt': np.asarray(v['popt']).tolist(), 'r2': float(v['r2']), 'aicc': float(v['aic'])}
             for k,v in result['Fits'].items()}}
Path(__file__).with_name('numerical_evidence.json').write_text(json.dumps(out, indent=2), encoding='utf-8')
print(json.dumps(out, indent=2))
