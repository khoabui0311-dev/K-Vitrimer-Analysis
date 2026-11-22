"""Projects must preserve data and fit choices, and reject invalid restoration atomically."""
import copy
import json
import numpy as np
import pandas as pd
import pytest

from can_relax.io.project import DEFAULT_SETTINGS, load_project, save_project
from can_relax.gui.workspace import open_project
from can_relax.core.state import analysis_identity


def recipe():
    return {'settings': {**DEFAULT_SETTINGS, 'time_origin': 1., 'time_cutoff': .2},
            'curve_timing': {'curve_1': {'origin': 1., 'cutoff': .2}},
            'point_exclusions': {'curve_1': [2]}, 'selected_curves': [], 'analysed': True}


def records(_):
    return [{'Curve_ID': 'curve_1', 'Temp': 100.,
             'Data': pd.DataFrame({'Time': [1., 2., 3., 4.], 'Modulus': [5., 4., 3., 2.]})}]


def test_project_roundtrip_preserves_original_bytes_and_recipe():
    source = b'original data\r\nincluding original formatting'
    restored = load_project(save_project(source, 'experiment.csv', recipe()))
    assert restored['source_bytes'] == source
    assert restored['filename'] == 'experiment.csv'
    for key, value in recipe().items():
        assert restored[key] == value


@pytest.mark.parametrize('mutation', [
    lambda d: d.update(schema_version=999),
    lambda d: d['source'].update(sha256='0'*64),
    lambda d: d['source'].update(filename='../elsewhere.csv'),
    lambda d: d['source'].update(base64='not base64!'),
    lambda d: d['settings'].update(time_cutoff=-1),
    lambda d: d['settings'].update(tg_input=float('nan')),
    lambda d: d['settings'].update(analysis_fit_model='Unknown'),
    lambda d: d['point_exclusions'].update(curve_1=[True]),
    lambda d: d.update(selected_curves=['curve_1', 'curve_1']),
    lambda d: d.update(settings=[]),
])
def test_project_rejects_corruption_and_invalid_settings(mutation):
    document = json.loads(save_project(b'data', 'source.csv', recipe()))
    mutation(document)
    with pytest.raises(ValueError):
        load_project(json.dumps(document).encode())


def test_open_restores_review_and_removes_stale_results():
    state = {'results': ['old'], 'master_data': 'old', 'points_old': 'old'}
    open_project(state, save_project(b'data', 'source.csv', recipe()), records)
    assert 'results' not in state and 'master_data' not in state and 'points_old' not in state
    assert state['review_dataset'] == analysis_identity(b'data', {})
    assert state['point_exclusions'] == {'curve_1': [2]}
    assert state['review_timing_table'].iloc[0]['Loading origin (s)'] == 1.
    assert state['project_restore_selection'] == []
    assert state['project_rerun_analysis'] is True


@pytest.mark.parametrize('change', ['unknown_curve', 'bad_point', 'unknown_selection'])
def test_failed_open_preserves_existing_workspace(change):
    candidate = recipe()
    if change == 'unknown_curve':
        candidate['curve_timing']['wrong'] = candidate['curve_timing'].pop('curve_1')
    elif change == 'bad_point':
        candidate['point_exclusions']['curve_1'] = [999]
    else:
        candidate['selected_curves'] = ['missing']
    state = {'results': ['existing'], 'analysis_fit_model': 'Single_KWW'}
    before = copy.deepcopy(state)
    with pytest.raises(ValueError):
        open_project(state, save_project(b'data', 'source.csv', candidate), records)
    assert state == before


def test_comparison_uses_same_points_and_recovers_two_modes():
    from can_relax.core.comparison import compare_models
    from can_relax.core.models import PRONY
    t = np.geomspace(.01, 1000, 180)
    g = .35*np.exp(-t/2) + .65*np.exp(-t/90)
    comparison = compare_models(120., pd.DataFrame({'Time': t, 'Modulus': g}), 50., 'Zero', 0.)
    assert len(comparison['results']) == 3
    raw = comparison['results']['Maxwell']['Raw']
    for result in comparison['results'].values():
        np.testing.assert_array_equal(result['Raw']['t'], raw['t'])
        np.testing.assert_array_equal(result['Raw']['g'], raw['g'])
    rows = {row['Model']: row for row in comparison['rows']}
    assert rows[PRONY]['ΔAICc'] == 0
    assert rows[PRONY]['RMSE / reference modulus'] < 1e-5
    assert rows['Maxwell']['ΔAICc'] > 10


def test_comparison_retains_failed_models_in_table():
    from can_relax.core.comparison import compare_models
    result = compare_models(20., records(None)[0]['Data'], 50., 'Zero', 0.)
    assert not result['results']
    assert len(result['rows']) == 3
    assert all(row['ΔAICc'] is None for row in result['rows'])
