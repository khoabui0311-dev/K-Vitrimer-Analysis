"""Parameter recovery and controlled perturbations, rather than curve appearance."""
import copy
import json
import numpy as np
import pandas as pd
import pytest

from can_relax.core.analyzer import CurveAnalyzer
from can_relax.core.models import PRONY, TwoMaxwell, conditional_relaxation
from can_relax.core.optimization import fit_prony_multistart, residual_diagnostics
from can_relax.core.reliability import check_prony_stability
from can_relax.core.state import clear_analysis, clear_derived
from can_relax.io.analysis_report import make_snapshot, render_report


def experiment(mode='Zero', count=400, start=2.):
    t = np.geomspace(start, 900, count)
    plateau = .35 if mode != 'Zero' else 0.
    g = plateau + 1.2*np.exp(-t/4) + .6*np.exp(-t/68)
    record = CurveAnalyzer().fit_one_temp(120., pd.DataFrame({'Time': t, 'Modulus': g}),
        fit_model=PRONY, plateau_mode=mode, fixed_plateau=plateau)
    record['Curve_ID'] = 'known-truth'
    return record


@pytest.mark.parametrize('mode', ['Zero', 'Fixed', 'Fit'])
def test_multistart_and_stability_recover_known_modes_and_plateau(mode):
    record = experiment(mode)
    baseline = copy.deepcopy(record)
    fit = record['Fits'][PRONY]
    optimization = fit['optimization']
    assert optimization['attempted_starts'] == (25 if mode == 'Fit' else 13)
    assert optimization['converged_starts'] > 1
    np.testing.assert_allclose(fit['popt'], [2/3, 4., 68.], rtol=1e-4)
    assert optimization['best_rss'] <= optimization['trials'][0]['rss']
    check = check_prony_stability(record)
    assert len(check['rows']) == 4
    assert check['rows'][1]['Points'] > check['rows'][0]['Points']
    for row in check['rows']:
        assert row['Status'] == 'Fitted'
        assert row['Reference time (s)'] == 2.
        assert row['Reference modulus (MPa)'] == record['Raw']['G0']
        np.testing.assert_allclose([row['Tau fast (s)'], row['Tau slow (s)']], [4., 68.], rtol=1e-4)
        np.testing.assert_allclose([row['G fast (MPa)'], row['G slow (MPa)']], [1.2, .6], rtol=1e-4)
        assert row['Plateau (MPa)'] == pytest.approx(.35 if mode != 'Zero' else 0., abs=1e-6)
    np.testing.assert_array_equal(record['Fits'][PRONY]['popt'], baseline['Fits'][PRONY]['popt'])
    np.testing.assert_array_equal(record['Raw']['t'], baseline['Raw']['t'])


def test_bad_initial_solution_and_failed_start_do_not_prevent_recovery(monkeypatch):
    import can_relax.core.optimization as optimizer
    real_fit = optimizer.curve_fit
    calls = []

    def fail_once(*args, **kwargs):
        calls.append(kwargs['p0'])
        if len(calls) == 1:
            raise RuntimeError('Deliberate first-start failure')
        return real_fit(*args, **kwargs)

    monkeypatch.setattr(optimizer, 'curve_fit', fail_once)
    monkeypatch.setattr(TwoMaxwell, 'get_initial_guess', lambda *args: [.99, 1e10, 1e11])
    fit = experiment()['Fits'][PRONY]
    np.testing.assert_allclose(fit['popt'], [2/3, 4., 68.], rtol=1e-4)
    assert fit['optimization']['converged_starts'] == 12
    assert fit['optimization']['trials'][0]['success'] is False


def test_all_starts_failed_is_explicit(monkeypatch):
    import can_relax.core.optimization as optimizer

    def fail(*args, **kwargs):
        raise RuntimeError('Deliberate failure')

    monkeypatch.setattr(optimizer, 'curve_fit', fail)
    result = experiment()
    assert not result['Valid']
    assert 'All 13' in result['Fits'][PRONY]['error']


