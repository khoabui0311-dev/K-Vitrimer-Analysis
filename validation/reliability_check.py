"""Audit the production reliability workflow against an independent log-time solver.

Usage: python validation/reliability_check.py workbook.xlsx --output local-directory
Writes parameter summaries only; never modifies or uploads the input workbook.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from can_relax.core.analyzer import CurveAnalyzer
from can_relax.core.models import PRONY
from can_relax.core.reliability import check_prony_stability, diagnostic_row
from can_relax.io.analysis_report import plain
from can_relax.io.parser import parse_curve_records
from can_relax.version import VERSION
from validation.experimental_prony import independent_fit


def audit(source):
    started = time.perf_counter()
    checks, diagnostics, comparisons, skipped = [], [], [], []
    for imported in parse_curve_records(source):
        record = CurveAnalyzer().fit_one_temp(imported['Temp'], imported['Data'], Tg=50, fit_model=PRONY)
        if not record['Valid']:
            skipped.append({'temperature_C': imported['Temp'], 'reason': record['Reason']})
            continue
        record['Curve_ID'] = imported['Curve_ID']
        checks.append(check_prony_stability(record))
        diagnostics.append(diagnostic_row(record, PRONY))
        raw, fit = record['Raw'], record['Fits'][PRONY]
        independent = independent_fit(raw['t'], raw['g'])[0]
        reference = np.array([independent['tau_fast_s'], independent['tau_slow_s']])
        change = (fit['popt'][1:3] / reference - 1) * 100
        original_trial = fit['optimization']['trials'][0]
        comparisons.append({'curve_id': record['Curve_ID'], 'temperature_C': record['Temp'],
            'tau_fast_s': fit['popt'][1], 'tau_slow_s': fit['popt'][2],
            'independent_fast_s': reference[0], 'independent_slow_s': reference[1],
            'difference_percent': change, 'attempted_starts': fit['optimization']['attempted_starts'],
            'converged_starts': fit['optimization']['converged_starts'],
            'rss': fit['optimization']['best_rss'], 'historical_start_rss': original_trial.get('rss')})
    return plain({'software_version': VERSION, 'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
        'policy': 'Independent two-Maxwell zero-plateau fits; below-Tg exclusion 50 C; no manual exclusions; origin 0 s',
        'elapsed_seconds': time.perf_counter()-started, 'skipped': skipped, 'diagnostics': diagnostics,
        'independent_comparison': comparisons, 'stability': checks})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    evidence = audit(args.source)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / 'reliability-audit.json').write_text(json.dumps(evidence, indent=2, allow_nan=False), encoding='utf-8')
    rows = [row for check in evidence['stability'] for row in check['rows']]
    pd.DataFrame(rows).to_csv(args.output / 'reliability-scenarios.csv', index=False)
    print(json.dumps({'curves': len(evidence['stability']), 'scenarios': len(rows),
        'unavailable': sum(row['Status'] != 'Fitted' for row in rows),
        'max_solver_difference_percent': max((abs(value) for item in evidence['independent_comparison']
                                               for value in item['difference_percent']), default=None),
        'elapsed_seconds': evidence['elapsed_seconds']}, indent=2))
