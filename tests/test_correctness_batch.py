import numpy as np
import pandas as pd
import pytest
from unittest.mock import patch

from can_relax.core.analyzer import CurveAnalyzer
from can_relax.core.observations import relaxation_crossing
from can_relax.core.spectrum import SpectrumAnalyzer
from can_relax.core.state import analysis_identity, clear_analysis
from can_relax.core.tts import TTSEngine


@pytest.mark.parametrize('start', [0, .01, 1, 30, 100])
def test_late_start_kww_recovery(start):
    t = np.r_[0, np.geomspace(.01, 3000, 200)] if start == 0 else np.geomspace(start, 3000, 200)
    g = 2.5 * np.exp(-(t/300)**.5)
    result = CurveAnalyzer().fit_one_temp(150, pd.DataFrame({'Time': t, 'Modulus': g}), fit_model='Single_KWW')
    assert result['Valid']
    assert result['Raw']['t'][0] == start
    np.testing.assert_allclose(result['Fits']['Single_KWW']['popt'], [300, .5], rtol=.001)
    np.testing.assert_allclose(result['Fits']['Single_KWW']['curve'] * result['Raw']['G0'], g, rtol=.001)


def test_failed_fit_not_valid():
    t = np.geomspace(.01, 100, 100)
    with patch('can_relax.core.analyzer.curve_fit', side_effect=RuntimeError('test failure')):
        result = CurveAnalyzer().fit_one_temp(150, pd.DataFrame({'Time':t, 'Modulus':np.exp(-t/10)}))
    assert not result['Valid']
    assert result['Best_Model'] is None
    assert all(np.isnan(f['curve']).all() for f in result['Fits'].values())


def test_crossing_not_reached_or_ambiguous():
    t = np.linspace(0, 100, 100)
    assert relaxation_crossing(t, np.exp(-t/1000))['status'] == 'not_reached'
    assert relaxation_crossing([0,1,2,3], [1,.2,.5,.1])['status'] == 'ambiguous'


def test_crossing_interval_and_plot_position_are_distinct():
    t = np.linspace(30, 200, 10000)
    result = relaxation_crossing(t, np.exp(-t/50))
    assert result['status'] == 'observed'
    assert result['tau'] == pytest.approx(50, abs=.001)
    assert result['crossing_time'] == pytest.approx(80, abs=.001)


@pytest.mark.parametrize('amplitude', [.006, .6, 60])
@pytest.mark.parametrize('subtract', [True, False])
def test_spectrum_reconstructs_input_units(amplitude, subtract):
    t = np.r_[0, np.geomspace(.01, 200, 200)]
    g = amplitude * ((.4 if subtract else 0) + .6*np.exp(-t/10))
    engine = SpectrumAnalyzer()
    grid, weights = engine.compute_continuous_spectrum(t, g, alpha=1e-5, subtract_G_eq=subtract)
    reconstructed = np.exp(-t[:,None]/grid) @ weights + engine.last_G_eq
    assert np.all(np.isfinite(grid))
    assert np.max(np.abs(reconstructed-g))/g[0] < .025


def test_data_content_invalidation():
    settings = {'temperatures': [120,130]}
    assert analysis_identity(b'old data', settings) != analysis_identity(b'new data', settings)
    state = dict(results=[1], master_data=[1], spec_results=[1], kinetics_df=[1], analysis_id='old', unrelated=2)
    clear_analysis(state)
    assert state == {'unrelated': 2}


def test_nonfinite_optimizer_result_is_rejected():
    t = np.geomspace(.01, 100, 100)
    with patch('can_relax.core.analyzer.curve_fit', return_value=(np.array([np.nan]), np.eye(1))):
        result = CurveAnalyzer().fit_one_temp(150, pd.DataFrame({'Time':t, 'Modulus':np.exp(-t/10)}), fit_model='Maxwell')
    assert not result['Valid']


def test_tts_preserves_replicate_shift_entries():
    analyzer = CurveAnalyzer()
    results = []
    for i, (temperature, tau) in enumerate([(100, 50), (100, 60), (140, 10)]):
        t = np.geomspace(.01, 500, 100)
        result = analyzer.fit_one_temp(temperature, pd.DataFrame({'Time':t, 'Modulus':np.exp(-t/tau)}), fit_model='Maxwell')
        result['Curve_ID'] = f'curve_{i}'
        results.append(result)
    master = TTSEngine().generate_mastercurve(results, ref_temp=100)
    assert len(master['Shifts']) == 3
    np.testing.assert_allclose(list(master['Shifts'].values()), np.array([50,60,10])/55, rtol=.001)
    assert master['Tau_ref'] == pytest.approx(55, rel=.001)
    assert master['Reference_curve_ids'] == ['curve_0', 'curve_1']
    reordered = TTSEngine().generate_mastercurve(results[::-1], ref_temp=100)
    assert reordered['Shifts'] == pytest.approx(master['Shifts'])
    explicit = TTSEngine().generate_mastercurve(results, ref_curve_id='curve_1')
    assert explicit['Shifts']['curve_1'] == pytest.approx(1)
    assert explicit['Tau_ref'] == pytest.approx(60, rel=.001)
    assert explicit['Reference_mode'] == 'curve'
    with pytest.raises(ValueError, match='exactly one'):
        TTSEngine().generate_mastercurve(results, ref_curve_id='missing')
    with pytest.raises(ValueError, match='does not match'):
        TTSEngine().generate_mastercurve(results, ref_temp=140, ref_curve_id='curve_0')


def test_labels_disambiguate_only_visible_replicates():
    from can_relax.gui.labels import curve_labels
    records = [{'Temp': temp, 'Curve_ID': cid} for temp, cid in [(100,'a'),(100,'b'),(140,'c')]]
    assert curve_labels(records) == {'a':'100°C (a)', 'b':'100°C (b)', 'c':'140°C'}
    assert curve_labels(records[1:]) == {'b':'100°C', 'c':'140°C'}


def test_dual_kww_late_start_recovers_separated_modes():
    t = np.geomspace(2, 10000, 220)
    g = .35*np.exp(-(t/20)**.8) + .65*np.exp(-(t/700)**.6)
    result = CurveAnalyzer().fit_one_temp(150, pd.DataFrame({'Time':t, 'Modulus':g}), fit_model='Dual_KWW')
    assert result['Valid']
    np.testing.assert_allclose(result['Fits']['Dual_KWW']['popt'], [.35,20,.8,700,.6], rtol=.01)
