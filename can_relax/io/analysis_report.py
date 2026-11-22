"""Self-contained, printable reports generated from a frozen analysis snapshot."""
from datetime import datetime, timezone
import hashlib
import html
import io
import json
import math

import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_svg import FigureCanvasSVG

from can_relax.core.models import PRONY
from can_relax.version import APP_NAME, VERSION

PARAMETERS = {
    'Maxwell': ['tau (s)'], 'Single_KWW': ['tau (s)', 'beta'],
    'Dual_KWW': ['fast fraction', 'tau fast (s)', 'beta fast', 'tau slow (s)', 'beta slow'],
    PRONY: ['fast fraction', 'tau fast (s)', 'tau slow (s)'],
}


def plain(value):
    """Convert numerical output to strict JSON; unavailable values remain explicit nulls."""
    if isinstance(value, np.ndarray):
        return plain(value.tolist())
    if isinstance(value, np.generic):
        return plain(value.item())
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {str(key): plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [plain(item) for item in value]
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    raise TypeError(f'Unsupported report value: {type(value).__name__}')


def make_snapshot(results, metadata, source_bytes, source_name, kinetics=None, master=None,
                  spectrum=None, comparison=None, skipped=None, options=None, reliability=None):
    model = metadata['model']
    curves = []
    for record in results:
        fit, raw = record['Fits'][model], record['Raw']
        errors = np.sqrt(np.maximum(np.diag(fit['covariance']), 0))
        curves.append({
            'curve_id': record['Curve_ID'], 'temperature_C': record['Temp'],
            'reference_modulus_MPa': raw['G0'], 'reference_time_s': raw['t'][0],
            'time_s': raw['t'], 'observed_normalized': raw['g'],
            'fitted_normalized': fit['curve'], 'residuals_normalized': fit['residuals'],
            'parameters': dict(zip(PARAMETERS[model], fit['popt'])),
            'local_standard_errors': dict(zip(PARAMETERS[model], errors)),
            'mode_moduli_MPa': fit.get('mode_moduli_MPa'),
            'optimization': fit.get('optimization'),
            'residual_diagnostics': fit.get('residual_diagnostics'),
            'plateau_MPa': fit['G_inf'], 'plateau_local_SE_MPa': fit['G_inf_std'],
            'R2': fit['r2'], 'AICc': fit['aic'], 'BIC': fit['bic'],
            'preprocessing': record['Preprocessing'],
            'warnings': list(dict.fromkeys(record['Warnings'] + fit['flags'])),
        })
    selected_ids = {r['Curve_ID'] for r in results}
    checks = []
    if reliability and reliability.get('analysis_id') == metadata['analysis_id']:
        checks = [item for cid, item in reliability.get('curves', {}).items() if cid in selected_ids]
    metadata = dict(metadata)
    if 'curves' in metadata:
        metadata['curves'] = [c for c in metadata['curves'] if c['curve_id'] in selected_ids]
    return plain({'format': 'vitrifit-analysis-snapshot', 'schema_version': 1,
                  'software': {'name': APP_NAME, 'version': VERSION},
                  'source': {'filename': source_name, 'sha256': hashlib.sha256(source_bytes).hexdigest()},
                  'analysis': metadata, 'selected_curve_ids': [r['Curve_ID'] for r in results],
                  'curves': curves, 'kinetics': kinetics, 'mastercurve': master,
                  'spectrum': spectrum, 'comparison': comparison, 'fit_reliability': checks,
                  'skipped_curves': skipped or [],
                  'options': options or {}})


def fingerprint(snapshot, title, notes):
    return hashlib.sha256(json.dumps([snapshot, title, notes], sort_keys=True,
                                    allow_nan=False).encode('utf-8')).hexdigest()


def _text(value):
    if value is None:
        return 'Unavailable'
    if isinstance(value, float):
        return f'{value:.6g}'
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False, allow_nan=False)
    return str(value)


def _escape(value):
    return html.escape(_text(value), quote=True)


def _table(rows):
    if not rows:
        return '<p class="muted">No rows available.</p>'
    columns = list(dict.fromkeys(key for row in rows for key in row))
    header = ''.join(f'<th>{_escape(key)}</th>' for key in columns)
    body = ''.join('<tr>' + ''.join(f'<td>{_escape(row.get(key))}</td>' for key in columns) + '</tr>' for row in rows)
    return f'<div class="table-wrap"><table><thead><tr>{header}</tr></thead><tbody>{body}</tbody></table></div>'


