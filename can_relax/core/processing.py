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
        
        # 5. Define Start: Use the peak directly for pre-trimmed data
        # Only skip initial jitter if there's a clear rise before the peak
        start_idx = peak_idx
        
        # If peak is not at the beginning, check for initial overshoot/jitter
        if peak_idx > 5:
            # Look for where curve drops 1% from peak (to skip overshoot)
            threshold = g_smooth[peak_idx] * 0.99
            for i in range(peak_idx, min(peak_idx + 10, len(g_smooth))):
                if g_smooth[i] < threshold:
                    start_idx = max(0, i - 1)
                    break
        # Otherwise keep start_idx = peak_idx (data is already clean)
        
        # 6. Find End (Drift Detection)
        # Scan for a local minimum followed by a significant rise (drift)
        end_idx = len(g)
        if start_idx < len(g) - 20:  # Need at least 20 points for drift detection
            remaining = g_smooth[start_idx:]
            min_idx_rel = np.argmin(remaining)
            min_idx = start_idx + min_idx_rel
            
            # Only trim if minimum is not at the very end and there's clear drift upward
            if min_idx < len(g) - 10:
                # Look ahead and check if drift is significant (>10% rise)
                tail = g_smooth[min_idx:]
                if len(tail) > 5 and np.max(tail) > g_smooth[min_idx] * 1.10:
                    end_idx = min_idx
            # If minimum is at the end, keep all data (no drift detected)

        # 7. Cut the Data
        t_clean = t[start_idx:end_idx]
        g_clean = g[start_idx:end_idx]
        
        if len(t_clean) < self.min_points:
            return None, None, None

        # 8. Normalize
        # Time starts at 0.01 (better numerical stability than 1e-6)
        t_final = t_clean - t_clean[0] + 0.01
        
        # G0 should be the maximum value (peak of the curve after trimming start artifacts)
        # Taking max of first 10% of points to be robust against single outliers
        n_init = max(3, min(10, len(g_clean) // 10))
        G0 = np.max(g_clean[:n_init])
        
        g_final = g_clean / G0

        return t_final, g_final, G0