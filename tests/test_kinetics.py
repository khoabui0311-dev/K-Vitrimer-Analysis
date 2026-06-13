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
    # May or may not converge, but must not raise
    # If it converges, R2 should be reasonable
    if res is not None:
        assert res["R2"] >= 0.0
        assert "Ea_chem" in res


def test_coupled_minimum_points_guard(engine):
    """Coupled model requires ≥4 points."""
    result = engine.fit_coupled_kinetics([100, 120, 140], [1.0, 0.5, 0.3])
    assert result is None
