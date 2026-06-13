import pytest
import numpy as np
import pandas as pd
from can_relax.core.analyzer import CurveAnalyzer
from can_relax.core.kinetics import KineticsEngine

def test_synthetic_maxwell_recovery():
    analyzer = CurveAnalyzer()
    tau_true = 500.0
    G0_true = 1.0
    
    t = np.logspace(0, 4, 100)
    g = G0_true * np.exp(-t / tau_true)
    df = pd.DataFrame({'Time': t, 'Modulus': g})
    
    # Run fit
    result = analyzer.fit_one_temp(150.0, df, fit_model='Maxwell')
    
    assert result['Valid'] is True
    assert 'Maxwell' in result['Fits']
    
    popt = result['Fits']['Maxwell']['popt']
    tau_fit = popt[0]
    r2 = result['Fits']['Maxwell']['r2']
    
    assert r2 > 0.999
    assert abs(tau_fit - tau_true) / tau_true < 0.01  # 1% tolerance

def test_synthetic_kww_recovery():
    analyzer = CurveAnalyzer()
    tau_true = 300.0
    beta_true = 0.7
    G0_true = 1.0
    
    t = np.logspace(0, 4, 100)
    g = G0_true * np.exp(-(t / tau_true)**beta_true)
    df = pd.DataFrame({'Time': t, 'Modulus': g})
    
    # Run fit
    result = analyzer.fit_one_temp(150.0, df, fit_model='Single_KWW')
    
    assert result['Valid'] is True
    assert 'Single_KWW' in result['Fits']
    
    popt = result['Fits']['Single_KWW']['popt']
    tau_fit = popt[0]
    beta_fit = popt[1]
    r2 = result['Fits']['Single_KWW']['r2']
    
    assert r2 > 0.999
    assert abs(tau_fit - tau_true) / tau_true < 0.05
    assert abs(beta_fit - beta_true) / beta_true < 0.05

def test_synthetic_vft_recovery():
    engine = KineticsEngine()
    
    A_true = -10.0
    B_true = 1500.0
    T0_true_K = 320.0
    
    temps_C = np.array([100.0, 110.0, 120.0, 130.0, 140.0])
    temps_K = temps_C + 273.15
    
    ln_tau = A_true + B_true / (temps_K - T0_true_K)
    taus = np.exp(ln_tau)
    
    result = engine.fit_vft(temps_C.tolist(), taus.tolist())
    
    assert result is not None
    assert result["Type"] == "VFT"
    assert result["R2"] > 0.999
    
    A_fit = result["Params"]["A"]
    B_fit = result["Params"]["B"]
    T0_fit = result["Params"]["T0"]
    
    assert abs(A_fit - A_true) < 0.1
    assert abs(B_fit - B_true) / B_true < 0.05
    assert abs(T0_fit - T0_true_K) / T0_true_K < 0.05
