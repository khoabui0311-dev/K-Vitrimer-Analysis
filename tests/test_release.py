"""Release identity, traceable exports and honest Arrhenius regression intervals."""
from pathlib import Path
import numpy as np
import pytest
from can_relax import __version__
from can_relax.version import APP_NAME, VERSION
from can_relax.core.kinetics import KineticsEngine, R_GAS


def test_release_identity_matches_launcher_and_citation():
    from desktop.launcher import APP_NAME as desktop_name, VERSION as desktop_version
    assert APP_NAME == desktop_name == 'VitriFit'
    assert VERSION == desktop_version == __version__
    citation = (Path(__file__).resolve().parents[1] / 'CITATION.cff').read_text(encoding='utf-8')
    assert f'version: "{VERSION}"' in citation


def test_arrhenius_does_not_clip_or_hide_negative_slope():
    temperatures = np.array([100., 120., 140., 160., 180.])
    tau = np.exp(-30000 / (R_GAS*(temperatures+273.15)) + 14.)
    result = KineticsEngine().fit_arrhenius(temperatures, tau)
    assert result['Ea'] == pytest.approx(-30.)
    assert 'Nonpositive' in result['Warning']
    assert result['Ea_CI95'][1] < 0


def test_arrhenius_interval_crossing_zero_is_reported():
    result = KineticsEngine().fit_arrhenius([100,120,140,160,180], [90,110,85,105,100])
    lo, hi = result['Ea_CI95']
    assert lo < 0 < hi
    assert 'includes zero' in result['Warning']


def test_two_temperatures_have_no_estimable_interval():
    result = KineticsEngine().fit_arrhenius([100,140], [100,10])
    assert result['Ea_CI95'] is None
    assert 'Two observations' in result['Warning']


def test_provenance_has_version_and_method(monkeypatch):
    import json
    import streamlit as st
    from streamlit.testing.v1 import AppTest
    real_download = st.download_button
    captured = {}

    def capture(label, data, *args, **kwargs):
        if label == 'Download analysis provenance JSON':
            captured.update(json.loads(data))
        return real_download(label, data, *args, **kwargs)

    monkeypatch.setattr(st, 'download_button', capture)
    app = AppTest.from_file('can_relax/gui/app.py', default_timeout=60).run()
    app.checkbox(key='use_example_data').check().run()
    next(b for b in app.button if 'Run Analysis' in b.label).click().run()
    assert not app.exception
    assert captured['software'] == {'name': APP_NAME, 'version': VERSION}
    assert captured['temperature_law_imposed_on_curve_fits'] is False
    assert 'Independent per-temperature' in captured['fit_method']
