import pytest
import numpy as np
from can_relax.core.kinetics import KineticsEngine

def test_arrhenius_kinetics():
    engine = KineticsEngine()
    
    # Fake Arrhenius data
    # tau = tau0 * exp(Ea / (R*T))
    # ln(tau) = ln(tau0) + Ea / (R*T)
    # Ea = 80,000 J/mol (80 kJ/mol)
    # tau0 = 1e-10
    
    Ea_true = 80000.0
    tau0_true = 1e-10
    R = 8.314462
    
    temps_C = [100.0, 120.0, 140.0, 160.0, 180.0]
    temps_K = np.array(temps_C) + 273.15
    taus = tau0_true * np.exp(Ea_true / (R * temps_K))
    
    result = engine.fit_arrhenius(temps_C, taus.tolist())
    
    assert result is not None
    assert result["Type"] == "Arrhenius"
    assert result["R2"] > 0.99
    
    # Error should be very small
    assert abs(result["Ea"] - (Ea_true / 1000.0)) < 0.1