def test_near_equal_rss_can_hide_widely_different_unresolved_times(monkeypatch):
    import can_relax.core.optimization as optimizer
    # Zero-amplitude slow mode is unidentifiable, with identical predictions.
    t = np.linspace(0, 300, 50)
    g = np.exp(-t/10)
    prediction = lambda x, *params: conditional_relaxation(PRONY, x, params, 0.)
    counter = []

    def many_slow_times(*args, **kwargs):
        counter.append(1)
        return np.array([1., 10., 1000. * len(counter)]), np.eye(3)

    monkeypatch.setattr(optimizer, 'curve_fit', many_slow_times)
    _, _, evidence = fit_prony_multistart(prediction, t, g, [.5, 10., 100.], TwoMaxwell().get_bounds())
    assert evidence['near_best_starts'] == 13
    assert evidence['near_best_tau_spread_percent'][1] > 25


def test_residual_diagnostic_handles_exact_fit_and_structured_error():
    assert residual_diagnostics(np.zeros(50))['lag1_correlation'] is None
    assert residual_diagnostics(np.full(50, .01))['lag1_correlation'] is None
    assert residual_diagnostics(np.linspace(-.1, .1, 50))['structured_residuals']
    assert not residual_diagnostics(np.random.default_rng(42).normal(0, .01, 500))['structured_residuals']


def test_short_window_failure_is_reported_without_moving_reference():
    t = np.r_[2., np.linspace(700, 900, 8)]
    g = .6*np.exp(-t/40) + .4*np.exp(-t/600)
    record = CurveAnalyzer().fit_retained(140., t, g/g[0], g[0], PRONY)
    record['Curve_ID'] = 'sparse'
    rows = check_prony_stability(record)['rows']
    assert rows[-1]['Status'] == rows[-2]['Status'] == 'Unavailable'
    assert rows[-1]['Reference time (s)'] == 2.
    assert 'Fewer than eight' in rows[-1]['Review notes']


def test_retained_path_does_not_repeat_trimming(monkeypatch):
    record = experiment()

    def unexpected(*args, **kwargs):
        raise AssertionError('Sensitivity must not trim or downsample again')

    monkeypatch.setattr('can_relax.core.processing.DataProcessor.trim_curve', unexpected)
    monkeypatch.setattr('can_relax.core.processing.DataProcessor.downsample', unexpected)
    assert all(row['Status'] == 'Fitted' for row in check_prony_stability(record)['rows'])


def test_reports_filter_stability_by_analysis_and_selected_curves():
    record = experiment()
    evidence = {'analysis_id': 'current', 'curves': {'known-truth': check_prony_stability(record),
                                                   'other': {'curve_id': 'other', 'rows': []}}}
    metadata = {'model': PRONY, 'analysis_id': 'current'}
    snapshot = make_snapshot([record], metadata, b'data', 'data.csv', reliability=evidence)
    assert len(snapshot['fit_reliability']) == 1
    html, numeric = render_report(snapshot)
    assert b'First 80%' in html
    assert json.loads(numeric)['curves'][0]['optimization']['attempted_starts'] == 13
    assert not make_snapshot([record], {**metadata, 'analysis_id': 'new'}, b'data', 'data.csv',
                             reliability=evidence)['fit_reliability']
    state = {'fit_reliability': evidence}
    clear_derived(state)
    assert state['fit_reliability'] == evidence
    clear_analysis(state)
    assert 'fit_reliability' not in state


def test_unobserved_slow_mode_keeps_window_warning():
    t = np.geomspace(.1, 200, 100)
    g = .7*np.exp(-t/4) + .3*np.exp(-t/4000)
    fit = CurveAnalyzer().fit_retained(150., t, g/g[0], g[0], PRONY)['Fits'][PRONY]
    assert any('outside measurement window' in flag for flag in fit['flags'])
    assert fit['optimization']['attempted_starts'] == 13
