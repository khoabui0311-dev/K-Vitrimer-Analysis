"""Portable formatting must round-trip without changing data or analysis settings."""
import copy
import json

import pytest

from can_relax.io.figure_style import apply_style, capture_style, load_style, save_style, validate_style, with_automatic_axes, JOURNAL_SIZES
from can_relax.io.project import load_project, save_project
from tests.test_projects import recipe


def style():
    return {'pub_preset': 'Custom', 'pub_w': 16., 'pub_h': 11., 'pub_kin_showfit': False,
            'pub_panel_font_family': 'DejaVu Sans', 'pl_2': 'B', 'eyr_showfit': False,
            'pub_data_color': '#123456', 'pub_fit_color': '#abcdef', 'tiff_dpi_f2': 600}


def test_style_roundtrip_is_data_free_and_only_changes_publication():
    state = {**style(), 'results': ['measurements'], 'kinetics_model_type': 'VFT', 'secret': 'not exported'}
    document = save_style(capture_style(state), 'Paper figures')
    assert b'measurements' not in document and b'secret' not in document
    restored = load_style(document)
    assert restored == {'name': 'Paper figures', 'settings': style()}
    state['vh_yscale'] = 'Log'
    apply_style(state, restored['settings'])
    assert 'vh_yscale' not in state
    assert state['results'] == ['measurements'] and state['kinetics_model_type'] == 'VFT'
    assert state['pub_size_preset'] == 'Custom'


@pytest.mark.parametrize('invalid', [
    {'results': []}, {'pub_w': 100}, {'pub_w': 10**1000}, {'pub_h': float('nan')}, {'pub_preset': 'Unknown'},
    {'pub_kin_showfit': 'false'}, {'pub_rel_ms': 2.5}, {'pub_data_color': 'javascript:foo'},
    {'pl_2': 'x' * 81}, {'pub_rel_cust_lims': True},
    {'pub_rel_cust_lims': True, 'pub_rel_xmin': -1., 'pub_rel_xmax': 2., 'pub_rel_ymin': 0., 'pub_rel_ymax': 1.},
])
def test_invalid_format_leaves_workspace_untouched(invalid):
    state = {**style(), 'results': ['keep']}
    before = copy.deepcopy(state)
    with pytest.raises(ValueError):
        apply_style(state, invalid)
    assert state == before


def test_project_formats_one_and_two_use_default_publication_style():
    value = {**recipe(), 'publication_style': style()}
    data = save_project(b'data', 'experiment.csv', value)
    assert load_project(data)['publication_style'] == style()
    for version in (1, 2):
        document = json.loads(data)
        document['schema_version'] = version
        document.pop('publication_style')
        assert load_project(json.dumps(document).encode())['publication_style'] == {}
    document = json.loads(data)
    document.pop('publication_style')
    with pytest.raises(ValueError, match='formatting is missing'):
        load_project(json.dumps(document).encode())


def test_unsupported_or_oversized_style_rejected():
    document = json.loads(save_style(style(), 'Paper'))
    document['schema_version'] = True
    with pytest.raises(ValueError):
        load_style(json.dumps(document).encode())
    with pytest.raises(ValueError):
        load_style(b' ' * (128*1024 + 1))


@pytest.mark.parametrize('preset,size', list(JOURNAL_SIZES.items()))
def test_named_preset_has_matching_export_dimensions(preset, size):
    restored = validate_style({'pub_preset': preset})
    assert (restored['pub_w'], restored['pub_h']) == size
    with pytest.raises(ValueError, match='dimensions do not match'):
        validate_style({'pub_preset': preset, 'pub_w': 5., 'pub_h': size[1]})


def test_partial_custom_size_is_not_overwritten_by_a_default_preset():
    state = {'pub_preset': next(iter(JOURNAL_SIZES)), 'pub_w': 8.5, 'pub_h': 7.5}
    apply_style(state, {'pub_w': 16.})
    assert state['pub_preset'] == state['pub_size_preset'] == 'Custom'
    assert (state['pub_w'], state['pub_h']) == (16., 10.)


def test_automatic_axes_preserve_units_colors_scales_and_input():
    settings = {**style(), 'pub_rel_cust_lims': True, 'pub_rel_xmin': 1., 'pub_rel_xmax': 1000.,
                'pub_rel_ymin': 0., 'pub_rel_ymax': 1., 'pub_xunit': 'Minutes (min)', 'pub_xscale': 'Log'}
    original = copy.deepcopy(settings)
    automatic = with_automatic_axes(settings)
    assert settings == original
    assert automatic['pub_rel_cust_lims'] is False
    assert 'pub_rel_xmin' not in automatic and 'pub_rel_ymax' not in automatic
    assert automatic['pub_xunit'] == 'Minutes (min)' and automatic['pub_xscale'] == 'Log'
    assert automatic['pub_fit_color'] == settings['pub_fit_color']


