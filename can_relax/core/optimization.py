"""Deterministic multi-start least squares for independent two-Maxwell fits."""
import numpy as np
from scipy.optimize import curve_fit


def prony_starts(t, guess, bounds):
    """Include the historical guess, then span fractions and observable time scales."""
    span = float(t[-1] - t[0])
    lo, hi = np.asarray(bounds[0]), np.asarray(bounds[1])
    starts = [np.asarray(guess, dtype=float)]
    for fraction in (.2, .5, .8):
        for fast, slow in ((.001, .1), (.01, 1.), (.1, 10.), (.3, .7)):
            seed = np.array(guess, dtype=float)
            seed[:3] = [fraction, span * fast, span * slow]
            starts.append(np.clip(seed, lo + 1e-10, hi - 1e-10))
    # A second plateau guess tests competition between slow decay and a plateau.
    if len(guess) == 4:
        starts += [np.r_[seed[:3], .001] for seed in starts[1:]]
    return starts


def fit_prony_multistart(prediction, t, g, guess, bounds):
    """Choose minimum RSS; near-best spread is a heuristic, never a confidence interval."""
    candidates, trials = [], []
    starts = prony_starts(t, guess, bounds)
    for index, seed in enumerate(starts):
        trial = {'start': index + 1, 'initial_parameters': seed.tolist()}
        try:
            params, covariance = curve_fit(prediction, t, g, p0=seed, bounds=bounds,
                                           maxfev=15000, x_scale='jac')
            residual = g - prediction(t, *params)
            rss = float(residual @ residual)
            if not np.isfinite(rss) or not np.all(np.isfinite(params)):
                raise ValueError('Nonfinite fit parameters or residuals')
            ordered = params.copy()
            if ordered[1] > ordered[2]:
                ordered[:3] = [1 - ordered[0], ordered[2], ordered[1]]
            trial.update(success=True, rss=rss, parameters=ordered.tolist())
            candidates.append((rss, index + 1, params, covariance, ordered))
        except (RuntimeError, ValueError, FloatingPointError) as exc:
            trial.update(success=False, error=str(exc))
        trials.append(trial)
    if not candidates:
        raise RuntimeError(f'All {len(starts)} two-Maxwell starting guesses failed.')
    best = min(candidates, key=lambda candidate: candidate[0])
    tolerance = max(best[0] * .001, 1e-12)
    near = [candidate for candidate in candidates if candidate[0] <= best[0] + tolerance]
    times = np.array([candidate[4][1:3] for candidate in near])
    spread = (times.max(axis=0) - times.min(axis=0)) / best[4][1:3] * 100
    diagnostics = {
        'method': 'deterministic multi-start bounded least squares',
        'attempted_starts': len(starts), 'converged_starts': len(candidates),
        'best_start': best[1], 'best_rss': best[0], 'near_best_starts': len(near),
        'near_best_rss_tolerance': tolerance,
        'near_best_tau_min_s': times.min(axis=0).tolist(),
        'near_best_tau_max_s': times.max(axis=0).tolist(),
        'near_best_tau_spread_percent': spread.tolist(),
        'trials': trials,
    }
    return best[2], best[3], diagnostics


def residual_diagnostics(residuals):
    """Descriptive adjacent-observation correlation; no significance test is implied."""
    residuals = np.asarray(residuals, dtype=float)
    rmse = float(np.sqrt(np.mean(residuals ** 2)))
    left, right = residuals[:-1], residuals[1:]
    correlation = None
    if len(left) >= 3 and rmse > 1e-8 and min(np.std(left), np.std(right)) > 1e-12:
        correlation = float(np.corrcoef(left, right)[0, 1])
    return {'rmse_normalized': rmse, 'lag1_correlation': correlation,
            'structured_residuals': correlation is not None and abs(correlation) >= .5}
