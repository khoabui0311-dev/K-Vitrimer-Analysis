"""
Extended kinetics tests for KineticsEngine.

Covers:
- Arrhenius (existing, extended with edge cases)
- Eyring-Polanyi (ΔH‡, ΔS‡ recovery)
- VFT / Vogel-Fulcher-Tammann
- Coupled WLF-Arrhenius
- Minimum data guards
"""
import numpy as np
import pytest
from can_relax.core.kinetics import KineticsEngine

R = 8.314462          # J/mol·K
H_P = 6.62607015e-34  # J·s
K_B = 1.380649e-23    # J/K


@pytest.fixture
def engine():
    return KineticsEngine()


def _arrhenius_taus(temps_C, Ea_J, tau0):
    T_K = np.array(temps_C) + 273.15
    return (tau0 * np.exp(Ea_J / (R * T_K))).tolist()


# ────────────────────────────────────────────────────────────────────
# Arrhenius
# ────────────────────────────────────────────────────────────────────
def test_arrhenius_Ea_recovery(engine):
    temps = [100, 120, 140, 160, 180]
    taus = _arrhenius_taus(temps, 80000.0, 1e-10)
    res = engine.fit_arrhenius(temps, taus)
    assert res is not None
    assert res["R2"] > 0.999
    assert abs(res["Ea"] - 80.0) < 0.5   # ±0.5 kJ/mol


def test_arrhenius_high_Ea(engine):
    """Verify recovery of a high-Ea system (150 kJ/mol)."""
    temps = [160, 180, 200, 220, 240]
    taus = _arrhenius_taus(temps, 150000.0, 1e-15)
    res = engine.fit_arrhenius(temps, taus)
    assert res is not None
    assert abs(res["Ea"] - 150.0) < 1.0


def test_arrhenius_minimum_points_guard(engine):
    result = engine.fit_arrhenius([100.0], [1.5])
    assert result is None


# ────────────────────────────────────────────────────────────────────
# Eyring-Polanyi
# ────────────────────────────────────────────────────────────────────
def test_eyring_dH_recovery(engine):
    """
    Eyring: τ·T = (h/kB) · exp(ΔH‡/(R·T)) · exp(-ΔS‡/R)
    Recover ΔH‡ = 80 kJ/mol, ΔS‡ = -50 J/(mol·K).
    """
    dH_J = 80000.0   # J/mol
    dS = -50.0       # J/(mol·K)
    temps_C = [100, 120, 140, 160, 180]
    T_K = np.array(temps_C) + 273.15
    # Compute taus from Eyring equation
    taus = ((H_P / K_B) * np.exp(dH_J / (R * T_K)) * np.exp(-dS / R) / T_K).tolist()

    res = engine.fit_eyring(temps_C, taus)
    assert res is not None
    assert res["R2"] > 0.999
    assert abs(res["dH"] - 80.0) < 1.0    # ±1 kJ/mol


def test_eyring_returns_dS(engine):
    dH_J = 90000.0
    dS = 20.0
    temps_C = [130, 150, 170, 190]
    T_K = np.array(temps_C) + 273.15
    taus = ((H_P / K_B) * np.exp(dH_J / (R * T_K)) * np.exp(-dS / R) / T_K).tolist()
    res = engine.fit_eyring(temps_C, taus)
    assert res is not None
    assert "dS" in res
    assert abs(res["dS"] - dS) < 5.0    # ±5 J/(mol·K)


def test_eyring_minimum_points_guard(engine):
    result = engine.fit_eyring([100.0], [1.5])
    assert result is None


# ────────────────────────────────────────────────────────────────────
# VFT / Vogel-Fulcher-Tammann
# ────────────────────────────────────────────────────────────────────
def test_vft_recovery(engine):
    """
    VFT: ln(τ) = A + B / (T - T0)
    True params: A=-5, B=1500, T0=350 K.
    """
    A_true = -5.0
    B_true = 1500.0
    T0_true = 350.0   # K

    temps_C = [100, 120, 140, 160, 180, 200]
    T_K = np.array(temps_C) + 273.15
    ln_tau = A_true + B_true / (T_K - T0_true)
    taus = np.exp(ln_tau).tolist()

    res = engine.fit_vft(temps_C, taus)
    assert res is not None
    assert res["R2"] > 0.99
    assert abs(res["Params"]["B"] - B_true) < 50.0       # ±50 K
    assert abs(res["Params"]["T0"] - T0_true) < 20.0     # ±20 K


