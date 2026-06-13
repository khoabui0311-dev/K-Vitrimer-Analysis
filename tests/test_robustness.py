import pytest
import numpy as np
import pandas as pd
from can_relax.core.analyzer import CurveAnalyzer

def test_short_time_window_robustness():
    analyzer = CurveAnalyzer()
    
    # Incomplete relaxation (only relaxes from 1.0 to 0.8)
    t = np.logspace(0, 2, 50)
    g = 1.0 * np.exp(-t / 1000.0)  # tau = 1000, so at t=100 it's 0.904
    df = pd.DataFrame({'Time': t, 'Modulus': g})
    
    result = analyzer.fit_one_temp(100.0, df, fit_model='Maxwell')
    
    # It should still be valid
    assert result['Valid'] is True
    # The dynamic range is small, so Quality should drop
    assert result['Quality'] < 1.0 
    
    # It should still fit without crashing
    assert 'Maxwell' in result['Fits']
    
def test_noisy_data_robustness():
    analyzer = CurveAnalyzer()
    
    t = np.logspace(0, 4, 100)
    g_clean = 1.0 * np.exp(-t / 500.0)
    
    # Inject large random noise (10% of G0)
    np.random.seed(42)
    noise = np.random.normal(0, 0.1, size=len(g_clean))
    g_noisy = g_clean + noise
    
    df = pd.DataFrame({'Time': t, 'Modulus': g_noisy})
    
    result = analyzer.fit_one_temp(100.0, df, fit_model='Maxwell')
    
    assert result['Valid'] is True
    # The fit should still execute
    assert 'Maxwell' in result['Fits']
    
    # The high noise and wiggles should significantly reduce the quality metric
    assert result['Quality'] < 0.9
