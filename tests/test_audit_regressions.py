"""Counterexamples found during the September 2026 whole-project audit."""
import io
import numpy as np
import pandas as pd
import pytest
import matplotlib.pyplot as plt
from PIL import Image

from can_relax.core.extrapolation import maxwell_equivalent_tv
from can_relax.core.simulator import MaterialSimulator
from can_relax.core.selection import prepare_curve
from can_relax.core.tts import TTSEngine
from can_relax.gui.exporting import figure_bytes
from can_relax.gui.tabs.tab_comparison import parse_manual_data
from can_relax.io.parser import parse_curve_records


@pytest.mark.parametrize('header', ['Stress (MPa)', 'Storage modulus (MPa)', "G' (MPa)", 'G_prime', 'Loss modulus'])
def test_reject_non_relaxation_measurements(tmp_path, header):
    path = tmp_path / 'data.csv'
    path.write_text(f'Temp,Time,{header}\n120,0,2\n120,1,1')
    with pytest.raises(ValueError, match='relaxation modulus'):
        parse_curve_records(path)


def test_unit_conversion_overflow_is_rejected(tmp_path):
    path = tmp_path / 'data.csv'
    path.write_text('Temp,Time (min),Modulus\n120,1e308,2')
    with pytest.raises(ValueError, match='after unit conversion'):
        parse_curve_records(path)


@pytest.mark.parametrize('text', ['100,10\n120,bad', '100,10\n120', '100,inf', '-274,1', '100,1,-2'])
def test_comparison_parse_is_transactional(text):
    with pytest.raises(ValueError):
        parse_manual_data(text)


@pytest.mark.parametrize('index', [1.5, np.nan, np.inf])
def test_point_numbers_are_not_silently_truncated(index):
    with pytest.raises(ValueError, match='integers'):
        prepare_curve(pd.DataFrame({'Time': [0, 1], 'Modulus': [2, 1]}), excluded=[index])


@pytest.mark.parametrize('fmt', ['png', 'bmp', 'jpg', 'tiff'])
@pytest.mark.parametrize('dpi', [100, 200])
def test_export_actual_resolution_and_format(fmt, dpi):
    fig, ax = plt.subplots(figsize=(2, 1))
    ax.plot([0, 1], [1, 0])
    try:
        with Image.open(io.BytesIO(figure_bytes(fig, fmt, dpi))) as img:
            assert img.size == (2*dpi, dpi)
            assert img.format == {'jpg': 'JPEG'}.get(fmt, fmt.upper())
            assert img.info['dpi'][0] == pytest.approx(dpi, abs=.1)
    finally:
        plt.close(fig)


def test_cmyk_export_and_allocation_guard():
    fig, _ = plt.subplots(figsize=(2, 1))
    try:
        for fmt in ('tiff', 'jpg'):
            with Image.open(io.BytesIO(figure_bytes(fig, fmt, 100, 'CMYK'))) as img:
                assert img.mode == 'CMYK'
        with pytest.raises(ValueError, match='CMYK requires'):
            figure_bytes(fig, 'png', 100, 'CMYK')
        with pytest.raises(ValueError, match='megapixels'):
            figure_bytes(fig, 'png', 10000)
        assert figure_bytes(fig, 'pdf').startswith(b'%PDF')
        assert b'<svg' in figure_bytes(fig, 'svg')
    finally:
        plt.close(fig)


def test_threshold_rejects_nonphysical_roots():
    assert np.isnan(maxwell_equivalent_tv(0, 0, 1))
    assert np.isnan(maxwell_equivalent_tv(-1000, 0, 1))
    assert np.isnan(maxwell_equivalent_tv(1000, 100, 1))
    slope = 80000/8.314462
    intercept = np.log(1e6)-slope/373.15
    assert maxwell_equivalent_tv(slope, intercept, 1) == pytest.approx(100)


