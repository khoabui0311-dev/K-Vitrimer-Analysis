import numpy as np
import pandas as pd
from scipy.signal import savgol_filter

class DataProcessor:
    def __init__(self, min_points=8):
        self.min_points = min_points

    def trim_curve(self, t, g):
        """
        Trims artifacts from the relaxation curve.
        Returns: (t_trimmed, g_normalized, G0) or (None, None, None)
        """
        # 1. Basic Cleaning (Remove NaNs, Infs, Negatives)
        mask = (g > 0) & np.isfinite(g) & np.isfinite(t)
        t = t[mask]
        g = g[mask]
        
        if len(t) < self.min_points:
            return None, None, None

        # 2. Sort by time (crucial for raw data)
        idx = np.argsort(t)
        t = t[idx]
        g = g[idx]

        # 3. Smoothing (Savitzky-Golay) to find the true peak
        # Dynamic window size: smaller of 11 or 10% of data
        eff_window = max(5, int(len(t) * 0.1))
        if eff_window % 2 == 0: eff_window += 1
        
        try:
            g_smooth = savgol_filter(g, eff_window, 2)
        except:
            g_smooth = g # Fallback if signal processing fails

        # 4. Find Peak (Start of Relaxation)
        peak_idx = np.argmax(g_smooth)
        
        # 5. Define Start: Drop slightly below peak to avoid initial machine jitter
        start_idx = peak_idx
        threshold = g_smooth[peak_idx] * 0.99 # 1% drop threshold
        
        for i in range(peak_idx, len(g_smooth)):
            if g_smooth[i] < threshold:
                start_idx = max(0, i - 1)
                break
        
        # 6. Find End (Drift Detection)
        # Scan for a local minimum followed by a significant rise (drift)
        end_idx = len(g)
        if start_idx < len(g) - 10:
            remaining = g_smooth[start_idx:]
            min_idx_rel = np.argmin(remaining)
            min_idx = start_idx + min_idx_rel
            
            # Check if it rises significantly (>5%) after the minimum
            if min_idx < len(g) - 10:
                # Look ahead
                if np.any(g_smooth[min_idx:] > g_smooth[min_idx] * 1.05):
                    end_idx = min_idx

        # 7. Cut the Data
        t_clean = t[start_idx:end_idx]
        g_clean = g[start_idx:end_idx]
        
        if len(t_clean) < self.min_points:
            return None, None, None

        # 8. Normalize
        # Time starts at 0
        t_final = t_clean - t_clean[0] + 1e-6 # small epsilon to avoid div/0
        # G0 is average of first 5 points (more robust than single point)
        G0 = np.mean(g_clean[:5])
        g_final = g_clean / G0

        return t_final, g_final, G0