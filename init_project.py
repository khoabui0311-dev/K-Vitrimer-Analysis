import os
import sys

def create_file(path, content=""):
    """Helper to create a file with content."""
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  [FILE] Created: {path}")

def create_structure():
    root = "can_relax"
    
    # 1. Directory Layout
    directories = [
        "can_relax",                # Source Code Root
        "can_relax/core",           # Physics, Math, Logic
        "can_relax/io",             # Parsers, Exporters
        "can_relax/gui",            # Streamlit Interface
        "can_relax/data",           # Database & Temp files
        "can_relax/ml",             # Machine Learning
        "tests",                    # Unit Tests
        "examples"                  # Toy data
    ]
    
    print(f"🚀 Initializing Project Structure...")
    
    for d in directories:
        os.makedirs(d, exist_ok=True)
        print(f"  [DIR]  Created: {d}")

    # 2. Package Initialization (__init__.py makes folders importable)
    create_file(os.path.join(root, "__init__.py"), '__version__ = "1.0.0"')
    create_file(os.path.join(root, "core", "__init__.py"))
    create_file(os.path.join(root, "io", "__init__.py"))
    create_file(os.path.join(root, "gui", "__init__.py"))
    create_file(os.path.join(root, "ml", "__init__.py"))

    # 3. Create Placeholder Source Files (We will fill these one by one)
    # CORE
    create_file(os.path.join(root, "core", "models.py"), "# Physics models (Maxwell, KWW)\n")
    create_file(os.path.join(root, "core", "processing.py"), "# Signal processing (Smoothing, Trimming)\n")
    create_file(os.path.join(root, "core", "analyzer.py"), "# Orchestrator for fitting logic\n")
    
    # IO
    create_file(os.path.join(root, "io", "parser.py"), "# Robust file parsing logic\n")
    create_file(os.path.join(root, "io", "report.py"), "# PDF/Excel generation\n")
    
    # GUI
    create_file(os.path.join(root, "gui", "dashboard.py"), "# Streamlit Entry Point\n")

    # ROOT FILES
    reqs = """numpy
pandas
scipy
matplotlib
streamlit
plotly
openpyxl
"""
    create_file("requirements.txt", reqs)
    create_file("README.md", "# CAN-Relax Supreme\n\nScientific Stress Relaxation Analysis Software.")
    
    # 4. Create a Data Generator (So we can test immediately)
    data_gen_code = r'''
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
'''
    create_file("generate_data.py", data_gen_code)

    print("\n✅ PHASE 1.1 COMPLETE: Structure Built.")
    print("👉 Next Step: Run 'python generate_data.py' to create test data.")

if __name__ == "__main__":
    create_structure()