"""Explicit report preparation with stale-download invalidation."""
import streamlit as st
from can_relax.io.analysis_report import fingerprint, render_report


def render_report_export(snapshot):
    st.subheader('4 · Keep a record of this analysis')
    st.caption('Create one offline report with fit tables, curves, residuals, kinetics, warnings and provenance. Generated mastercurves and model comparisons are included when available.')
    title = st.text_input('Report title', value='Relaxation analysis', max_chars=200, key='report_title')
    notes = st.text_area('Research notes', max_chars=4000, key='report_notes',
                         placeholder='Sample identity, preparation, test conditions, and interpretation notes…')
    # Notes are part of the fingerprint; other settings were captured earlier in this rerun.
    snapshot['options']['report_title'] = title
    snapshot['options']['report_notes'] = notes
    identity = fingerprint(snapshot, title, notes)
    prepared = st.session_state.get('prepared_report')
    if prepared and prepared['identity'] != identity:
        st.session_state.pop('prepared_report', None)
        prepared = None
        st.info('The analysis or report notes changed. Prepare a new report to update the downloads.')
    if st.button('Prepare analysis report', type='primary', disabled=not snapshot['curves'], key='prepare_report'):
        with st.spinner('Preparing the report and numerical snapshot…'):
            report, numeric = render_report(snapshot, title, notes)
        prepared = {'identity': identity, 'html': report, 'json': numeric}
        st.session_state['prepared_report'] = prepared
    if prepared:
        left, right = st.columns(2)
        left.download_button('Download analysis report (HTML)', prepared['html'], 'vitrifit_report.html',
                             mime='text/html', key='download_report_html', width='stretch')
        right.download_button('Download numerical snapshot (JSON)', prepared['json'], 'vitrifit_snapshot.json',
                              mime='application/json', key='download_report_json', width='stretch')
        st.success('Report ready. It opens offline; use your browser’s Print command to save a PDF.')
    st.caption('The report is a fixed record, not a project file. Save a project separately to reopen the analysis. It contains selected measurements and your notes; review them before sharing.')
