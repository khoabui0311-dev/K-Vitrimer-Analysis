"""An explicit, per-curve model comparison workspace."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from can_relax.core.comparison import compare_models
from can_relax.core.selection import prepare_curve


@st.cache_data
def cached_comparison(temperature, data, Tg, plateau, fixed):
    return compare_models(temperature, data, Tg, plateau, fixed)


def _use_model():
    st.session_state['analysis_fit_model'] = st.session_state['comparison_chosen_model']
    st.session_state['project_rerun_analysis'] = True


def render_comparison(curves, timing, exclusions, Tg, plateau, fixed, identity):
    st.subheader('Which model describes this curve?')
    st.caption('Compare Maxwell, single KWW and two-Maxwell on the same selected observations. This comparison applies to one curve at a time.')
    options = {r['Curve_ID']: r for r in curves if r['Temp'] >= Tg}
    if not options:
        st.info('No curves are above the selected Tg threshold.')
        return
    selected = st.selectbox('Curve for model comparison', list(options),
                            format_func=lambda cid: f"{cid} · {options[cid]['Temp']:g} °C",
                            key=f'comparison_curve_{identity}')
    comparison_key = (identity, selected)
    if st.button('Compare three models', key='compare_three_models', type='primary'):
        record = options[selected]
        try:
            data, _, _ = prepare_curve(record['Data'], **timing[selected], excluded=exclusions.get(selected, []))
            with st.spinner('Fitting three models to the same observations…'):
                comparison = cached_comparison(record['Temp'], data, Tg, plateau, fixed)
            st.session_state['model_comparison'] = {'key': comparison_key, **comparison}
            st.session_state['comparison_id'] = identity
        except ValueError as exc:
            st.error(str(exc))
    comparison = st.session_state.get('model_comparison')
    if not comparison or comparison['key'] != comparison_key:
        st.info('Run the comparison to see overlaid fits, residuals and a model score table.')
        return
    table = pd.DataFrame(comparison['rows'])
    st.dataframe(table, hide_index=True, width='stretch')
    st.caption(f'Plateau policy: {plateau}. Lower AICc/BIC favours a model under the residual-error assumptions. These scores do not establish a molecular mechanism or resolve poorly constrained parameters. Missing ΔAICc means the score is unavailable.')
    st.download_button('Download model comparison CSV', table.to_csv(index=False),
                       f'{selected}_model_comparison.csv', key='comparison_csv')
    if not comparison['results']:
        st.warning('None of the requested models fitted this curve.')
        return
    fit_plot, residual_plot = go.Figure(), go.Figure()
    reference = next(iter(comparison['results'].values()))['Raw']
    fit_plot.add_trace(go.Scatter(x=reference['t'], y=reference['g'], mode='markers',
                                 name='Measured', marker=dict(color='#94a3b8', size=5)))
    for (name, result), color in zip(comparison['results'].items(), ['#0f766e', '#7c3aed', '#ea580c']):
        raw, fit = result['Raw'], result['Fits'][name]
        fit_plot.add_trace(go.Scatter(x=raw['t'], y=fit['curve'], name=name, mode='lines', line=dict(color=color)))
        residual_plot.add_trace(go.Scatter(x=raw['t'], y=fit['residuals'], name=name, mode='lines', line=dict(color=color)))
    log_time = st.checkbox('Log time in comparison', value=False, key='comparison_log_time')
    for figure in (fit_plot, residual_plot):
        figure.update_layout(xaxis_title='Elapsed time (s)', xaxis_type='log' if log_time else 'linear',
                             height=360, margin=dict(l=20, r=20, t=20, b=20))
    fit_plot.update_yaxes(title='G(t) / G(reference)')
    residual_plot.update_yaxes(title='Observed − fitted (normalized)')
    residual_plot.add_hline(y=0, line_dash='dash')
    left, right = st.columns(2)
    with left:
        st.markdown('**Measured curve and fits**')
        st.plotly_chart(fit_plot, width='stretch')
    with right:
        st.markdown('**Residuals**')
        st.plotly_chart(residual_plot, width='stretch')
    st.selectbox('Model to use for the full analysis', list(comparison['results']), key='comparison_chosen_model')
    st.button('Use this model and refit all curves', on_click=_use_model, key='apply_comparison_model')
    st.caption('This is your selection, not an automatic recommendation. All temperatures are still fitted independently.')
