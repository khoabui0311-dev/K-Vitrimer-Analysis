# -*- coding: utf-8 -*-
"""
Created on Sat Dec  6 13:41:27 2025

@author: khoab
"""

import sys
import os

print("--- PYTHON INFO ---")
print(f"Executable: {sys.executable}")
print(f"Version: {sys.version}")

print("\n--- IMPORT CHECKS ---")
try:
    import sklearn
    print(f"✅ scikit-learn is installed (v{sklearn.__version__})")
except ImportError as e:
    print(f"❌ scikit-learn FAILED: {e}")

try:
    import joblib
    print(f"✅ joblib is installed (v{joblib.__version__})")
except ImportError as e:
    print(f"❌ joblib FAILED: {e}")

print("\n--- INTERNAL MODULE CHECK ---")
try:
    # Add current path so we can find the package
    sys.path.append(os.getcwd())
    from can_relax.ml_engine.classifier import MLPredictor
    print("✅ MLPredictor imported successfully!")
except Exception as e:
    print(f"❌ MLPredictor CRASHED: {e}")
    import traceback
    traceback.print_exc()

input("\nPress Enter to exit...")