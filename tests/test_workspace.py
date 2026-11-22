"""Exercise saving, reopening and changing models through the running interface."""
from pathlib import Path
import numpy as np
from streamlit.testing.v1 import AppTest
from tests import APP_PATH


def button(app, key):
    return next(b for b in app.button if key in b.label)


def test_open_saved_project_recomputes_and_restores_review(monkeypatch):
    import streamlit as st
    from can_relax.io.parser import parse_curve_records
    from can_relax.io.project import DEFAULT_SETTINGS, load_project, save_project
    from can_relax.gui.workspace import source_file
    from can_relax.gui.tabs import tab_pub_main
    monkeypatch.setattr(tab_pub_main, 'save_and_download', lambda *args: None)
    path = Path(APP_PATH).parents[2] / 'examples/toy_data.csv'
    curves = parse_curve_records(path)
    ids = [r['Curve_ID'] for r in curves]
    recipe = {'settings': {**DEFAULT_SETTINGS, 'analysis_fit_model': 'Single_KWW', 'tg_input': 80.},
              'curve_timing': {cid: {'origin': 0., 'cutoff': .1} for cid in ids},
              'point_exclusions': {ids[0]: [2]}, 'selected_curves': ids[-2:], 'analysed': True}
    payload = save_project(path.read_bytes(), 'experiment.csv', recipe)
    real_upload, real_download = st.file_uploader, st.download_button
    downloads = {}

    def upload(*args, **kwargs):
        if kwargs.get('key') == 'project_upload':
            return source_file(payload, 'analysis.vfit')
        return real_upload(*args, **kwargs)

    def download(label, data, *args, **kwargs):
        if label == 'Save project':
            downloads['project'] = data
        return real_download(label, data, *args, **kwargs)

    monkeypatch.setattr(st, 'file_uploader', upload)
    monkeypatch.setattr(st, 'download_button', download)
    app = AppTest.from_file(APP_PATH, default_timeout=90).run()
    button(app, 'Open project').click().run()
    assert not app.exception
    assert app.selectbox(key='analysis_fit_model').value == 'Single_KWW'
    assert app.number_input(key='tg_input').value == 80.
    assert len(app.session_state['results']) == len(curves)
    first = app.session_state['results'][0]
    assert first['Preprocessing']['manual_selection']['excluded_point_numbers'] == [2]
    assert first['Preprocessing']['manual_selection']['short_time_cutoff_s'] == .1
    assert {r['Curve_ID'] for r in app.session_state['active_results']} == set(ids[-2:])
    restored = load_project(downloads['project'])
    assert restored['source_bytes'] == path.read_bytes()
    for key, value in recipe.items():
        assert restored[key] == value
    # Reopening the same file must not reuse stale data-editor changes or results.
    before = first['Fits']['Single_KWW']['popt'].copy()
    button(app, 'Open project').click().run()
    assert not app.exception
    np.testing.assert_allclose(app.session_state['results'][0]['Fits']['Single_KWW']['popt'], before)
    button(app, 'New project').click().run()
    assert not app.exception
    assert 'results' not in app.session_state
    assert 'project_source' not in app.session_state
    assert app.selectbox(key='analysis_fit_model').value == 'Maxwell'


def test_compare_models_apply_and_invalidate(monkeypatch):
    from can_relax.gui.tabs import tab_pub_main
    monkeypatch.setattr(tab_pub_main, 'save_and_download', lambda *args: None)
    app = AppTest.from_file(APP_PATH, default_timeout=90).run()
    assert any(x.value == 'Your relaxation workspace' for x in app.title)
    app.checkbox(key='use_example_data').check().run()
    button(app, 'Run Analysis').click().run()
    app.button(key='compare_three_models').click().run()
    assert not app.exception
    assert len(app.session_state['model_comparison']['results']) == 3
    app.selectbox(key='comparison_chosen_model').select('Single_KWW').run()
    app.button(key='apply_comparison_model').click().run()
    assert not app.exception
    assert app.selectbox(key='analysis_fit_model').value == 'Single_KWW'
    assert all(r['Fits']['Single_KWW']['success'] for r in app.session_state['results'])
    assert 'model_comparison' not in app.session_state
    app.number_input(key='time_cutoff').set_value(.2).run()
    assert not app.exception
    assert 'results' not in app.session_state
