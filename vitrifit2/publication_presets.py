"""Capture every existing v1 Publication widget without redefining plot styles.

This is a compatibility adapter; it does not change any scientific calculation,
Matplotlib format, or renderer. Presets use the v2 SQLite data store.
"""
from __future__ import annotations

import numbers

from .persistence import VitriFitStore

PREFIXES = ("pub_", "sh_fig", "pl_", "plx_", "ply_", "eyr_", "vh_")
EXACT_KEYS = {"f2_model"}


def is_publication_key(key: str) -> bool:
    return key.startswith(PREFIXES) or key in EXACT_KEYS


def capture_publication_settings(state) -> dict:
    """Save the exact values of currently instantiated publication controls."""
    settings = {}
    for key in state:
        if not is_publication_key(key):
            continue
        value = state[key]
        if isinstance(value, (str, bool, numbers.Integral, numbers.Real)):
            settings[key] = int(value) if isinstance(value, numbers.Integral) and not isinstance(value, bool) else (
                float(value) if isinstance(value, numbers.Real) and not isinstance(value, bool) else value)
    return settings


def apply_publication_settings(state, settings: dict) -> int:
    """Set widget keys BEFORE v1 creates them, preserving its own field controls."""
    restored = 0
    for key, value in settings.items():
        if is_publication_key(key) and isinstance(value, (str, bool, int, float)):
            state[key] = value
            restored += 1
    if "pub_preset" in settings:
        # The existing v1 UI resets dimensions when pub_size_preset differs.
        state["pub_size_preset"] = settings["pub_preset"]
    return restored


def render_preset_controls(st):
    """Insert at the start of render_publication, before existing controls."""
    store = VitriFitStore.home() if hasattr(VitriFitStore, "home") else VitriFitStore(
        __import__("pathlib").Path.home() / ".vitrifit2")
    with st.expander("💾 Saved publication figure styles", expanded=False):
        st.caption("Preserve all current v1 Publication controls and reuse the same settings next session.")
        presets = store.list_figure_presets()
        names = {p["id"]: p["name"] for p in presets}
        selected = st.selectbox("Load saved style", [""] + list(names),
                                format_func=lambda i: names.get(i, "Choose saved style"),
                                key="v2_saved_style_selected")
        if st.button("Restore selected style", disabled=not selected, key="v2_restore_style"):
            preset = store.get_figure_preset(selected)
            restored = apply_publication_settings(st.session_state, preset["settings"])
            st.toast(f"Restored {restored} publication settings")
            st.rerun()
        name = st.text_input("New style name", placeholder="ACS manuscript / Figure 2",
                             key="v2_saved_style_name")
        if st.button("Save current publication style", disabled=not name.strip(),
                     key="v2_save_style"):
            settings = capture_publication_settings(st.session_state)
            if not settings:
                st.warning("Open an analyzed dataset and configure the publication figures first.")
            else:
                store.save_figure_preset(name.strip(), settings)
                st.success("Saved the current publication settings to your local library.")
