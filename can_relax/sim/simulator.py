import numpy as np
import pandas as pd

R_GAS = 8.314462  # J/mol*K

class MaterialSimulator:
    def __init__(self):
        pass

    def simulate_curve(self, temp_C, model_type, params, time_points=None):
        """
        Generates synthetic G(t). 
        - Uses Viscosity-defined Tv (tau = 1e12/G).
        - Supports Advanced Dual-Mode (separate Ea/Beta).
        """
        if time_points is None:
            time_points = np.logspace(-4, 8, 500)
            
        T_K = temp_C + 273.15
        
        # --- PHYSICS PARAMETERS ---
        Ea_kJ = params.get('Ea', 80.0)
        Tv_C  = params.get('Tv', 100.0)
        Tg_C  = params.get('Tg', 50.0)
        G_MPa = params.get('G_plateau', 1.0)
        
        Ea_J = Ea_kJ * 1000.0
        Tv_K = Tv_C + 273.15
        G_Pa = G_MPa * 1e6
        
        # 1. CALCULATE TAU AT TV (The Physics Fix)
        # Viscosity = 10^12 Pa.s at Tv -> tau = eta / G
        tau_at_Tv = 1e12 / G_Pa 
        
        # 2. CALCULATE TAU_1 (Fast Mode / Main Mode)
        if temp_C < Tg_C:
            tau_1 = 1e20 # Frozen
        else:
            exponent1 = (Ea_J / R_GAS) * (1.0/T_K - 1.0/Tv_K)
            tau_1 = tau_at_Tv * np.exp(exponent1)
        
        # 3. GENERATE CURVE
        if model_type == "Maxwell":
            g = np.exp(-(time_points / tau_1))
            
        elif model_type == "Single_KWW":
            beta = params.get('beta', 0.8)
            g = np.exp(-((time_points / tau_1) ** beta))
            
        elif model_type == "Dual_KWW":
            # --- ADVANCED DUAL MODE ---
            beta1 = params.get('beta', 0.8)
            fraction = params.get('fraction_fast', 0.5)
            
            # Mode 2 (Slow) Properties
            beta2 = params.get('beta_2', beta1)
            Ea_2_kJ = params.get('Ea_2', Ea_kJ) 
            separation_factor = params.get('tau_factor', 50.0)
            
            # Calculate Tau 2
            if temp_C < Tg_C:
                tau_2 = 1e20
            else:
                # Mode 2 Anchor: Slower at Tv
                tau_Tv_2 = tau_at_Tv * separation_factor
                
                # Mode 2 Shift: Own Activation Energy
                Ea_2_J = Ea_2_kJ * 1000.0
                exponent2 = (Ea_2_J / R_GAS) * (1.0/T_K - 1.0/Tv_K)
                tau_2 = tau_Tv_2 * np.exp(exponent2)
            
            # Combine
            term1 = fraction * np.exp(-((time_points / tau_1) ** beta1))
            term2 = (1 - fraction) * np.exp(-((time_points / tau_2) ** beta2))
            g = term1 + term2
            
        else:
            g = np.zeros_like(time_points)

        if temp_C < Tg_C:
            g = np.ones_like(time_points)

        return time_points, g, tau_1