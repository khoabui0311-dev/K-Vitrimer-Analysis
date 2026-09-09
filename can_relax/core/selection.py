"""Explicit measurement exclusions, applied before automatic preprocessing."""
import numpy as np


def prepare_curve(data, origin=0.0, cutoff=0.0, excluded=()):
    if not np.isfinite(origin) or not np.isfinite(cutoff) or cutoff < 0:
        raise ValueError('Origin must be finite and cutoff must be nonnegative.')
    indices = np.asarray(list(excluded), dtype=float)
    if not np.all(np.isfinite(indices)) or np.any(indices != np.floor(indices)):
        raise ValueError('Excluded measurement numbers must be finite integers.')
    excluded = sorted(set(int(i) for i in indices))
    if any(i < 1 or i > len(data) for i in excluded):
        raise ValueError('Excluded measurement number is outside this curve.')
    preview = data.reset_index(drop=True).copy()
    preview.insert(0, 'Point', np.arange(1, len(data)+1))
    preview['Elapsed time (s)'] = preview['Time'] - origin
    preview['Keep'] = ~preview['Point'].isin(excluded)
    preview['In time window'] = preview['Elapsed time (s)'] >= cutoff
    selected = preview['Keep'] & preview['In time window']
    frame = preview.loc[selected, ['Time', 'Modulus']].copy()
    frame['Time'] = preview.loc[selected, 'Elapsed time (s)']
    audit = {'loading_origin_s': float(origin), 'short_time_cutoff_s': float(cutoff),
             'excluded_point_numbers': excluded, 'imported_points': len(data),
             'points_after_manual_selection': len(frame),
             'points_before_cutoff': int((~preview['In time window']).sum())}
    return frame, preview, audit
