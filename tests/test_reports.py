"""Report fidelity, offline rendering, escaping and project format migration."""
import json
from html.parser import HTMLParser
import numpy as np
import pandas as pd
import pytest

from can_relax.core.analyzer import CurveAnalyzer
from can_relax.core.kinetics import KineticsEngine
from can_relax.io.analysis_report import make_snapshot, render_report, fingerprint
from can_relax.io.project import load_project, save_project
from can_relax.io.project_options import DEFAULT_OPTIONS
from tests.test_projects import recipe


def snapshot():
    results = []
    for temperature, tau in [(100., 20.), (140., 2.), (180., .3)]:
        t = np.geomspace(.001, 300, 130)
        result = CurveAnalyzer().fit_one_temp(temperature, pd.DataFrame({'Time': t, 'Modulus': 2*np.exp(-t/tau)}), fit_model='Maxwell')
        result['Curve_ID'] = f'curve_{temperature:g}'
        results.append(result)
    temperatures = [r['Temp'] for r in results]
    taus = [r['Fits']['Maxwell']['popt'][0] for r in results]
    selection = [{'Curve_ID': r['Curve_ID'], 'Temp': r['Temp'], 'Tau': tau, 'Include': True} for r, tau in zip(results, taus)]
    kinetics = {'model': 'Arrhenius', 'mode': 'Fit Parameter', 'component': None,
                'selection': selection, 'fit': KineticsEngine().fit_arrhenius(temperatures, taus)}
    return make_snapshot(results, {'model': 'Maxwell', 'analysis_id': 'test-analysis'}, b'raw source', 'experiment.csv', kinetics=kinetics)


def test_report_preserves_numbers_and_excludes_executable_or_external_content():
    value = snapshot()
    report, numeric = render_report(value, '<script>alert(1)</script>', '<img src="https://example.org/private">')
    text = report.decode()
    saved = json.loads(numeric)
    assert saved['curves'] == value['curves']
    assert saved['kinetics'] == value['kinetics']
    assert saved['report']['fingerprint'] == fingerprint(value, '<script>alert(1)</script>', '<img src="https://example.org/private">')
    assert '&lt;script&gt;' in text and '&lt;img' in text

    class Inspector(HTMLParser):
        def handle_starttag(self, tag, attrs):
            assert tag not in ('script', 'iframe', 'object', 'embed', 'link', 'img')
            assert not any(key.lower().startswith('on') for key, _ in attrs)
            for key, value in attrs:
                if key in ('src', 'href', 'xlink:href'):
                    assert value.startswith('#')
    Inspector().feed(text)
    assert text.count('<svg') == 3
    assert 'Regression uncertainty does not propagate' in text


def test_report_contains_only_selected_curves_and_explicit_missing_kinetics():
    value = snapshot()
    value['curves'] = value['curves'][:1]
    value['selected_curve_ids'] = [value['curves'][0]['curve_id']]
    value['kinetics']['fit'] = None
    value['kinetics']['selection'] = value['kinetics']['selection'][:1]
    report, _ = render_report(value)
    assert b'curve_100' in report and b'curve_180' not in report
    assert b'No valid kinetics regression' in report
    assert b'Not generated for the current selection' in report


def test_report_fingerprint_changes_with_selection_and_notes():
    value = snapshot()
    before = fingerprint(value, 'Title', '')
    assert fingerprint(value, 'Title', 'Changed notes') != before
    value['kinetics']['selection'][0]['Include'] = False
    assert fingerprint(value, 'Title', '') != before


def test_project_format_one_remains_readable():
    document = json.loads(save_project(b'data', 'data.csv', recipe()))
    document['schema_version'] = 1
    document.pop('options')
    assert load_project(json.dumps(document).encode())['options'] == DEFAULT_OPTIONS


@pytest.mark.parametrize('update', [
    {'n_modes': 19}, {'alpha_reg': float('nan')}, {'show_fits': 'false'},
    {'kinetics_exclusions': ['x', 'x']}, {'tts_reference_temp': -274},
    {'report_title': 'x'*201}, {'unrecognized_option': True},
])
def test_project_rejects_invalid_downstream_choices(update):
    value = recipe()
    value['options'] = update
    with pytest.raises(ValueError):
        save_project(b'data', 'data.csv', value)


def test_project_preserves_downstream_choices():
    value = recipe()
    value['options'] = {'kinetics_exclusions': ['curve_1'], 'kinetic_component': 'Fast (tau1)',
                        'kinetics_model_type': 'Eyring (Transition State)', 'opt_alpha': False,
                        'alpha_reg': .25, 'n_modes': 80, 'report_notes': 'sample A'}
    restored = load_project(save_project(b'data', 'data.csv', value))
    for key, expected in value['options'].items():
        assert restored['options'][key] == expected
