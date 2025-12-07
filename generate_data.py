
import pandas as pd
import numpy as np
import os

def generate_toy_data():
    t = np.logspace(-2, 4, 200)
    data = {}
    
    temps = [120, 130, 140, 150]
    for T in temps:
        tau = 100 * (10 ** (3 * (150 - T) / 30))  # Fake Arrhenius
        g = 0.9 * np.exp(-(t/tau)**0.8) + 0.05
        # Add some noise
        noise = np.random.normal(0, 0.005, size=len(t))
        g = g + noise
        
        data[f"Temp_{T}C"] = [T]*len(t)
        data[f"Time_{T}C"] = t
        data[f"Modulus_{T}C"] = g * 100 # MPa

    df = pd.DataFrame(data)
    os.makedirs("examples", exist_ok=True)
    df.to_csv("examples/toy_data.csv", index=False)
    print("✅ Generated examples/toy_data.csv")

if __name__ == "__main__":
    generate_toy_data()