def test_vft_minimum_points_guard(engine):
    """VFT requires ≥4 points."""
    result = engine.fit_vft([100, 120, 140], [1.0, 0.5, 0.3])
    assert result is None


# ────────────────────────────────────────────────────────────────────
# Coupled WLF-Arrhenius
# ────────────────────────────────────────────────────────────────────
def test_coupled_runs_with_tg(engine):
    """Coupled model should converge with Tg provided."""
    # Use Arrhenius-like data so there's a sensible answer
    temps = [100, 120, 140, 160, 180]
    taus = _arrhenius_taus(temps, 85000.0, 1e-11)
    res = engine.fit_coupled_kinetics(temps, taus, Tg=60.0)
    assert res is not None
    assert res["R2"] > 0.99
    assert "Ea_chem" in res


def test_coupled_minimum_points_guard(engine):
    """Coupled model requires ≥4 points."""
    result = engine.fit_coupled_kinetics([100, 120, 140], [1.0, 0.5, 0.3])
    assert result is None

@pytest.mark.parametrize('method', ['fit_arrhenius', 'fit_eyring', 'fit_vft', 'fit_van_t_hoff', 'fit_coupled_kinetics'])
@pytest.mark.parametrize('temps,values', [
    ([100]*6, [1]*6),
    ([100,120,140,160,180,200], [1,2,3,4,5]),
    ([100,120,140,160,180,200], [1,2,0,4,5,6]),
    ([100,120,140,160,180,200], [1,2,-1,4,5,6]),
    ([100,120,140,160,180,200], [1,2,np.inf,4,5,6]),
    ([-273.15,120,140,160,180,200], [1,2,3,4,5,6]),
    ([100,np.nan,140,160,180,200], [1,2,3,4,5,6]),
])
def test_invalid_inputs_return_none(engine, method, temps, values):
    assert getattr(engine, method)(temps, values) is None


@pytest.mark.parametrize('method,error', [('fit_arrhenius','Ea_std'), ('fit_eyring','dH_std')])
def test_two_observations_do_not_claim_uncertainty(engine, method, error):
    result = getattr(engine, method)([100,120], [10,1])
    assert result is not None
    assert np.isnan(result[error])
    assert result['Warning']


def test_van_t_hoff_predictions_match_equation_and_result(engine):
    from can_relax.core.kinetics import predict_van_t_hoff
    T = np.linspace(373.15, 473.15, 8)
    expected = 0.02*T/(1+np.exp(-80000/(R*T)+200/R))
    np.testing.assert_allclose(predict_van_t_hoff(T, .02, 80000, 200), expected)
    result = engine.fit_van_t_hoff(T-273.15, expected)
    assert result is not None
    assert 'G0_max' not in result and 'G0_max' not in result['Params']
    np.testing.assert_allclose(result['Plot']['y_pred'], predict_van_t_hoff(T, **result['Params']))
    np.testing.assert_allclose(result['Plot']['y_pred'], expected, rtol=1e-4)
    assert result['Units']['A'] == 'MPa/K'


def test_coupled_prediction_stable_beyond_exp_range():
    from can_relax.core.kinetics import predict_coupled
    T = np.array([300.,400.])
    actual = predict_coupled(T, 1000., 80000., 1000., 1500., 250.)
    assert np.all(np.isfinite(actual))
    expected = 1000 + np.logaddexp(80000/(R*T), 1500/(T-250))
    np.testing.assert_allclose(actual, expected)


@pytest.mark.parametrize('tg,n', [(60.,4), (None,5)])
def test_coupled_requires_residual_degrees_of_freedom(engine, tg, n):
    assert engine.fit_coupled_kinetics(np.linspace(100,200,n), np.linspace(10,1,n), Tg=tg) is None


def test_van_t_hoff_requires_four_temperatures(engine):
    assert engine.fit_van_t_hoff([100,120,140], [10,8,6]) is None

@pytest.mark.parametrize('tg', [60., None])
def test_coupled_fit_uses_shared_prediction(engine, tg):
    from can_relax.core.kinetics import predict_coupled
    temps = np.linspace(100,240,10)
    T = temps + 273.15
    tau = np.exp(predict_coupled(T,-20,85000,-8,1500,283.15))
    result = engine.fit_coupled_kinetics(temps,tau,Tg=tg)
    assert result is not None
    assert result['R2'] > 0.99
    np.testing.assert_allclose(result['Plot']['y_pred'], predict_coupled(T, **result['Params']))
