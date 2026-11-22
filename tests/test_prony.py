from tests import APP_PATH
"""Independent absolute-modulus recovery and mode-selection checks."""
import numpy as np
import pandas as pd
import pytest

from can_relax.core.analyzer import CurveAnalyzer
from can_relax.core.models import PRONY
from can_relax.core.tts import TTSEngine


def fit_two(fast, slow, temp=120., mode='Fit'):
    t = np.geomspace(.8, 900, 220)
    plateau = .35 if mode != 'Zero' else 0.
    g = plateau + 1.2*np.exp(-t/fast) + .6*np.exp(-t/slow)
    return CurveAnalyzer().fit_one_temp(temp, pd.DataFrame({'Time': t, 'Modulus': g}),
                                        fit_model=PRONY, plateau_mode=mode, fixed_plateau=plateau)


@pytest.mark.parametrize('mode', ['Zero', 'Fixed', 'Fit'])
def test_loading_time_moduli_after_late_start(mode):
    result = fit_two(4., 68., mode=mode)
    fit = result['Fits'][PRONY]
    assert result['Valid'] and fit['success']
    np.testing.assert_allclose(fit['popt'], [2/3, 4., 68.], rtol=1e-4)
    np.testing.assert_allclose(fit['mode_moduli_MPa'], [1.2, .6], rtol=1e-4)
    assert fit['G_inf'] == pytest.approx(.35 if mode != 'Zero' else 0., abs=1e-6)
    assert fit['n_params'] == 3 + (mode == 'Fit')
    assert fit['curve'][0] == pytest.approx(1.)


def test_mode_specific_shifts_use_times_not_fractions():
    results = [fit_two(4., 68.), fit_two(2., 17., temp=140.)]
    for component, shift in [('fast', .5), ('slow', .25)]:
        master = TTSEngine().generate_mastercurve(results, ref_temp=120., component=component,
                                                  normalization='model_initial')
        assert master['Shifts']['140.0'] == pytest.approx(shift, rel=1e-4)
        assert master['Vertical_factors']['120.0'] == pytest.approx(results[0]['Raw']['G0']/2.15)


def test_one_exponential_does_not_imply_two_resolved_modes():
    t = np.geomspace(.1, 300, 120)
    data = pd.DataFrame({'Time': t, 'Modulus': np.exp(-t/30)})
    fit = CurveAnalyzer().fit_one_temp(120., data, fit_model=PRONY)['Fits'][PRONY]
    assert fit['success']
    assert any('unresolved' in flag for flag in fit['flags'])


def test_analysis_ui_exports_modes_and_selects_kinetic_time(monkeypatch):
    from io import StringIO
    import streamlit as st
    from streamlit.testing.v1 import AppTest
    from can_relax.io import parser

    t = np.geomspace(.8, 900, 180)
    data = pd.DataFrame({'Time': t, 'Modulus': 1.2*np.exp(-t/4) + .6*np.exp(-t/68)})
    monkeypatch.setattr(parser, 'parse_curve_records', lambda _: [
        {'Temp': 120., 'Curve_ID': 'prony_test', 'Data': data}])
    downloads = {}
    real_download = st.download_button

    def capture(label, data, *args, **kwargs):
        if kwargs.get('key') == 'dl_fit_params':
            downloads['parameters'] = data
        return real_download(label, data, *args, **kwargs)

    monkeypatch.setattr(st, 'download_button', capture)
    app = AppTest.from_file(APP_PATH, default_timeout=60).run()
    app.checkbox(key='use_example_data').check()
    app.selectbox(key='analysis_fit_model').select(PRONY).run()
    next(b for b in app.button if 'Run Analysis' in b.label).click().run()
    assert not app.exception
    csv = pd.read_csv(StringIO(downloads['parameters'])).iloc[0]
    np.testing.assert_allclose([csv['G1 fast (MPa)'], csv['G2 slow (MPa)'],
                                csv['Tau 1 fast (s)'], csv['Tau 2 slow (s)']],
                               [1.2, .6, 4., 68.], rtol=1e-4)
    assert app.session_state['kinetics_df']['Tau'].iloc[0] == pytest.approx(68.)
    next(r for r in app.radio if r.label == 'Fitted component').set_value('Fast (tau1)').run()
    assert not app.exception
    assert app.session_state['kinetics_df']['Tau'].iloc[0] == pytest.approx(4.)
