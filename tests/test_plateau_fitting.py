"""Recovery checks for plateau fits with a nonzero physical start time."""
import numpy as np
import pandas as pd
import pytest

from can_relax.core.analyzer import CurveAnalyzer
from can_relax.core.kinetics import KineticsEngine, R_GAS


def fit_curve(model='Single_KWW', mode='Fit', plateau=.3, start=20., stop=3000., noise=0):
    t = np.geomspace(start, stop, 220)
    beta = 1 if model == 'Maxwell' else .65
    g = plateau + (2-plateau)*np.exp(-(t/100)**beta)
    g += np.random.default_rng(7).normal(0, noise, len(t))
    result = CurveAnalyzer().fit_one_temp(120, pd.DataFrame({'Time': t, 'Modulus': g}),
        fit_model=model, plateau_mode=mode, fixed_plateau=plateau)
    assert result['Valid']
    return result, result['Fits'][model]


@pytest.mark.parametrize('model', ['Maxwell', 'Single_KWW'])
@pytest.mark.parametrize('mode', ['Fit', 'Fixed'])
def test_plateau_recovery_preserves_origin(model, mode):
    result, fit = fit_curve(model, mode)
    assert fit['popt'][0] == pytest.approx(100, rel=.001)
    assert fit['G_inf'] == pytest.approx(.3, abs=1e-5)
    assert fit['curve'][0] == pytest.approx(1)
    assert result['Raw']['t'][0] >= 20
    assert np.max(np.abs(fit['residuals'])) < 1e-5
    assert fit['n_params'] == (1 if model == 'Maxwell' else 2) + (mode == 'Fit')


def test_noisy_plateau_and_zero_limit():
    _, fit = fit_curve(noise=.0005)
    assert fit['G_inf'] == pytest.approx(.3, abs=.004)
    assert fit['popt'][0] == pytest.approx(100, rel=.03)
    _, fit = fit_curve(plateau=0)
    assert fit['G_inf'] < .001
    assert fit['popt'][0] == pytest.approx(100, rel=.01)


def test_truncated_plateau_is_flagged():
    _, fit = fit_curve(stop=40)
    assert any('window' in flag for flag in fit['flags'])


def test_invalid_fixed_plateau_and_unsupported_model():
    t = np.arange(20.)
    df = pd.DataFrame({'Time': t, 'Modulus': np.exp(-t/10)})
    result = CurveAnalyzer().fit_one_temp(120, df, fit_model='Maxwell', plateau_mode='Fixed', fixed_plateau=2)
    assert not result['Valid']
    with pytest.raises(ValueError):
        CurveAnalyzer().fit_one_temp(120, df, fit_model='Dual_KWW', plateau_mode='Fit')


def test_recovered_plateau_taus_recover_activation_energy():
    temperatures = np.linspace(100, 180, 6)
    taus = []
    for temperature in temperatures:
        tau = 100*np.exp(65000/R_GAS*(1/(temperature+273.15)-1/413.15))
        t = np.geomspace(5, 30*tau, 200)
        g = .2+1.8*np.exp(-(t/tau)**.7)
        result = CurveAnalyzer().fit_one_temp(temperature, pd.DataFrame({'Time': t, 'Modulus': g}),
            fit_model='Single_KWW', plateau_mode='Fit')
        taus.append(result['Fits']['Single_KWW']['popt'][0])
    kinetics = KineticsEngine().fit_arrhenius(temperatures, taus)
    assert kinetics['Ea'] == pytest.approx(65, abs=.05)


def test_plateau_controls_invalidate_and_export(monkeypatch):
    from streamlit.testing.v1 import AppTest
    from can_relax.gui.tabs import tab_pub_main
    monkeypatch.setattr(tab_pub_main, 'save_and_download', lambda *args: None)
    app = AppTest.from_file('can_relax/gui/app.py', default_timeout=60).run()
    app.checkbox(key='use_example_data').check().run()
    app.selectbox(key='analysis_fit_model').select('Single_KWW').run()
    app.selectbox(key='plateau_mode').select('Fit').run()
    next(b for b in app.button if 'Run Analysis' in b.label).click().run()
    assert not app.exception
    assert all(r['Fits']['Single_KWW']['plateau_mode'] == 'Fit' for r in app.session_state['results'])
    assert any(m.label == 'Apparent Ea' for m in app.metric)
    app.selectbox(key='plateau_mode').select('Fixed').run()
    assert 'results' not in app.session_state
    next(b for b in app.button if 'Run Analysis' in b.label).click().run()
    assert not app.exception
    assert all(r['Fits']['Single_KWW']['G_inf'] == 0 for r in app.session_state['results'])
