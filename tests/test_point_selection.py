import numpy as np
import pandas as pd
import pytest
from can_relax.core.selection import prepare_curve


def test_cutoff_and_point_exclusion_preserve_physical_time_and_source():
    data = pd.DataFrame({'Time': [1020., 1021., 1022., 1023.], 'Modulus': [5., 999., 3., 2.]})
    original = data.copy(deep=True)
    selected, preview, audit = prepare_curve(data, origin=1019, cutoff=2, excluded=[2])
    assert selected['Time'].tolist() == [3, 4]
    assert selected['Modulus'].tolist() == [3, 2]
    assert audit['excluded_point_numbers'] == [2]
    assert audit['points_before_cutoff'] == 1
    assert preview['Point'].tolist() == [1, 2, 3, 4]
    pd.testing.assert_frame_equal(data, original)


def test_exclusions_address_individual_duplicates_and_can_be_restored():
    data = pd.DataFrame({'Time': [1., 1., 2.], 'Modulus': [3., 99., 2.]})
    selected, _, _ = prepare_curve(data, excluded=[2])
    assert selected['Modulus'].tolist() == [3, 2]
    restored, _, _ = prepare_curve(data)
    assert len(restored) == 3
    empty, _, _ = prepare_curve(data, excluded=[1, 2, 3])
    assert empty.empty


@pytest.mark.parametrize('settings', [{'origin': np.nan}, {'cutoff': -1}, {'excluded': [4]}])
def test_invalid_selection_rejected(settings):
    with pytest.raises(ValueError):
        prepare_curve(pd.DataFrame({'Time': [1.], 'Modulus': [2.]}), **settings)


def test_review_workflow_invalidation_and_provenance(monkeypatch):
    from streamlit.testing.v1 import AppTest
    from can_relax.gui.tabs import tab_pub_main
    monkeypatch.setattr(tab_pub_main, 'save_and_download', lambda *args: None)
    app = AppTest.from_file('can_relax/gui/app.py', default_timeout=60).run()
    app.checkbox(key='use_example_data').check().run()
    def run_analysis():
        next(b for b in app.button if 'Run Analysis' in b.label).click().run()
        assert not app.exception
    run_analysis()
    old_id = app.session_state['analysis_id']
    point_key = next(k for k in app.session_state.filtered_state if k.startswith('points_'))
    app.session_state[point_key] = {'edited_rows': {1: {'Keep': False}}, 'added_rows': [], 'deleted_rows': []}
    app.run()
    assert not app.exception
    assert 'results' not in app.session_state
    run_analysis()
    assert app.session_state['analysis_id'] != old_id
    first = app.session_state['results'][0]
    assert first['Preprocessing']['manual_selection']['excluded_point_numbers'] == [2]
    timing_key = next(k for k in app.session_state.filtered_state if k.startswith('timing_'))
    app.session_state[timing_key] = {'edited_rows': {0: {'Loading origin (s)': .01, 'Cutoff (s)': 1.}}, 'added_rows': [], 'deleted_rows': []}
    app.run()
    assert not app.exception
    assert 'results' not in app.session_state
    run_analysis()
    audit = app.session_state['results'][0]['Preprocessing']['manual_selection']
    assert audit['loading_origin_s'] == .01
    assert audit['short_time_cutoff_s'] == 1.
    assert audit['excluded_point_numbers'] == [2]
