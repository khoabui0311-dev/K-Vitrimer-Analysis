"""An inspectable fitting-reliability workspace, separate from kinetics selection."""
import json
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from can_relax.core.models import PRONY
from can_relax.core.reliability import METHOD, check_prony_stability, diagnostic_row
from can_relax.io.analysis_report import plain


@st.cache_data(show_spinner=False, max_entries=128)
def cached_stability(record):
    return check_prony_stability(record)


def render_reliability(results, model, identity):
    st.subheader('Can you trust the fitted parameters?')
    st.caption('Review the numerical search, residual patterns and sensitivity to the experiment window before interpreting relaxation times.')
    if not results:
        st.info('Select at least one fitted curve to inspect reliability.')
        return
    table = pd.DataFrame([diagnostic_row(record, model) for record in results])
    st.dataframe(table, hide_index=True, width='stretch', column_config={
        'R²': st.column_config.NumberColumn(format='%.5f'),
        'RMSE (normalized)': st.column_config.NumberColumn(format='%.5g'),
        'Adjacent residual correlation': st.column_config.NumberColumn(format='%.3f')})
    st.download_button('Download fit diagnostics CSV', table.to_csv(index=False), 'fit_diagnostics.csv', key='reliability_diagnostics_csv')
    options = {record['Curve_ID']: record for record in results}
    selected = st.selectbox('Curve to inspect', list(options), key=f'reliability_curve_{identity}',
                            format_func=lambda cid: f"{cid} · {options[cid]['Temp']:g} °C")
    record = options[selected]
    fit, raw = record['Fits'][model], record['Raw']
    for flag in fit['flags']:
        st.warning(flag)
    left, right = st.columns(2)
    with left:
        st.markdown('**Residuals: observed minus fitted**')
        residuals = go.Figure(go.Scatter(x=raw['t'], y=fit['residuals'], mode='lines+markers',
                                       marker=dict(size=4), line=dict(color='#0f766e'), name='Residual'))
        residuals.add_hline(y=0, line_dash='dash')
        residuals.update_layout(height=300, margin=dict(l=15, r=15, t=15, b=15),
                                xaxis_title='Elapsed time (s)', yaxis_title='Normalized residual')
        st.plotly_chart(residuals, width='stretch', key='reliability_residuals')
        st.caption('Adjacent-point correlation is descriptive, including on uneven time grids. |r| ≥ 0.5 flags a pattern; it is not a statistical significance test. Near-zero residuals have no reported correlation.')
    with right:
        optimization = fit.get('optimization')
        if optimization:
            st.markdown('**Do different starts agree?**')
            a, b = st.columns(2)
            a.metric('Converged starts', f"{optimization['converged_starts']} / {optimization['attempted_starts']}")
            b.metric('Near-best solutions', optimization['near_best_starts'])
            trials = [trial for trial in optimization['trials'] if trial['success']]
            scatter = go.Figure(go.Scatter(x=[trial['parameters'][1] for trial in trials],
                y=[trial['parameters'][2] for trial in trials], mode='markers',
                text=[f"Start {trial['start']} · RSS {trial['rss']:.6g}" for trial in trials],
                hovertemplate='%{text}<br>Fast: %{x:.6g} s<br>Slow: %{y:.6g} s<extra></extra>',
                marker=dict(size=9, color=[trial['rss'] for trial in trials], colorscale='Teal')))
            scatter.update_layout(height=220, margin=dict(l=15, r=15, t=15, b=15),
                xaxis=dict(type='log', title='Fast time (s)'), yaxis=dict(type='log', title='Slow time (s)'))
            # Do not magnify negligible optimizer differences into an apparent wide spread.
            for axis, index in [('xaxis', 1), ('yaxis', 2)]:
                values = np.log10([trial['parameters'][index] for trial in trials])
                padding = max(.05, float(np.ptp(values)) * .1)
                scatter.update_layout(**{axis: {'range': [float(values.min()-padding), float(values.max()+padding)]}})
            st.plotly_chart(scatter, width='stretch', key='reliability_starts')
            st.caption('The lowest residual sum of squares (RSS) wins. Near-best means RSS within max(0.1% of best RSS, 10⁻¹²). More than 25% spread in either time triggers review. Agreement across starts does not establish physical identifiability.')
            with st.expander('Inspect every starting guess'):
                st.dataframe(pd.DataFrame(plain(optimization['trials'])), hide_index=True, width='stretch')
        else:
            st.info('Multiple starting guesses and window sensitivity are currently available for the two-Maxwell model. Residual review is available for every model.')
    if model != PRONY:
        return
    st.markdown('**How much do the fast and slow times change?**')
    st.caption(METHOD)
    if st.button('Check stability of selected curves', key='run_fit_stability', type='primary'):
        evidence = {}
        progress = st.progress(0, text='Checking retained observations and shorter windows…')
        for index, record in enumerate(results):
            evidence[record['Curve_ID']] = cached_stability(record)
            progress.progress((index + 1) / len(results), text=f"Checked {index + 1} of {len(results)} curves")
        st.session_state['fit_reliability'] = {'analysis_id': identity, 'curves': evidence}
        progress.empty()
    saved = st.session_state.get('fit_reliability', {})
    evidence = {cid: item for cid, item in saved.get('curves', {}).items() if cid in options} if saved.get('analysis_id') == identity else {}
    if not evidence:
        st.info('Run the stability check to compare the current fit, all retained points and two shorter time windows. Your analysis and kinetics selection stay unchanged.')
        return
    missing = set(options) - set(evidence)
    if missing:
        st.info(f'{len(missing)} selected curve(s) have not been checked. Run again to include them.')
    rows = [row for item in evidence.values() for row in item['rows']]
    changes = pd.DataFrame(rows)
    flagged = sum(any(row.get('Above 20% review threshold') for row in item['rows']) for item in evidence.values())
    unavailable = sum(row['Status'] != 'Fitted' for row in rows)
    if flagged or unavailable:
        st.warning(f'{flagged} curve(s) exceed the 20% sensitivity review threshold; {unavailable} scenario(s) could not be fitted. Review the rows below before using these times in kinetics.')
    else:
        st.info('No time changes exceeded 20% in these checks. This does not prove the modes are identifiable; also inspect the fit warnings and residuals.')
    display_columns = ['Curve', 'Scenario', 'Status', 'Points', 'Tau fast (s)', 'Tau slow (s)',
                       'Fast change (%)', 'Slow change (%)', 'Above 20% review threshold']
    st.dataframe(changes.reindex(columns=display_columns), hide_index=True, width='stretch', column_config={
        name: st.column_config.NumberColumn(format='%.3g')
        for name in ['Tau fast (s)', 'Tau slow (s)', 'Fast change (%)', 'Slow change (%)']})
    with st.expander('Full scenario parameters and review notes'):
        st.dataframe(changes, hide_index=True, width='stretch')
    chosen_rows = [row for row in rows if row['Curve'] == selected and row['Status'] == 'Fitted']
    if chosen_rows:
        figure = go.Figure()
        for mode, color in [('Fast', '#0f766e'), ('Slow', '#d97706')]:
            figure.add_bar(x=[row['Scenario'] for row in chosen_rows], y=[row[f'{mode} change (%)'] for row in chosen_rows],
                           name=mode, marker_color=color)
        figure.add_hline(y=20, line_dash='dash', line_color='#64748b')
        figure.add_hline(y=-20, line_dash='dash', line_color='#64748b')
        figure.update_layout(height=320, yaxis_title='Change from current fit (%)', barmode='group',
                             margin=dict(l=15, r=15, t=15, b=15))
        st.plotly_chart(figure, width='stretch', key='reliability_changes')
    st.download_button('Download stability CSV', changes.to_csv(index=False), 'fit_stability.csv', key='reliability_csv')
    st.download_button('Download reliability JSON', json.dumps(plain({'analysis_id': identity, 'method': METHOD,
        'diagnostics': {cid: options[cid]['Fits'][model] for cid in evidence}, 'stability': list(evidence.values())}),
        indent=2, allow_nan=False), 'fit_reliability.json', mime='application/json', key='reliability_json')
    st.caption('The Report tab includes the checks for its selected curves. Projects restore the analysis recipe; run stability checks again after reopening, and keep these exports as a fixed record.')
