"""Bulk, reversible measurement review using original observation numbers."""
import re

import plotly.graph_objects as go
import streamlit as st

from can_relax.core.selection import prepare_curve
from can_relax.core.state import clear_analysis


def parse_point_numbers(text, count):
    """Parse inclusive original-row ranges without silently accepting typos."""
    if not text.strip():
        return []
    points = set()
    for token in text.split(','):
        match = re.fullmatch(r'\s*(\d+)\s*(?:-\s*(\d+)\s*)?', token)
        if not match:
            raise ValueError('Use point numbers or inclusive ranges, for example: 1-20, 35, 50-65.')
        start, end = int(match[1]), int(match[2] or match[1])
        if not 1 <= start <= end <= count:
            raise ValueError(f'Use increasing ranges between 1 and {count}.')
        points.update(range(start, end + 1))
    return sorted(points)


def selected_point_numbers(event, count):
    """Read stable original-row IDs, never trace-local Plotly point indices."""
    numbers = set()
    for point in event.get('selection', {}).get('points', []):
        number = point.get('customdata')
        if isinstance(number, (list, tuple)) and len(number) == 1:
            number = number[0]
        if isinstance(number, (int, float)) and not isinstance(number, bool) and 1 <= number <= count and int(number) == number:
            numbers.add(int(number))
    return sorted(numbers)


def render_point_review(chosen, settings, dataset_id):
    cid = chosen['Curve_ID']
    exclusions = st.session_state['point_exclusions']
    scope = f"{dataset_id}_{cid}_{st.session_state.get('source_epoch', 0)}"
    state_key = f'point_review_{scope}'
    state = st.session_state.setdefault(state_key, {'revision': 0, 'history': []})

    def replace_exclusions(new, remember=True):
        previous = sorted(exclusions.get(cid, []))
        new = sorted(set(new))
        if new == previous:
            return
        if remember:
            state['history'] = (state['history'] + [previous])[-30:]
        exclusions[cid] = new
        state['revision'] += 1
        clear_analysis(st.session_state)

    def apply_selection(points, exclude):
        current = set(exclusions.get(cid, []))
        replace_exclusions(current.union(points) if exclude else current.difference(points))

    def undo():
        if state['history']:
            replace_exclusions(state['history'].pop(), remember=False)

    _, preview, audit = prepare_curve(chosen['Data'], **settings, excluded=exclusions.get(cid, []))
    st.markdown('**Select many points at once**')
    st.caption('Drag a box over the graph, or choose the lasso in its toolbar. Then exclude or restore the highlighted points. Your source file stays unchanged.')
    plot = go.Figure()
    accepted = preview['Keep'] & preview['In time window']
    for mask, label, color in [(accepted, 'Kept', '#238b45'),
                               (~preview['Keep'], 'Manually excluded', '#d73027'),
                               (preview['Keep'] & ~preview['In time window'], 'Outside time window', '#94a3b8')]:
        points = preview.loc[mask]
        plot.add_trace(go.Scatter(x=points['Elapsed time (s)'], y=points['Modulus'], mode='markers',
            name=label, marker=dict(color=color), customdata=points['Point'].tolist(),
            hovertemplate='Point %{customdata}<br>Elapsed time %{x} s<br>Modulus %{y} MPa<extra>%{fullData.name}</extra>'))
    plot.update_layout(xaxis_title='Elapsed time (s)', yaxis_title='Modulus (MPa)', height=360,
                       dragmode='select', legend=dict(orientation='h', y=1.15), margin=dict(t=50))
    event = st.plotly_chart(plot, width='stretch', on_select='rerun', selection_mode=('points', 'box', 'lasso'),
        key=f"points_graph_{scope}_{settings}_{state['revision']}", config={'displaylogo': False})
    method = st.radio('Select points using', ['Graph', 'Point numbers', 'Time interval'], horizontal=True,
                       key=f'points_method_{scope}')
    selected = []
    if method == 'Graph':
        selected = selected_point_numbers(event, len(preview))
    elif method == 'Point numbers':
        specification = st.text_input('Point numbers or ranges', placeholder='1-20, 35, 50-65', key=f'points_range_{scope}')
        try:
            selected = parse_point_numbers(specification, len(preview))
        except ValueError as exc:
            st.warning(str(exc))
    else:
        left, right = st.columns(2)
        start = left.number_input('From elapsed time (s)', value=float(preview['Elapsed time (s)'].min()), key=f'points_start_{scope}')
        end = right.number_input('Through elapsed time (s)', value=float(preview['Elapsed time (s)'].max()), key=f'points_end_{scope}')
        if start > end:
            st.warning('The start time must not exceed the end time.')
        else:
            selected = preview.loc[preview['Elapsed time (s)'].between(start, end), 'Point'].tolist()
    st.caption(f'{len(selected)} points highlighted for this action. Changes apply only to this curve.')
    left, right = st.columns(2)
    left.button('Exclude highlighted points', key=f'points_exclude_{scope}', disabled=not selected,
                on_click=apply_selection, args=(selected, True), width='stretch', type='primary')
    right.button('Restore highlighted points', key=f'points_restore_{scope}', disabled=not selected,
                 on_click=apply_selection, args=(selected, False), width='stretch')
    left, right = st.columns(2)
    left.button('Undo last point edit', key=f'points_undo_{scope}', disabled=not state['history'], on_click=undo, width='stretch')
    right.button('Restore all manually excluded points', key=f'points_restore_all_{scope}',
                 disabled=not exclusions.get(cid), on_click=replace_exclusions, args=([],), width='stretch')
    st.caption('Restoring points does not override the loading origin or time cutoff. Run Analysis after editing.')
    with st.expander('Individual points and reviewed data table'):
        edited = st.data_editor(preview, hide_index=True, height=300,
            disabled=[c for c in preview.columns if c != 'Keep'],
            key=f"points_{scope}_{settings}_{state['revision']}")
        revised = edited.loc[~edited['Keep'], 'Point'].astype(int).tolist()
        if sorted(revised) != sorted(exclusions.get(cid, [])):
            replace_exclusions(revised)
            st.rerun()
    st.caption(f"{audit['points_after_manual_selection']} of {len(preview)} measurements kept. Point numbers refer to imported observations, before sorting or downsampling. Automatic peak/drift preprocessing still follows this selection.")
    st.download_button('Download reviewed points CSV', preview.to_csv(index=False), f'{cid}_review.csv')
