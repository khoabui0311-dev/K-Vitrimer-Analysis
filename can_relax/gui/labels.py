"""Consistent curve labels that disambiguate only replicated temperatures."""
from collections import Counter


def curve_labels(results):
    counts = Counter(r['Temp'] for r in results)
    return {r['Curve_ID']: (f"{r['Temp']:g}°C ({r['Curve_ID']})"
            if counts[r['Temp']] > 1 else f"{r['Temp']:g}°C") for r in results}