def test_style_and_project_restore_current_widgets_without_changing_analysis(monkeypatch):
    import streamlit as st
    from streamlit.testing.v1 import AppTest
    from can_relax.gui.tabs import tab_pub_main
    from can_relax.gui.workspace import source_file
    from tests import APP_PATH
    from tests.test_workspace import button

    monkeypatch.setattr(tab_pub_main, 'save_and_download', lambda *args: None)
    original_upload, original_download = st.file_uploader, st.download_button
    pending, downloads = {}, {}

    def upload(*args, **kwargs):
        key = kwargs.get('key')
        if key in pending:
            return source_file(pending[key], 'format.vstyle' if key == 'figure_style_upload' else 'project.vfit')
        return original_upload(*args, **kwargs)

    def download(label, data, *args, **kwargs):
        downloads[label] = data
        return original_download(label, data, *args, **kwargs)

    monkeypatch.setattr(st, 'file_uploader', upload)
    monkeypatch.setattr(st, 'download_button', download)
    app = AppTest.from_file(APP_PATH, default_timeout=90).run()
    app.checkbox(key='use_example_data').check().run()
    button(app, 'Run Analysis').click().run()
    analysis_id = app.session_state['analysis_id']
    app.selectbox(key='pub_preset').select('Custom').run()
    app.number_input(key='pub_w').set_value(16.).run()
    app.checkbox(key='pub_kin_showfit').uncheck().run()
    app.text_input(key='pl_2').set_value('B').run()
    app.color_picker(key='pub_fit_color').set_value('#123456').run()
    payload = downloads['Save figure format']
    project = downloads['Save project']
    expected = load_style(payload)['settings']
    assert load_project(project)['publication_style'] == expected
    assert expected['pub_w'] == 16. and expected['pub_fit_color'] == '#123456'
    # Hidden figure controls survive widget cleanup and remain in saved formatting.
    app.checkbox(key='sh_fig2').uncheck().run()
    assert load_style(downloads['Save figure format'])['settings']['pl_2'] == 'B'
    app.checkbox(key='sh_fig2').check().run()
    assert app.text_input(key='pl_2').value == 'B'
    app.button(key='reset_figure_style').click().run()
    assert app.selectbox(key='pub_preset').value != 'Custom'
    assert app.session_state['analysis_id'] == analysis_id
    app.button(key='undo_figure_style').click().run()
    assert app.number_input(key='pub_w').value == 16.
    assert app.color_picker(key='pub_fit_color').value == '#123456'
    assert app.button(key='undo_figure_style').disabled
    app.button(key='reset_figure_style').click().run()
    pending['figure_style_upload'] = payload
    app.run()
    app.button(key='apply_figure_style').click().run()
    assert not app.exception
    assert app.number_input(key='pub_w').value == 16.
    assert not app.checkbox(key='pub_kin_showfit').value
    assert app.color_picker(key='pub_fit_color').value == '#123456'
    assert app.session_state['analysis_id'] == analysis_id
    # A bad upload is rejected before Apply and does not change the open format.
    pending['figure_style_upload'] = b'{invalid'
    app.run()
    assert not app.exception and app.button(key='apply_figure_style').disabled
    assert app.number_input(key='pub_w').value == 16.
    # Automatic axes is an explicit override, without changing the other formatting.
    bounded = {**expected, 'pub_rel_cust_lims': True, 'pub_rel_xmin': 1., 'pub_rel_xmax': 1000.,
               'pub_rel_ymin': 0., 'pub_rel_ymax': 1.}
    pending['figure_style_upload'] = save_style(bounded, 'Another dataset')
    app.run()
    app.checkbox(key='figure_style_auto_axes').check().run()
    app.button(key='apply_figure_style').click().run()
    assert not app.exception
    assert not app.checkbox(key='pub_rel_cust_lims').value
    assert app.number_input(key='pub_w').value == 16.
    assert app.session_state['analysis_id'] == analysis_id
    app.button(key='undo_figure_style').click().run()
    assert load_style(downloads['Save figure format'])['settings'] == expected
    app.button(key='reset_figure_style').click().run()
    pending['project_upload'] = project
    app.run()
    button(app, 'Open project').click().run()
    assert not app.exception
    assert app.number_input(key='pub_w').value == 16.
    assert app.text_input(key='pl_2').value == 'B'
    assert load_project(downloads['Save project'])['publication_style'] == expected
    assert app.button(key='undo_figure_style').disabled
