"""Exercise stability, export, selection and invalidation through the actual app."""
import json
import numpy as np
import pandas as pd
import streamlit as st
from streamlit.testing.v1 import AppTest

from tests import APP_PATH
from can_relax.core.models import PRONY


def test_reliability_workflow_and_stale_result_invalidation(monkeypatch):
    from can_relax.io import parser
    from can_relax.gui.tabs import tab_pub_main
    monkeypatch.setattr(tab_pub_main, 'save_and_download', lambda *args: None)
    t = np.geomspace(.8, 900, 300)
    monkeypatch.setattr(parser, 'parse_curve_records', lambda _: [
        {'Temp': temperature, 'Curve_ID': cid, 'Data': pd.DataFrame({'Time': t,
         'Modulus': 1.2*np.exp(-t/fast) + .6*np.exp(-t/slow)})}
        for temperature, cid, fast, slow in [(120., 'curve-a', 4., 68.), (140., 'curve-b', 2., 34.)]])
    downloads = {}
    real_download = st.download_button

    def download(label, data, *args, **kwargs):
        downloads[kwargs.get('key', label)] = data
        return real_download(label, data, *args, **kwargs)

    monkeypatch.setattr(st, 'download_button', download)
    app = AppTest.from_file(APP_PATH, default_timeout=90).run()
    app.checkbox(key='use_example_data').check().run()
    app.selectbox(key='analysis_fit_model').select(PRONY).run()
    next(b for b in app.button if 'Run Analysis' in b.label).click().run()
    assert not app.exception
    before = [r['Fits'][PRONY]['popt'].copy() for r in app.session_state['results']]
    app.button(key='prepare_report').click().run()
    assert 'prepared_report' in app.session_state
    app.button(key='run_fit_stability').click().run()
    assert not app.exception
    assert 'prepared_report' not in app.session_state
    evidence = json.loads(downloads['reliability_json'])
    assert len(evidence['stability']) == 2
    assert len(evidence['stability'][0]['rows']) == 4
    for old, record in zip(before, app.session_state['results']):
        np.testing.assert_array_equal(old, record['Fits'][PRONY]['popt'])
    app.button(key='prepare_report').click().run()
    assert len(json.loads(app.session_state['prepared_report']['json'])['fit_reliability']) == 2
    selection = next(control for control in app.multiselect if control.label == 'Select Curves:')
    selection.set_value(['curve-b']).run()
    assert not app.exception
    assert 'prepared_report' not in app.session_state
    assert len(json.loads(downloads['reliability_json'])['stability']) == 1
    app.button(key='prepare_report').click().run()
    report = json.loads(app.session_state['prepared_report']['json'])
    assert report['fit_reliability'][0]['curve_id'] == 'curve-b'
    assert len(report['fit_reliability']) == 1
    app.selectbox(key='analysis_fit_model').select('Maxwell').run()
    assert not app.exception
    assert 'fit_reliability' not in app.session_state
    assert 'prepared_report' not in app.session_state