def test_simulator_dual_window_covers_slow_mode():
    p = {'Ea': 80., 'Tv': 120., 'G_plateau': 2., 'beta': .8,
         'tau_factor': 10000., 'fraction_fast': .2}
    t, g, tau = MaterialSimulator().simulate_curve(120, 'Dual_KWW', p)
    assert tau == pytest.approx(5e5)
    assert t[-1] == pytest.approx(tau*10000*100)
    assert g[-1] < .001*g[0]
    for updates in ({'tau_factor': -1}, {'G_plateau': 0}, {'beta': 0}, {'Tv': -273.15}):
        with pytest.raises(ValueError):
            MaterialSimulator().simulate_curve(120, 'Dual_KWW', dict(p, **updates))
    with pytest.raises(ValueError):
        MaterialSimulator().simulate_curve(np.nan, 'Maxwell', p)


def test_tts_extrapolated_normalization_corrects_delayed_reference():
    records = []
    for index, tau in enumerate((50., 200.)):
        t = np.geomspace(30, 2000, 100)
        f = np.exp(-(t/tau)**.5)
        records.append({'Temp': 100+20*index, 'Curve_ID': str(index), 'Valid': True,
            'Best_Model': 'Single_KWW', 'Fits': {'Single_KWW': {'success': True,
            'popt': np.array([tau, .5]), 'G_inf': 0}},
            'Raw': {'t': t, 'g': f/f[0], 'G0': 2*f[0]}})
    master = TTSEngine().generate_mastercurve(records, ref_temp=100, normalization='model_initial')
    np.testing.assert_allclose(master['Master_g'], np.exp(-(master['Master_t']/50)**.5))
    absolute = TTSEngine().generate_mastercurve(records, ref_temp=100, normalization='absolute')
    np.testing.assert_allclose(absolute['Master_g'], 2*master['Master_g'])


def test_raw_crossing_retains_recrossings_hidden_by_downsampling():
    from can_relax.core.analyzer import CurveAnalyzer
    from can_relax.core.observations import relaxation_crossing
    t = np.linspace(0, 50, 5001)
    g = np.exp(-t/10)
    g[1002] = 1/np.e + .001
    result = CurveAnalyzer().fit_one_temp(120, pd.DataFrame({'Time': t, 'Modulus': g}), fit_model='Maxwell')
    raw = result['Raw']
    assert len(raw['full_t']) > len(raw['t'])
    assert relaxation_crossing(raw['full_t'], raw['full_g'])['status'] == 'ambiguous'
    assert relaxation_crossing(raw['t'], raw['g'])['status'] == 'observed'


def test_comparison_edits_and_failed_reanalysis_clear_results(monkeypatch):
    from streamlit.testing.v1 import AppTest
    app = AppTest.from_file('can_relax/gui/app.py', default_timeout=60).run()
    app.text_area(key='data_1').set_value('100,100\n120,10\n140,1').run()
    next(b for b in app.button if 'Analyze All' in b.label).click().run()
    assert not app.exception
    assert app.session_state['comparison_results']
    app.text_area(key='data_1').set_value('100,100\n120,bad').run()
    assert not app.exception
    assert 'comparison_results' not in app.session_state
    assert app.session_state['comparison_samples']['sample_1']['data'] == []
    app.button(key='delete_1').click().run()
    assert not app.exception
    assert app.text_area(key='data_1').value == ''


def test_publication_presets_legends_and_no_figure_leak(monkeypatch):
    from streamlit.testing.v1 import AppTest
    from can_relax.gui.tabs import tab_pub_main
    figures = {}
    def capture(fig, title, *args):
        figures[title] = fig
    monkeypatch.setattr(tab_pub_main, 'save_and_download', capture)
    initial = set(plt.get_fignums())
    app = AppTest.from_file('can_relax/gui/app.py', default_timeout=60).run()
    app.checkbox(key='use_example_data').check().run()
    next(b for b in app.button if 'Run Analysis' in b.label).click().run()
    app.checkbox(key='sh_fig3').check().run()
    app.checkbox(key='sh_fig4').check().run()
    app.checkbox(key='eyr_leg').uncheck().run()
    app.checkbox(key='vh_leg').uncheck().run()
    app.selectbox(key='pub_preset').select('ACS/RSC Double-Column (170 x 140 mm)').run()
    assert not app.exception
    assert figures['Eyring'].axes[0].get_legend() is None
    assert figures['Van_t_Hoff'].axes[0].get_legend() is None
    np.testing.assert_allclose(figures['Relaxation_Curves'].get_size_inches()*2.54, [17, 14])
    assert set(plt.get_fignums()) == initial
