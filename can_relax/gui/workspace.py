"""Main-workspace summaries and portable-project restoration."""
import io
import pandas as pd
import streamlit as st

from can_relax.core.state import analysis_identity, clear_analysis
from can_relax.core.selection import prepare_curve
from can_relax.io.project import DEFAULT_SETTINGS, load_project, save_project
from can_relax.io.project_options import DEFAULT_OPTIONS
from can_relax.version import VERSION


def source_file(data, filename):
    stream = io.BytesIO(data)
    stream.name = filename
    return stream


def open_project(state, data, parse_source):
    """Validate the complete recipe against its data before replacing the open workspace."""
    project = load_project(data)
    curves = parse_source(source_file(project['source_bytes'], project['filename']))
    curve_ids = {r['Curve_ID'] for r in curves}
    if not curves or set(project['curve_timing']) != curve_ids or not set(project['point_exclusions']).issubset(curve_ids):
        raise ValueError('Saved curve settings do not match the source data.')
    if project['selected_curves'] is not None and not set(project['selected_curves']).issubset(curve_ids):
        raise ValueError('Saved curve selection does not match the source data.')
    options = project['options']
    if not set(options['kinetics_exclusions']).issubset(curve_ids):
        raise ValueError('Saved kinetics selection does not match the source data.')
    reference = options['tts_reference_curve']
    if reference is not None and (reference not in curve_ids or
            next(r['Temp'] for r in curves if r['Curve_ID'] == reference) != options['tts_reference_temp']):
        raise ValueError('Saved reference curve does not match the reference temperature.')
    if options['tts_reference_temp'] is not None and options['tts_reference_temp'] not in [r['Temp'] for r in curves]:
        raise ValueError('Saved reference temperature is not in the source data.')
    for record in curves:
        prepare_curve(record['Data'], **project['curve_timing'][record['Curve_ID']],
                      excluded=project['point_exclusions'].get(record['Curve_ID'], []))
    clear_analysis(state)
    for key in list(state):
        if key.startswith(('timing_', 'points_', 'selection_', 'review_curve_', 'point_review_', 'kinetics_editor_', 'tts_reference_')):
            state.pop(key, None)
    state.update(project['settings'])
    state.update(options)
    state['restore_kinetics_exclusions'] = options['kinetics_exclusions']
    state.pop('kinetics_exclusion_context', None)
    state['project_regenerate_master'] = options['tts_generated']
    state['use_example_data'] = False
    state['project_source'] = source_file(project['source_bytes'], project['filename'])
    state['source_epoch'] = state.get('source_epoch', 0) + 1
    dataset = analysis_identity(project['source_bytes'], {})
    state['review_dataset'] = dataset
    state['review_timing_id'] = f"{dataset}_{project['settings']['time_origin']}_{project['settings']['time_cutoff']}"
    state['review_timing_table'] = pd.DataFrame([
        {'Curve_ID': r['Curve_ID'], 'Temperature (C)': r['Temp'],
         'Loading origin (s)': project['curve_timing'][r['Curve_ID']]['origin'],
         'Cutoff (s)': project['curve_timing'][r['Curve_ID']]['cutoff']} for r in curves])
    state['point_exclusions'] = project['point_exclusions']
    state['project_restore_selection'] = project['selected_curves']
    state['project_rerun_analysis'] = project['analysed']
    state['project_notice'] = (f"Opened {project['filename']}. Data, point exclusions and fit settings restored. "
                               'Kinetics, spectrum and curve display choices restored. Saved analyses and mastercurves are recalculated. Publication styling must be set separately.')
    if project['saved_version'] != VERSION:
        state['project_notice'] += f" Saved with {project['saved_version']}; running {VERSION}. Results may differ."
    if project['schema_version'] == 1:
        state['project_notice'] += ' This older project has no downstream choices; defaults were used for those settings.'
    state.pop('model_comparison', None)
    state.pop('prepared_report', None)


def render_project_open(parse_source):
    with st.sidebar.expander('Open a saved project', expanded=True):
        upload = st.file_uploader('VitriFit project', type=['vfit'], key='project_upload', max_upload_size=36)
        if st.button('Open project', disabled=upload is None, width='stretch'):
            try:
                open_project(st.session_state, upload.getvalue(), parse_source)
                st.rerun()
            except (ValueError, OSError) as exc:
                st.error(f'Project could not be opened: {exc}')
        st.caption('A project includes your original data and analysis recipe. Results are recalculated when reopened.')
        st.button('New project', on_click=st.session_state.clear, help='Clear this workspace. Save your project and exports first.', width='stretch')


def render_project_save(source, filename, timing, exclusions, current_id):
    if not source or not timing:
        return
    settings = {key: st.session_state.get(key, value) for key, value in DEFAULT_SETTINGS.items()}
    if settings['analysis_fit_model'] == 'Dual_KWW':
        settings['plateau_mode'] = 'Zero'
    options = {key: st.session_state.get(key, value) for key, value in DEFAULT_OPTIONS.items()}
    options['tts_generated'] = bool(st.session_state.get('master_data'))
    is_current = bool(st.session_state.get('results')) and st.session_state.get('analysis_id') == current_id
    if not is_current:
        options.update(kinetics_exclusions=[], tts_reference_temp=None, tts_reference_curve=None, tts_generated=False)
    recipe = {'settings': settings, 'curve_timing': timing, 'point_exclusions': exclusions,
              'options': options,
              'selected_curves': st.session_state.get(f'selection_{current_id}'),
              'analysed': is_current}
    with st.sidebar.container():
        st.subheader('Keep your work')
        try:
            data = save_project(source, filename, recipe)
            st.download_button('Save project', data, 'analysis.vfit', mime='application/json',
                               key='save_project', width='stretch')
            st.caption('Includes source data, fitting, kinetics selections, mastercurve choices, spectrum settings and report notes. Keep exported results separately as a record of this calculation.')
        except ValueError as exc:
            st.warning(str(exc))


def render_data_summary(curves, filename):
    st.caption(f'Source: {filename} · internal units: seconds, MPa, °C')
    a, b, c = st.columns(3)
    a.metric('Imported curves', len(curves))
    b.metric('Measurements', f"{sum(len(r['Data']) for r in curves):,}")
    temperatures = [r['Temp'] for r in curves]
    c.metric('Temperature range', f'{min(temperatures):g}–{max(temperatures):g} °C')


def render_result_summary(results, model):
    st.subheader('3 · Understand your results')
    flagged = sum(bool(r['Fits'][model]['flags']) for r in results)
    a, b, c = st.columns(3)
    a.metric('Fitted curves', len(results))
    b.metric('Curves to review', flagged)
    c.metric('Model', {'Single_KWW': 'Single KWW', 'Dual_KWW': 'Dual KWW'}.get(model, model))
    if flagged:
        st.warning(f'{flagged} fitted curve(s) need review. Check residuals and parameter warnings before interpreting relaxation times.')
    else:
        st.info('Fits are ready for review. Inspect residuals and compare models before interpreting the fitted times.')
