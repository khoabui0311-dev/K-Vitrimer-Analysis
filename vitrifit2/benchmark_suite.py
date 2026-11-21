"""Deterministic, mechanism-neutral reference cases for VitriFit.

No experimental curve is represented as ground truth. Synthetic cases provide
known mathematical parameters; published relaxation times are external
comparison targets with limited precision.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
import random

R = 8.31446261815324


@dataclass(frozen=True)
class SyntheticCase:
    name: str
    model: str
    time_s: tuple[float, ...]
    normalized_modulus: tuple[float, ...]
    parameters: dict[str, float]
    noise_fraction: float = 0.0


def time_grid(start_s: float = 0.01, stop_s: float = 10000.0,
              count: int = 301) -> tuple[float, ...]:
    if not (math.isfinite(start_s) and math.isfinite(stop_s)
            and 0 < start_s < stop_s and isinstance(count, int)
            and not isinstance(count, bool) and 3 <= count <= 100000):
        raise ValueError("Require 3–100000 logarithmic time points and 0 < start < stop")
    ratio = math.log(stop_s / start_s)
    return tuple(start_s * math.exp(ratio * i / (count - 1))
                 for i in range(count))


def relaxation_case(model: str, *, tau_s: float = 100.0,
                    beta: float = 0.65, fast_fraction: float = 0.3,
                    fast_tau_s: float = 10.0, noise_fraction: float = 0.0,
                    seed: int = 1729) -> SyntheticCase:
    """Generate Maxwell, KWW or dual-Maxwell curves with fixed-seed noise.

    Noise is additive Gaussian relative to G(0); values may become negative
    at long times and MUST NOT be silently clipped or used on a log axis.
    """
    if model not in ("maxwell", "kww", "dual_maxwell"):
        raise ValueError("Unsupported synthetic relaxation model")
    numbers = (tau_s, beta, fast_fraction, fast_tau_s, noise_fraction)
    if not all(math.isfinite(v) for v in numbers):
        raise ValueError("Synthetic parameters must be finite")
    if (tau_s <= 0 or fast_tau_s <= 0 or not 0 < beta <= 1
            or not 0 <= fast_fraction <= 1 or noise_fraction < 0
            or noise_fraction > 0.2):
        raise ValueError("Invalid synthetic relaxation parameters")
    times = time_grid()
    rng = random.Random(seed)
    values = []
    for t in times:
        if model == "maxwell":
            value = math.exp(-t / tau_s)
        elif model == "kww":
            value = math.exp(-(t / tau_s) ** beta)
        else:
            value = (fast_fraction * math.exp(-t / fast_tau_s)
                     + (1 - fast_fraction) * math.exp(-t / tau_s))
        if noise_fraction:
            value += rng.gauss(0.0, noise_fraction)
        values.append(value)
    return SyntheticCase(model, model, times, tuple(values),
                         {"tau_s": tau_s, "beta": beta,
                          "fast_fraction": fast_fraction,
                          "fast_tau_s": fast_tau_s}, noise_fraction)


def arrhenius_tau(temperatures_c: tuple[float, ...], *,
                  activation_kj_mol: float = 85.0,
                  tau_reference_s: float = 100.0,
                  reference_c: float = 160.0) -> tuple[float, ...]:
    """Apparent Arrhenius relaxation times, referenced to a measured T."""
    if (not all(math.isfinite(x) and x > -273.15 for x in
                (*temperatures_c, reference_c))
            or not math.isfinite(activation_kj_mol)
            or not math.isfinite(tau_reference_s) or tau_reference_s <= 0):
        raise ValueError("Invalid Arrhenius temperatures or parameters")
    tref = reference_c + 273.15
    return tuple(tau_reference_s * math.exp(
        activation_kj_mol * 1000 / R * (1 / (t + 273.15) - 1 / tref))
        for t in temperatures_c)


def vft_tau(temperatures_c: tuple[float, ...], *, a: float = -4.0,
            b_kelvin: float = 500.0, t0_c: float = 20.0) -> tuple[float, ...]:
    """VFT: ln(tau/s) = A + B / (T - T0), all temperatures in kelvin."""
    if (not all(math.isfinite(t) and t > max(-273.15, t0_c)
                for t in temperatures_c)
            or not all(math.isfinite(x) for x in (a, b_kelvin, t0_c))
            or b_kelvin <= 0):
        raise ValueError("Invalid VFT parameters or temperatures")
    return tuple(math.exp(a + b_kelvin / (t - t0_c))
                 for t in temperatures_c)


# Published 1/e relaxation times; these are reported values, not raw curves.
# Dynamic Crosslinking: An Efficient Approach to Fabricate Epoxy Vitrimer,
# Materials 2021, 14, 919, https://doi.org/10.3390/ma14040919
LITERATURE_EPOXY_REFERENCE = {
    "doi": "10.3390/ma14040919",
    "temperature_c": (140., 160., 180., 200., 220.),
    "evs_tau_s": (9330., 2100., 930., 336., 132.),
    "evd_tau_s": (5706., 1206., 450., 198., 60.),
    "reported_ea_kj_mol": {"EVS": 92.29, "EVD": 88.07},
    "tau_definition": "observed 1/e crossing",
    "provenance": "published summary values; not digitized raw data",
}


def apparent_arrhenius_ea(temperatures_c: tuple[float, ...],
                          tau_s: tuple[float, ...]) -> float:
    """Unweighted least-squares apparent Ea (kJ/mol), no mechanism inferred."""
    if (len(temperatures_c) != len(tau_s) or len(tau_s) < 2
            or len(set(temperatures_c)) < 2
            or any(not math.isfinite(t) or t <= -273.15 for t in temperatures_c)
            or any(not math.isfinite(tau) or tau <= 0 for tau in tau_s)):
        raise ValueError("Need >=2 distinct valid temperatures and positive times")
    xs = [1 / (t + 273.15) for t in temperatures_c]
    ys = [math.log(tau) for tau in tau_s]
    xm = sum(xs) / len(xs)
    ym = sum(ys) / len(ys)
    denom = sum((x - xm) ** 2 for x in xs)
    if denom <= 0:
        raise ValueError("Degenerate temperature range")
    return R * sum((x - xm) * (y - ym) for x, y in zip(xs, ys)) / denom / 1000
