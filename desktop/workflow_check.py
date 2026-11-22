"""Exercise import → review → fit → save → fresh reopen → export in Streamlit.

Only file-picker input and download capture are adapted for AppTest; the parser,
review controls, analysis, serialization, figures and report generation are real.
"""
import json
from unittest.mock import patch

import numpy as np


def verify_workflow(app_path, source_bytes, filename='workflow.csv'):
    import streamlit as st
    from streamlit.testing.v1 import AppTest
    from can_relax.core.models import PRONY
    from can_relax.gui.workspace import source_file
    from can_relax.io.project import load_project
    from can_relax.io.figure_style import load_style

    original_upload, original_download = st.file_uploader, st.download_button
    uploads = {'source': source_bytes}
    downloads = {}

    def upload(*args, **kwargs):
        key = kwargs.get('key', '')
        if key.startswith('source_upload_') and 'source' in uploads:
            return source_file(uploads['source'], filename)
        if key == 'project_upload' and 'project' in uploads:
            return source_file(uploads['project'], 'reviewed.vfit')
        return original_upload(*args, **kwargs)

    def download(label, data, *args, **kwargs):
        downloads[label] = data
        downloads[kwargs.get('key') or label] = data
        return original_download(label, data, *args, **kwargs)

    def check(app):
        if app.exception:
            raise RuntimeError(str(app.exception))

    with patch.object(st, 'file_uploader', upload), patch.object(st, 'download_button', download):
        app = AppTest.from_file(str(app_path), default_timeout=120).run()
        check(app)
        app.selectbox(key='analysis_fit_model').select(PRONY).run()
        next(x for x in app.radio if x.label == 'Select points using').set_value('Point numbers').run()
        next(x for x in app.text_input if x.label == 'Point numbers or ranges').set_value('2-4').run()
        next(x for x in app.button if x.label == 'Exclude highlighted points').click().run()
        check(app)
        excluded = dict(app.session_state['point_exclusions'])
        next(x for x in app.button if 'Run Analysis' in x.label).click().run()
        check(app)
        expected = {r['Curve_ID']: np.array(r['Fits'][PRONY]['popt']) for r in app.session_state['results'] if r['Valid']}
        if not expected:
            raise RuntimeError('Imported workflow produced no valid fits.')
        app.button(key='run_fit_stability').click().run()
        check(app)
        original_checks = app.session_state['fit_reliability']['curves']
        if set(original_checks) != set(expected):
            raise RuntimeError('Stability checks did not cover every fitted curve.')
        app.text_input(key='publication_format_name').set_value('Workflow format').run()
        app.checkbox(key='pub_kin_showfit').uncheck().run()
        saved = downloads['Save project']
        project = load_project(saved)
        if project['source_bytes'] != source_bytes or project['point_exclusions'] != excluded:
            raise RuntimeError('Saved source or exclusions changed.')
        if project['publication_style']['pub_kin_showfit'] is not False:
            raise RuntimeError('Publication display choice was not saved.')
        # A genuinely fresh AppTest session, not a rerun of the existing session.
        uploads.clear()
        uploads['project'] = saved
        reopened = AppTest.from_file(str(app_path), default_timeout=120).run()
        next(x for x in reopened.button if x.label == 'Open project').click().run()
        check(reopened)
        if reopened.session_state['point_exclusions'] != excluded:
            raise RuntimeError('Reopened point exclusions changed.')
        restored = {r['Curve_ID']: r['Fits'][PRONY]['popt'] for r in reopened.session_state['results'] if r['Valid']}
        if restored.keys() != expected.keys():
            raise RuntimeError('Reopening changed the fitted curves.')
        for cid in expected:
            if not np.allclose(restored[cid], expected[cid], rtol=1e-9, atol=1e-10):
                raise RuntimeError('Reopening changed fitted parameter values.')
        if reopened.checkbox(key='pub_kin_showfit').value:
            raise RuntimeError('Reopening lost fit visibility.')
        if 'fit_reliability' in reopened.session_state:
            raise RuntimeError('Project incorrectly restored old stability results instead of a recipe.')
        reopened.button(key='run_fit_stability').click().run()
        check(reopened)
        for cid, evidence in reopened.session_state['fit_reliability']['curves'].items():
            if evidence['rows'] != original_checks[cid]['rows']:
                raise RuntimeError('Repeated stability checks changed after reopening.')
        style = load_style(downloads['save_figure_style'])
        if style['settings']['pub_kin_showfit'] is not False:
            raise RuntimeError('Standalone format export lost fit visibility.')
        reopened.button(key='prepare_report').click().run()
        check(reopened)
        prepared = reopened.session_state['prepared_report']
        snapshot = json.loads(prepared['json'])
        if len(snapshot['curves']) != len(expected) or b'<svg' not in prepared['html']:
            raise RuntimeError('Report did not contain curves and embedded vector figures.')
        if len(snapshot['fit_reliability']) != len(expected):
            raise RuntimeError('Report did not include the completed stability checks.')
        if 'First 80%' not in downloads['reliability_csv']:
            raise RuntimeError('Stability CSV did not contain the window checks.')
        if 'Tau 1 fast (s)' not in downloads['dl_fit_params']:
            raise RuntimeError('Fit CSV is missing two-Maxwell times.')
        next(x for x in reopened.button if x.label == 'Prepare SVG / PDF downloads').click().run()
        check(reopened)
        payloads = [v.encode() if isinstance(v, str) else v for v in downloads.values() if isinstance(v, (str, bytes))]
        if not any(v.startswith(b'%PDF') for v in payloads) or not any(b'<svg' in v[:2000] for v in payloads):
            raise RuntimeError('Publication PDF/SVG downloads were not generated.')
        return reopened, {'import': filename.rsplit('.', 1)[-1], 'reviewed_points': 3,
                          'curves': len(expected), 'fresh_session_reopen': 'identical fitted parameters',
                          'project_source_and_exclusions': 'preserved',
                          'stability_reopen': 'recomputed with identical scenario results',
                          'exports': ['fit CSV', 'diagnostics CSV', 'stability CSV', 'reliability JSON', 'project VFIT', 'format VSTYLE', 'report HTML', 'snapshot JSON', 'publication SVG', 'publication PDF']}
