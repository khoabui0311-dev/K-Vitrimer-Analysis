"""Save/load formatting independently of the experimental data."""
import streamlit as st

from can_relax.io.figure_style import apply_style, capture_style, load_style, save_style, with_automatic_axes
from can_relax.io.publication_fields import FIELDS


def preserve_style():
    # Keep settings even when their figure, legend or manual-axis controls hide.
    for key in (*FIELDS, 'publication_format_name'):
        if key in st.session_state:
            st.session_state[key] = st.session_state[key]


def render_style_controls():
    def remember_current():
        try:
            st.session_state['figure_style_undo'] = {
                'settings': capture_style(st.session_state),
                'name': st.session_state.get('publication_format_name', 'My figure format'),
            }
        except ValueError:
            # Reset can still recover invalid manually entered axis limits.
            st.session_state.pop('figure_style_undo', None)

    def restore(data, automatic_axes):
        try:
            style = load_style(data)
            if automatic_axes:
                style['settings'] = with_automatic_axes(style['settings'])
            remember_current()
            apply_style(st.session_state, style['settings'])
            st.session_state['publication_format_name'] = style['name']
            st.session_state['format_notice'] = 'Figure format applied. Check axis limits and units when using it with different data.'
        except ValueError as exc:
            st.session_state['format_error'] = str(exc)

    def reset():
        remember_current()
        apply_style(st.session_state, {})
        st.session_state['publication_format_name'] = 'My figure format'
        st.session_state['format_notice'] = 'Publication formatting reset to defaults.'

    def undo():
        previous = st.session_state.get('figure_style_undo')
        if previous:
            apply_style(st.session_state, previous['settings'])
            st.session_state['publication_format_name'] = previous['name']
            st.session_state.pop('figure_style_undo', None)
            st.session_state['format_notice'] = 'Previous figure formatting restored.'

    with st.expander('Save or load figure formatting', expanded=False):
        st.caption('Reuse figure sizes, fonts, colors, labels, legends, axes and fit visibility. Format files contain no measurements. Projects also save these choices.')
        st.text_input('Format name', value='My figure format', max_chars=80, key='publication_format_name')
        download_slot = st.container()
        upload = st.file_uploader('Load figure format (.vstyle)', type=['vstyle'], key='figure_style_upload', max_upload_size=1)
        valid_upload = False
        if upload is not None:
            try:
                preview = load_style(upload.getvalue())
                settings = preview['settings']
                size = (f"{settings['pub_w']:g} × {settings['pub_h']:g} cm"
                        if 'pub_w' in settings else 'Default figure size')
                st.info(f"{preview['name']} · {size} · {len(settings)} saved settings")
                valid_upload = True
            except ValueError as exc:
                st.error(f'Cannot load this format: {exc}')
        automatic_axes = st.checkbox('Use automatic axis limits when applying', value=False,
            key='figure_style_auto_axes', help='Useful for a different dataset. Keep fonts, colors, units and scales while recalculating axis limits.')
        st.button('Apply figure format', disabled=not valid_upload, on_click=restore,
                  args=(upload.getvalue() if upload else b'', automatic_axes), key='apply_figure_style')
        st.button('Reset figure formatting', on_click=reset, key='reset_figure_style')
        st.button('Undo format apply or reset', disabled='figure_style_undo' not in st.session_state,
                  on_click=undo, key='undo_figure_style')
        if 'format_notice' in st.session_state:
            st.success(st.session_state.pop('format_notice'))
        if 'format_error' in st.session_state:
            st.error(st.session_state.pop('format_error'))
    return download_slot


def render_style_download(slot):
    with slot:
        try:
            payload = save_style(capture_style(st.session_state), st.session_state['publication_format_name'])
            st.download_button('Save figure format', payload, 'figure_format.vstyle', mime='application/json',
                                key='save_figure_style', on_click='ignore')
        except ValueError as exc:
            st.warning(str(exc))
