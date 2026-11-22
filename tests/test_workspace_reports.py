"""Report downloads and restored downstream selections must describe the live calculation."""
import json
import streamlit as st
from streamlit.testing.v1 import AppTest
from tests import APP_PATH
from tests.test_workspace import button
from can_relax.gui.workspace import source_file
from can_relax.io.project import load_project


def test_report_and_project_restore_downstream_choices(monkeypatch):
    from can_relax.gui.tabs import tab_pub_main
    monkeypatch.setattr(tab_pub_main, 'save_and_download', lambda *args: None)
    real_editor, real_download, real_upload = st.data_editor, st.download_button, st.file_uploader
    downloads, editor_keys, pending = {}, {}, {}

    def editor(*args, **kwargs):
        key = kwargs.get('key', '')
        if key.startswith('kinetics_editor_'):
            editor_keys['kinetics'] = key
        return real_editor(*args, **kwargs)

    def download(label, data, *args, **kwargs):
        downloads[label] = data
        return real_download(label, data, *args, **kwargs)

    def upload(*args, **kwargs):
        if kwargs.get('key') == 'project_upload' and pending:
            return source_file(pending['data'], 'test.vfit')
        return real_upload(*args, **kwargs)

    monkeypatch.setattr(st, 'data_editor', editor)
    monkeypatch.setattr(st, 'download_button', download)
    monkeypatch.setattr(st, 'file_uploader', upload)
    app = AppTest.from_file(APP_PATH, default_timeout=90).run()
    app.checkbox(key='use_example_data').check().run()
    button(app, 'Run Analysis').click().run()
    app.selectbox(key='kinetics_model_type').select('Eyring (Transition State)').run()
    app.session_state[editor_keys['kinetics']] = {'edited_rows': {0: {'Include': False}}, 'added_rows': [], 'deleted_rows': []}
    app.run()
    assert not app.exception
    excluded = app.session_state['kinetics_exclusions']
    assert len(excluded) == 1
    app.selectbox(key='tts_reference_temp').select(120.).run()
    app.selectbox(key='tts_normalization').select('absolute').run()
    button(app, 'Generate Mastercurve').click().run()
    app.checkbox(key='opt_alpha').uncheck().run()
    app.slider(key='alpha_reg').set_value(.25).run()
    app.slider(key='n_modes').set_value(80).run()
    app.text_input(key='report_title').set_value('Trial A').run()
    app.text_area(key='report_notes').set_value('Sample A, repeat 2').run()
    saved = downloads['Save project']
    options = load_project(saved)['options']
    assert options['kinetics_exclusions'] == excluded
    assert options['tts_generated'] and options['tts_reference_temp'] == 120.
    assert options['n_modes'] == 80 and options['alpha_reg'] == .25
    app.button(key='prepare_report').click().run()
    assert not app.exception
    report = json.loads(app.session_state['prepared_report']['json'])
    assert report['kinetics']['fit']['Type'] == 'Eyring'
    assert sum(row['Include'] for row in report['kinetics']['selection']) == 3
    assert report['mastercurve']['Normalization'] == 'absolute'
    assert report['mastercurve']['T_ref'] == 120.
    assert report['report']['notes'] == 'Sample A, repeat 2'
    assert all(len(s['tau_grid']) == 80 for s in report['spectrum'])
    assert 'prepared_report' in app.session_state
    app.text_area(key='report_notes').set_value('Changed notes').run()
    assert 'prepared_report' not in app.session_state
    # Open through the UI after changing the current analysis; no stale editor
    # state or old mastercurve may survive the new project load.
    app.selectbox(key='kinetics_model_type').select('Arrhenius').run()
    pending['data'] = saved
    app.run()
    button(app, 'Open project').click().run()
    assert not app.exception
    assert app.selectbox(key='kinetics_model_type').value == 'Eyring (Transition State)'
    assert app.session_state['kinetics_exclusions'] == excluded
    assert sum(app.session_state['kinetics_df']['Include']) == 3
    assert app.session_state['master_data']['Normalization'] == 'absolute'
    assert app.session_state['master_data']['T_ref'] == 120.
    assert app.slider(key='n_modes').value == 80
    assert app.slider(key='alpha_reg').value == .25
    assert app.text_area(key='report_notes').value == 'Sample A, repeat 2'
    # Notes survive a temporary absence of results when the user changes model.
    app.selectbox(key='analysis_fit_model').select('Single_KWW').run()
    assert not app.exception
    assert app.session_state['report_notes'] == 'Sample A, repeat 2'
    assert 'prepared_report' not in app.session_state


def test_report_never_reuses_failed_kinetics(monkeypatch):
    from can_relax.gui.tabs import tab_pub_main
    monkeypatch.setattr(tab_pub_main, 'save_and_download', lambda *args: None)
    app = AppTest.from_file(APP_PATH, default_timeout=90).run()
    app.checkbox(key='use_example_data').check().run()
    button(app, 'Run Analysis').click().run()
    app.button(key='prepare_report').click().run()
    assert app.session_state['kinetics_snapshot']['fit']['Type'] == 'Arrhenius'
    selector = next(x for x in app.multiselect if x.label == 'Select Curves:')
    selector.set_value(selector.value[:1]).run()
    assert not app.exception
    assert app.session_state['kinetics_snapshot']['fit'] is None
    assert 'prepared_report' not in app.session_state
    app.button(key='prepare_report').click().run()
    prepared = app.session_state['prepared_report']
    payload = json.loads(prepared['json'])
    assert len(payload['curves']) == len(payload['analysis']['curves']) == 1
    assert payload['kinetics']['fit'] is None
    assert b'No valid kinetics regression' in prepared['html']
