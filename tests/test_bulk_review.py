import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from tests import APP_PATH
from tests.test_workspace import button
from can_relax.gui.point_review import parse_point_numbers, selected_point_numbers


def test_ranges_are_inclusive_deduplicated_and_original_row_numbers():
    assert parse_point_numbers('1-20, 15-25, 40, 100-105', 200) == list(range(1, 26)) + [40] + list(range(100, 106))
    assert parse_point_numbers('', 20) == []


@pytest.mark.parametrize('text', ['0', '201', '20-1', '1-999999999', '1,,2', '1.5', '1-2-3', 'abc'])
def test_invalid_ranges_do_not_partially_apply(text):
    with pytest.raises(ValueError):
        parse_point_numbers(text, 200)


def test_graph_selection_uses_original_ids_across_traces():
    event = {'selection': {'points': [{'point_index': 0, 'customdata': 50},
                                      {'point_index': 0, 'customdata': [75]},
                                      {'point_index': 7, 'customdata': 50},
                                      {'point_index': 1}, {'customdata': 201}]}}
    assert selected_point_numbers(event, 200) == [50, 75]


def test_bulk_review_undo_restore_and_curve_isolation(monkeypatch):
    from can_relax.gui.tabs import tab_pub_main
    monkeypatch.setattr(tab_pub_main, 'save_and_download', lambda *args: None)
    real_plot, real_editor = st.plotly_chart, st.data_editor
    simulated_selection, editor_keys = {}, {}

    def plot(*args, **kwargs):
        result = real_plot(*args, **kwargs)
        if kwargs.get('key', '').startswith('points_graph_') and simulated_selection:
            return {'selection': {'points': [{'customdata': n} for n in simulated_selection['ids']]}}
        return result

    def editor(*args, **kwargs):
        if kwargs.get('key', '').startswith('points_'):
            editor_keys['points'] = kwargs['key']
        return real_editor(*args, **kwargs)

    monkeypatch.setattr(st, 'plotly_chart', plot)
    monkeypatch.setattr(st, 'data_editor', editor)
    app = AppTest.from_file(APP_PATH, default_timeout=90).run()
    app.checkbox(key='use_example_data').check().run()
    button(app, 'Run Analysis').click().run()
    curve_ids = [r['Curve_ID'] for r in app.session_state['results']]
    cid = next(x for x in app.selectbox if x.label == 'Review curve').value
    radio = next(x for x in app.radio if x.label == 'Select points using')
    radio.set_value('Point numbers').run()
    next(x for x in app.text_input if x.label == 'Point numbers or ranges').set_value('1-40, 75-90').run()
    button(app, 'Exclude highlighted points').click().run()
    assert not app.exception
    assert app.session_state['point_exclusions'][cid] == list(range(1, 41)) + list(range(75, 91))
    assert 'results' not in app.session_state
    # An individual edit must join the same undo history and not overwrite the bulk selection.
    app.session_state[editor_keys['points']] = {'edited_rows': {59: {'Keep': False}}, 'added_rows': [], 'deleted_rows': []}
    app.run()
    assert 60 in app.session_state['point_exclusions'][cid]
    button(app, 'Undo last point edit').click().run()
    assert 60 not in app.session_state['point_exclusions'][cid]
    assert len(app.session_state['point_exclusions'][cid]) == 56
    review = next(x for x in app.selectbox if x.label == 'Review curve')
    review.select(curve_ids[1]).run()
    other = next(x for x in app.selectbox if x.label == 'Review curve').value
    assert not app.session_state['point_exclusions'].get(other)
    next(x for x in app.selectbox if x.label == 'Review curve').select(cid).run()
    button(app, 'Restore all manually excluded points').click().run()
    assert app.session_state['point_exclusions'][cid] == []
    button(app, 'Undo last point edit').click().run()
    assert len(app.session_state['point_exclusions'][cid]) == 56
    next(x for x in app.radio if x.label == 'Select points using').set_value('Graph').run()
    simulated_selection['ids'] = [40, 60, 75]
    app.run()
    button(app, 'Restore highlighted points').click().run()
    assert 40 not in app.session_state['point_exclusions'][cid]
    assert 75 not in app.session_state['point_exclusions'][cid]
    button(app, 'Exclude highlighted points').click().run()
    assert {40, 60, 75}.issubset(app.session_state['point_exclusions'][cid])
    simulated_selection.clear()
    button(app, 'Run Analysis').click().run()
    assert not app.exception
    assert app.session_state['results'][0]['Preprocessing']['manual_selection']['excluded_point_numbers'] == app.session_state['point_exclusions'][cid]
