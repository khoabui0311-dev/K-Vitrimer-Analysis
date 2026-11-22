"""Save/load formatting independently of the experimental data."""
import streamlit as st

from can_relax.io.figure_style import apply_style, capture_style, load_style, save_style
from can_relax.io.publication_fields import FIELDS


def preserve_style():
    # Keep settings even when their figure, legend or manual-axis controls hide.
    for key in (*FIELDS, 'publication_format_name'):
        if key in st.session_state:
            st.session_state[key] = st.session_state[key]


def render_style_controls():
    def restore(data):
        try:
            style = load_style(data)
            apply_style(st.session_state, style['settings'])
            st.session_state['publication_format_name'] = style['name']
            st.session_state['format_notice'] = 'Figure format applied. Check axis limits and units when using it with different data.'
        except ValueError as exc:
            st.session_state['format_error'] = str(exc)

    def reset():
        apply_style(st.session_state, {})
        st.session_state['publication_format_name'] = 'My figure format'
        st.session_state['format_notice'] = 'Publication formatting reset to defaults.'

    with st.expander('Save or load figure formatting', expanded=False):
        st.caption('Reuse figure sizes, fonts, colors, labels, legends, axes and fit visibility. Format files contain no measurements. Projects also save these choices.')
        st.text_input('Format name', value='My figure format', max_chars=80, key='publication_format_name')
        download_slot = st.container()
        upload = st.file_uploader('Load figure format (.vstyle)', type=['vstyle'], key='figure_style_upload', max_upload_size=1)
        st.button('Apply figure format', disabled=upload is None, on_click=restore,
                  args=(upload.getvalue() if upload else b'',), key='apply_figure_style')
        st.button('Reset figure formatting', on_click=reset, key='reset_figure_style')
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
