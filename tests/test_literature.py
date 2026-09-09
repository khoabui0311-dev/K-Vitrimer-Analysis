import pytest
import numpy as np
from can_relax.core.kinetics import KineticsEngine

def test_example_arrhenius_regression():
    """
    Regression on an illustrative, uncited dataset; not experimental validation.
    """
    engine = KineticsEngine()
    
    # Illustrative example dataset
    temps_C = [130.0, 140.0, 150.0, 160.0]
    # Example characteristic relaxation times in seconds
    taus = [10000.0, 3000.0, 1000.0, 350.0]
    
    # The dummy generic dataset yields Ea = ~162 kJ/mol
    expected_Ea = 162.0
    
    result = engine.fit_arrhenius(temps_C, taus)
    
    assert result is not None
    assert result["Type"] == "Arrhenius"
    
    # Loose numerical sanity check; no literature or experimental claim.
    Ea_fit = result["Ea"]
    assert abs(Ea_fit - expected_Ea) / expected_Ea < 0.15
