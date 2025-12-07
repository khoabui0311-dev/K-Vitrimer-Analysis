# -*- coding: utf-8 -*-
"""
Created on Thu Dec  4 15:36:00 2025

@author: khoab
"""

import numpy as np

class AutoEngine:
    def __init__(self):
        pass

    def compute_signal_quality(self, t, g):
        """
        Returns a Quality Score (0.0 to 1.0) based on noise and drift.
        """
        if len(t) < 6: return 0.0

        # 1. Noise Check (Standard deviation of the last 10 points)
        # Ideally, the tail should be smooth.
        tail = g[-10:]
        noise = np.std(tail)
        # If noise > 2% of G0, penalize.
        noise_score = max(0, 1 - noise / 0.02)

        # 2. Dynamic Range Check (Did it actually relax?)
        # If G drops by less than 10%, it's probably not a good relaxation curve.
        drop = g[0] - g[-1]
        range_score = min(1, drop / 0.10)

        # 3. Wiggle Check (First derivative sign changes)
        # Relaxation should be monotonic. Wiggles = Instability.
        diffs = np.diff(g)
        sign_changes = np.sum(np.diff(np.sign(diffs)) != 0)
        # Allow a few wiggles due to noise, but punish heavy oscillation
        wiggle_score = max(0, 1 - sign_changes / (len(t) * 0.1))

        # Weighted Final Score
        final_score = (0.4 * noise_score) + (0.4 * range_score) + (0.2 * wiggle_score)
        return float(np.clip(final_score, 0, 1))

    def generate_explanation(self, temp, best_model, r2, quality):
        """
        Writes a human-readable summary of the curve.
        """
        msg = f"**Assessment for {temp}°C:**\n\n"
        
        # Quality Assessment
        if quality > 0.85:
            msg += f"✅ **High Quality Data** ({quality:.0%}). The curve is smooth and shows clear relaxation.\n"
        elif quality > 0.50:
            msg += f"⚠️ **Moderate Quality** ({quality:.0%}). Some noise or limited relaxation observed.\n"
        else:
            msg += f"❌ **Low Quality** ({quality:.0%}). Significant noise or drift detected. Results may be unreliable.\n"

        # Model Interpretation
        if best_model == "Maxwell":
            msg += "- Behavior matches a **Maxwellian** fluid (simple exponential decay).\n"
        elif best_model == "Single_KWW":
            msg += "- Behavior matches a **Vitrimer-like** stretched exponential (broad relaxation spectrum).\n"
        elif best_model == "Dual_KWW":
            msg += "- Complex behavior detected (**Dual-mode**). Likely distinct fast and slow relaxation processes.\n"

        # Fit Warning
        if r2 < 0.95:
            msg += f"- ❗ **Warning:** The fit is poor ($R^2={r2:.3f}$). Check for artifacts."
            
        return msg