def _plot(series, xlabel, ylabel, log_x=False, zero=False):
    figure = Figure(figsize=(9, 3.6), constrained_layout=True)
    axis = figure.subplots()
    for x, y, label, kind in series:
        axis.plot(x, y, '.' if kind == 'points' else '-', label=label, markersize=3, linewidth=1.2)
    if log_x:
        axis.set_xscale('log')
    if zero:
        axis.axhline(0, color='#64748b', linewidth=.7, linestyle='--')
    axis.set(xlabel=xlabel, ylabel=ylabel)
    axis.grid(alpha=.15)
    axis.legend(fontsize=7, loc='best')
    output = io.StringIO()
    FigureCanvasSVG(figure).print_svg(output)
    svg = output.getvalue()
    return '<div class="chart">' + svg[svg.index('<svg'):] + '</div>'


def render_report(snapshot, title='Relaxation analysis', notes=''):
    """Return immutable HTML + JSON bytes. No JavaScript, remote assets or network access."""
    if not snapshot['curves']:
        raise ValueError('Select at least one fitted curve to prepare a report.')
    report_id = fingerprint(snapshot, title, notes)
    saved = {**snapshot, 'report': {'title': title, 'notes': notes, 'fingerprint': report_id,
                                    'created_utc': datetime.now(timezone.utc).isoformat()}}
    curves, analysis = saved['curves'], saved['analysis']
    parts = [f'<header><p class="eyebrow">{_escape(APP_NAME)} · ANALYSIS REPORT</p><h1>{_escape(title)}</h1>',
             f'<p>{_escape(saved["source"]["filename"])} · {_escape(analysis["model"])} · {len(curves)} selected curves</p>',
             f'<p class="muted">Software {_escape(saved["software"]["version"])} · Created {_escape(saved["report"]["created_utc"])} (UTC)</p></header>']
    if notes.strip():
        parts.append(f'<section><h2>Research notes</h2><p class="notes">{_escape(notes)}</p></section>')
    parts.append('<section><h2>Analysis summary</h2>')
    parts.append(_table([{'Curve': c['curve_id'], 'Temperature (°C)': c['temperature_C'],
                         'Fitted points': len(c['time_s']), 'First time (s)': c['time_s'][0],
                         'Last time (s)': c['time_s'][-1], 'R²': c['R2'],
                         'AICc': c['AICc'], 'BIC': c['BIC']} for c in curves]))
    parts.append('<p>Only the selected fitted curves are shown. Other imported or fitted curves are not implied to be included in these results.</p>')
    if saved['skipped_curves']:
        parts.append('<h3>Skipped during fitting</h3><ul>' + ''.join(f'<li>{_escape(s)}</li>' for s in saved['skipped_curves']) + '</ul>')
    parts.append('</section><section><h2>Measured curves and fits</h2>')
    parts.append(_plot([(c['time_s'], c[key], c['curve_id'] + suffix, kind) for c in curves
                        for key, suffix, kind in [('observed_normalized', ' measured', 'points'),
                                                  ('fitted_normalized', ' fit', 'line')]],
                       'Elapsed time (s)', 'G(t) / G(reference)'))
    parts.append(_plot([(c['time_s'], c['residuals_normalized'], c['curve_id'], 'line') for c in curves],
                       'Elapsed time (s)', 'Observed − fitted (normalized)', zero=True))
    parts.append('<p>Figures use a linear time axis so observations at t = 0 are retained. The JSON snapshot includes all retained points.</p></section>')
    for curve in curves:
        parts.append(f'<section><h2>{_escape(curve["curve_id"])} · {_escape(curve["temperature_C"])} °C</h2>')
        parts.append(_table([{'Parameter': name, 'Estimate': value, 'Local standard error': curve['local_standard_errors'][name]}
                             for name, value in curve['parameters'].items()]))
        parts.append(_table([{'Reference modulus (MPa)': curve['reference_modulus_MPa'],
                             'Reference time (s)': curve['reference_time_s'], 'Plateau (MPa)': curve['plateau_MPa'],
                             'Plateau local SE (MPa)': curve['plateau_local_SE_MPa']}]))
        if curve['mode_moduli_MPa'] is not None:
            parts.append(_table([{'Loading-time G fast (MPa)': curve['mode_moduli_MPa'][0],
                                 'Loading-time G slow (MPa)': curve['mode_moduli_MPa'][1]}]))
        parts.append('<h3>Review notes</h3><ul>' + ''.join(f'<li>{_escape(w)}</li>' for w in curve['warnings']) + '</ul>')
        parts.append(f'<details><summary>Preprocessing and point selection</summary><pre>{_escape(curve["preprocessing"])}</pre></details></section>')
    parts.append('<section><h2>Fit reliability</h2>')
    parts.append(_table([{'Curve': c['curve_id'],
        'RMSE (normalized)': (c.get('residual_diagnostics') or {}).get('rmse_normalized'),
        'Adjacent residual correlation': (c.get('residual_diagnostics') or {}).get('lag1_correlation'),
        'Starts converged': (c.get('optimization') or {}).get('converged_starts'),
        'Starts attempted': (c.get('optimization') or {}).get('attempted_starts'),
        'Near-best starts': (c.get('optimization') or {}).get('near_best_starts')} for c in curves]))
    parts.append('<p>Two-Maxwell fits select the lowest RSS across deterministic starting guesses. Near-best RSS tolerance is max(0.1% of best RSS, 10⁻¹²). Time spread above 25% flags numerical ambiguity. Adjacent residual correlation |r| ≥ 0.5 flags structure; it is descriptive, not a significance test. Neither convergence nor high R² establishes identifiable physical modes.</p>')
    checked_ids = set()
    for check in saved.get('fit_reliability', []):
        checked_ids.add(check['curve_id'])
        parts.append(f'<h3>{_escape(check["curve_id"])}</h3><p>{_escape(check["method"])}</p>')
        parts.append(_table([{key: row.get(key) for key in ('Scenario', 'Status', 'Points',
            'Tau fast (s)', 'Tau slow (s)', 'Fast change (%)', 'Slow change (%)')} for row in check['rows']]))
        parts.append(_table([{key: row.get(key) for key in ('Scenario', 'G fast (MPa)', 'G slow (MPa)',
            'Plateau (MPa)', 'Last observed time (s)', 'Review notes')} for row in check['rows']]))
    unchecked = [c['curve_id'] for c in curves if c['curve_id'] not in checked_ids]
    if unchecked:
        parts.append(f'<p>Window/sampling stability not checked for: {_escape(", ".join(unchecked))}.</p>')
    parts.append('</section>')
    kinetics = saved.get('kinetics')
    parts.append('<section><h2>Kinetics</h2>')
    if kinetics:
        parts.append(f'<p>Model: {_escape(kinetics["model"])} · Time source: {_escape(kinetics["mode"])} · Component: {_escape(kinetics["component"])}</p>')
        parts.append(_table(kinetics['selection']))
        fit = kinetics.get('fit')
        if fit:
            result_units = {'Ea': 'kJ/mol', 'Ea_std': 'kJ/mol', 'Ea_CI95': 'kJ/mol',
                            'dH': 'kJ/mol', 'dH_std': 'kJ/mol', 'dS': 'J/(mol K)',
                            'dH_diss': 'kJ/mol', 'dS_diss': 'J/(mol K)', 'A': 'MPa/K',
                            'Ea_chem': 'kJ/mol', 'B_glass': 'K', 'T0_glass': '°C'}
            coefficient_units = {'slope': 'K', 'intercept': 'dimensionless', 'B': 'K', 'T0': 'K',
                                 'Ea': 'J/mol', 'dH_diss': 'J/mol', 'dS_diss': 'J/(mol K)',
                                 'ln_A': 'dimensionless', 'ln_C': 'dimensionless',
                                 'A': 'MPa/K' if fit['Type'] == 'Van_t_Hoff' else 'dimensionless'}
            parts.append(_table([{'Result': name, 'Value': value, 'Units': result_units.get(name, '')} for name, value in fit.items() if name not in ('Plot', 'Params')]))
            parts.append(_table([{'Fitted coefficient': name, 'Value': value, 'Units': coefficient_units.get(name, '')} for name, value in fit['Params'].items()]))
            plot = fit['Plot']
            order = np.argsort(plot['x'])
            x_label, y_label = {
                'Arrhenius': ('1/T (K⁻¹)', 'ln(tau / s)'), 'VFT': ('1/T (K⁻¹)', 'ln(tau / s)'),
                'Eyring': ('1/T (K⁻¹)', 'ln(tau T / (s K))'),
                'Van_t_Hoff': ('1000/T (K⁻¹)', 'Reference modulus (MPa)'),
                'Coupled': ('1/T (K⁻¹)', 'ln(tau / s)'),
            }[fit['Type']]
            parts.append(_plot([(plot['x'], plot['y'], 'Included observations', 'points'),
                                (np.asarray(plot['x'])[order], np.asarray(plot['y_pred'])[order], 'Fit at measured temperatures', 'line')], x_label, y_label))
        else:
            parts.append('<p class="notice">No valid kinetics regression for this selection. No previous kinetics result has been reused.</p>')
    else:
        parts.append('<p>No valid kinetics observations for this selection.</p>')
    parts.append('<p>Ea_CI95 is a 95% regression interval. Regression uncertainty does not propagate uncertainty from fitting each curve. Apparent Eyring parameters assume tau is an inverse molecular rate with transmission coefficient one. Van ’t Hoff fits to reference moduli do not establish dissociation thermodynamics; coupled fits are phenomenological.</p></section>')
    master = saved.get('mastercurve')
    parts.append('<section><h2>Mastercurve</h2>')
    if master:
        parts.append(f'<p>Reference temperature: {_escape(master["T_ref"])} °C. Normalization: {_escape(master["Normalization"])}. Component: {_escape(master["Component"])}.</p>')
        parts.append(_table([{'Curve': cid, 'aT': shift, 'Vertical factor': master['Vertical_factors'][cid]} for cid, shift in master['Shifts'].items()]))
        ylabel = 'Modulus (MPa)' if master['Normalization'] == 'absolute' else ('G(t) / G(0), extrapolated' if master['Normalization'] == 'model_initial' else 'G(t) / G(reference)')
        parts.append(_plot([(master['Master_t'], master['Master_g'], 'Shifted observations', 'points')], 'Shifted time (s)', ylabel))
        parts.append(f'<p class="notice">{_escape(master["Warning"])}</p>')
    else:
        parts.append('<p>Not generated for the current selection.</p>')
    parts.append('</section>')
    spectrum = saved.get('spectrum')
    if spectrum:
        parts.append('<section><h2>Relaxation spectrum</h2>')
        parts.append(_plot([(s['tau_grid'], s['H'], s['Curve_ID'], 'line') for s in spectrum],
                           'Relaxation time (s)', 'Discrete modal weight / G(reference)', log_x=True))
        parts.append(_table([{'Curve': s['Curve_ID'], 'Regularization alpha': s['last_alpha'],
                             'Subtracted baseline / reference': s['last_G_eq'], 'Relative RMSE': s['reconstruction_error']} for s in spectrum]))
        parts.append('<p>Regularized discrete exponential weights are not a unique continuous spectrum. Tail subtraction and the measurement window affect the result.</p></section>')
    if saved.get('comparison'):
        parts.append('<section><h2>Model comparison</h2>')
        parts.append(f'<p>Comparison curve: {_escape(saved["comparison"]["curve_id"])}. This selection may differ from the curves used in the report above.</p>')
        parts.append(_table(saved['comparison']['rows']))
        parts.append('<p>Scores use the same retained observations and plateau policy. Lower scores do not establish a molecular mechanism.</p></section>')
    parts.append('<section><h2>Methods and traceability</h2><p>Each temperature is fitted independently using least squares on modulus normalized by the first retained observation. Loading origin and manual exclusions precede automatic trimming and logarithmic downsampling. Curve fits do not impose an Arrhenius law.</p><p>Local fit errors and regression intervals are screening tools, not evidence of identifiability. Slow modes outside the observation window are extrapolations. Two fitted modes alone do not identify two physical mechanisms.</p>')
    parts.append(f'<p>Source SHA-256: <code>{_escape(saved["source"]["sha256"])}</code><br>Analysis ID: <code>{_escape(analysis["analysis_id"])}</code><br>Report fingerprint: <code>{report_id}</code></p>')
    parts.append(f'<details><summary>Analysis settings and provenance</summary><pre>{_escape(analysis)}</pre></details>')
    parts.append(f'<details><summary>Display and downstream settings</summary><pre>{_escape(saved["options"])}</pre></details></section>')
    stylesheet = """body{font:15px/1.55 'Segoe UI',Arial,sans-serif;color:#183044;background:#edf3f5;margin:0}main{max-width:1040px;margin:auto;padding:32px}header,section{background:white;padding:28px;margin:0 0 22px;border-radius:10px;border:1px solid #dce5e9}header{border-top:6px solid #0f766e}h1{font-size:32px;margin:8px 0}h2{font-size:22px;margin:0 0 16px}h3{font-size:17px}.eyebrow{color:#0f766e;font-weight:bold;letter-spacing:2px}.muted{color:#526572}.notes{white-space:pre-wrap}.table-wrap{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:13px;margin:12px 0}th,td{padding:9px;text-align:left;border-bottom:1px solid #dce5e9;vertical-align:top}th{background:#eff7f6}td{overflow-wrap:anywhere}.chart svg{max-width:100%;height:auto}.notice{border-left:4px solid #c87816;padding:12px;background:#fff8e9}pre,code{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px}details{margin:12px 0}footer{text-align:center;color:#526572}@media print{body{background:white}main{padding:0;max-width:none}header,section{border-radius:0;padding:15px;box-shadow:none}h2,h3{break-after:avoid}.chart,tr{break-inside:avoid}table{font-size:10px}.table-wrap{overflow:visible}details{display:block}}"""
    document = ('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
                + f'<title>{_escape(title)} — VitriFit</title><style>{stylesheet}</style></head><body><main>'
                + ''.join(parts) + '<footer>Self-contained report · Open offline in a browser · Use Print to save as PDF<br>Unavailable values are recorded as null in the accompanying JSON snapshot.</footer></main></body></html>')
    return document.encode('utf-8'), json.dumps(saved, indent=2, ensure_ascii=False, allow_nan=False).encode('utf-8')
