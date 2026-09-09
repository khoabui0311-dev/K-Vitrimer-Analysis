"""Streamlit state/engine integration; high-resolution downloads are stubbed."""
import numpy as np
import pytest
from streamlit.testing.v1 import AppTest


def _button(app, text):
    return next(x for x in app.button if text in x.label)


def test_example_analysis_and_configuration_invalidation(monkeypatch):
    from can_relax.gui.tabs import tab_pub_main
    monkeypatch.setattr(tab_pub_main, 'save_and_download', lambda *args: None)
    app = AppTest.from_file('can_relax/gui/app.py', default_timeout=60).run()
    assert not app.exception
    app.checkbox(key='use_example_data').check().run()
    _button(app, 'Run Analysis').click().run()
    assert not app.exception
    results = app.session_state['results']
    assert len(results) == 4
    assert all(r['Valid'] and r['Curve_ID'] for r in results)
    assert all(np.isfinite(r['Fits']['Maxwell']['popt']).all() for r in results)
    app.selectbox(key='kinetics_model_type').select("Van 't Hoff (Decrosslinking)").run()
    assert not app.exception
    _button(app, 'Generate Mastercurve').click().run()
    assert not app.exception
    assert 'master_data' in app.session_state
    next(x for x in app.selectbox if x.label == 'Reference T (°C)').select(120.0).run()
    assert not app.exception
    assert 'master_data' not in app.session_state
    app.selectbox(key='analysis_fit_model').select('Single_KWW').run()
    assert not app.exception
    assert 'results' not in app.session_state
    assert 'kinetics_df' not in app.session_state
    _button(app, 'Run Analysis').click().run()
    assert not app.exception
    assert all('Single_KWW' in r['Fits'] for r in app.session_state['results'])
    next(x for x in app.multiselect if x.label == 'Select Curves:').set_value([]).run()
    assert not app.exception
    assert app.session_state['kinetics_df'].empty


def test_replicates_incomplete_raw_curves_and_dataset_replacement(monkeypatch):
    from pathlib import Path
    import pandas as pd
    from can_relax.io import parser
    from can_relax.gui.tabs import tab_pub_main
    from can_relax.core.spectrum import SpectrumAnalyzer
    window_tau = [99.0]
    monkeypatch.setattr(SpectrumAnalyzer, 'get_weighted_avg_tau', lambda *args: window_tau[0])
    monkeypatch.setattr(tab_pub_main, 'save_and_download', lambda *args: None)
    version = [1]
    real_read_bytes = Path.read_bytes
    monkeypatch.setattr(Path, 'read_bytes', lambda self: str(version[0]).encode() if self == Path(__file__).resolve().parents[1] / 'examples/toy_data.csv' else real_read_bytes(self))
    def records(path):
        t = np.geomspace(.01, 100, 100)
        return [{'Temp': temp, 'Curve_ID': f'curve_{i}', 'Data': pd.DataFrame({
            'Time':t, 'Modulus':version[0]*np.exp(-t/(1000+100*i))})}
            for i, temp in enumerate([100,100,140])]
    monkeypatch.setattr(parser, 'parse_curve_records', records)
    app = AppTest.from_file('can_relax/gui/app.py', default_timeout=60).run()
    app.checkbox(key='use_example_data').check().run()
    _button(app, 'Run Analysis').click().run()
    assert not app.exception
    assert len(app.session_state['results']) == 3
    assert any('Possible incomplete relaxation' in x.value for x in app.markdown)
    window_tau[0] = 1.0
    app.run()
    assert not any('Possible incomplete relaxation' in x.value for x in app.markdown)
    old_id = app.session_state['analysis_id']
    _button(app, 'Generate Mastercurve').click().run()
    assert len(app.session_state['master_data']['Shifts']) == 3
    next(x for x in app.selectbox if x.label == 'Reference T (°C)').select(100).run()
    _button(app, 'Generate Mastercurve').click().run()
    assert app.session_state['master_data']['Tau_ref'] == pytest.approx(1050, rel=.001)
    next(x for x in app.selectbox if x.label == 'Reference replicate').select('curve_1').run()
    assert 'master_data' not in app.session_state
    _button(app, 'Generate Mastercurve').click().run()
    assert app.session_state['master_data']['Shifts']['curve_1'] == pytest.approx(1)
    next(x for x in app.radio if x.label == 'Kinetics Base:').set_value('Raw 1/e').run()
    assert not app.exception
    assert app.session_state['kinetics_df'].empty
    assert len(app.warning) >= 3
    version[0] = 2
    app.run()
    assert not app.exception
    assert 'results' not in app.session_state
    assert 'master_data' not in app.session_state
    _button(app, 'Run Analysis').click().run()
    assert not app.exception
    assert app.session_state['analysis_id'] != old_id
    assert app.session_state['results'][0]['Raw']['G0'] > 1.99
