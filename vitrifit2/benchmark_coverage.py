"""Coverage study for independent synthetic relaxation experiments.

This study tests whether nominal residual-bootstrap intervals contain
known synthetic parameters over multiple independent noise realizations.
"""
from __future__ import annotations

import math
from vitrifit2.benchmark_suite import relaxation_case
from vitrifit2.benchmark_uncertainty import bootstrap_relaxation


def bootstrap_coverage_study(*, model="kww", datasets=20,
                             replicates=40, noise_fraction=.01,
                             seed=1729, tau_s=100., beta=.65,
                             confidence=.95):
    """Return empirical marginal coverage, not a guarantee of calibration."""
    if model not in ("maxwell", "kww"):
        raise ValueError("Coverage study currently supports Maxwell/KWW")
    if (not isinstance(datasets, int) or isinstance(datasets, bool)
            or not 2 <= datasets <= 200):
        raise ValueError("datasets must be an integer between 2 and 200")
    if (not isinstance(replicates, int) or isinstance(replicates, bool)
            or not 20 <= replicates <= 1000):
        raise ValueError("replicates must be an integer between 20 and 1000")
    if not math.isfinite(noise_fraction) or not 0 < noise_fraction <= .2:
        raise ValueError("noise_fraction must be in (0, .2]")
    if not math.isfinite(confidence) or not .5 < confidence < 1:
        raise ValueError("confidence must be in (0.5, 1)")
    truth = (tau_s,) if model == "maxwell" else (tau_s, beta)
    hits = [0] * len(truth)
    failures = 0
    for index in range(datasets):
        case = relaxation_case(model, tau_s=tau_s, beta=beta,
                               noise_fraction=noise_fraction, seed=seed+index)
        try:
            result = bootstrap_relaxation(
                case.time_s, case.normalized_modulus, model=model,
                replicates=replicates, seed=seed+100000+index,
                confidence=confidence)
            for j, true_value in enumerate(truth):
                hits[j] += int(result["lower"][j] <= true_value
                               <= result["upper"][j])
        except (RuntimeError, ValueError, OverflowError):
            failures += 1
    successful = datasets - failures
    return {
        "model": model, "datasets": datasets, "successful_datasets": successful,
        "failed_datasets": failures, "confidence": confidence,
        "parameters": ("tau_s",) if model == "maxwell" else ("tau_s", "beta"),
        "empirical_coverage": [hit / successful if successful else None
                               for hit in hits],
        "warning": ("Finite simulation coverage is uncertain; use many "
                    "independent datasets before asserting calibration"),
    }
