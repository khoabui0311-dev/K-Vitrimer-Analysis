"""Measurements extracted without assuming a relaxation model."""
import numpy as np


def relaxation_crossing(t, g):
    """First-observation-relative 1/e interval, only for an unambiguous crossing.

    An interval on a truncated KWW curve is not its intrinsic fitted tau.
    Multiple downward crossings indicate noise/recrossing and are not accepted.
    """
    t, g = np.asarray(t, dtype=float), np.asarray(g, dtype=float)
    invalid = {'status': 'invalid', 'tau': np.nan, 'crossing_time': np.nan}
    if (t.ndim != 1 or g.shape != t.shape or len(t) < 2
            or not np.all(np.isfinite(t)) or not np.all(np.isfinite(g))
            or np.any(np.diff(t) <= 0) or g[0] <= 0):
        return invalid
    target = g[0] / np.e
    crossings = np.flatnonzero((g[:-1] > target) & (g[1:] <= target))
    if len(crossings) == 0:
        return dict(invalid, status='not_reached')
    if len(crossings) != 1 or np.any(g[crossings[0] + 1:] > target):
        return dict(invalid, status='ambiguous')
    i = crossings[0]
    crossing = t[i] + (target - g[i]) * (t[i + 1] - t[i]) / (g[i + 1] - g[i])
    return {'status': 'observed', 'tau': float(crossing - t[0]),
            'crossing_time': float(crossing), 'reference_time': float(t[0])}
