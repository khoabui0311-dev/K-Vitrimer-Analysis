"""Saved-analysis Eyring and empirical Van 't Hoff Publication figures.

Reuse the existing v1 scientific fit functions and the original Figure 3/4
widget keys, without modifying the v1 Streamlit renderer. Original publication
standards: 1000/T abscissa, ln(tau*T) Eyring ordinate, reference modulus
Van 't Hoff ordinate, steelblue measurements, red dashed fit for one sample.
"""
from __future__ import annotations

from collections import defaultdict
import math

import matplotlib.ticker as ticker
import numpy as np

from can_relax.core.kinetics import KineticsEngine, predict_van_t_hoff

LEGEND_POSITIONS = {
    "Best (Auto)": "best", "Upper Right": "upper right",
    "Upper Left": "upper left", "Lower Left": "lower left",
    "Lower Right": "lower right", "Right (Outside)": "upper left",
}
MULTI_COLORS = ("#6366f1", "#f43f5e", "#10b981", "#f59e0b", "#3b82f6", "#8b5cf6")


def _value(style, key, default):
    return style[key] if key in style and style[key] is not None else default


def _number(style, key, default, minimum, maximum):
    value = float(_value(style, key, default))
    if not math.isfinite(value) or not minimum <= value <= maximum:
        raise ValueError(f"Invalid publication setting {key}: expected {minimum}–{maximum}")
    return value


def _axes(ax, style: dict, prefix: str):
    """Exact naming convention for the v1 Eyring/Van 't Hoff widget settings."""
    family = str(_value(style, prefix + "_ff", "Arial"))
    tick_family = str(_value(style, prefix + "_nf", "Same as Label"))
    if tick_family == "Same as Label":
        tick_family = family
    label_font = {
        "family": family, "size": _number(style, prefix + "_lsz", 12, 4, 30),
        "weight": str(_value(style, prefix + "_lwt", "normal")),
        "style": str(_value(style, prefix + "_lst", "normal")),
    }
    ax.set_facecolor("white")
    ax.grid(False)
    for spine in ax.spines.values():
        spine.set_linewidth(1.0)
        spine.set_color("black")
    mirror = bool(_value(style, prefix + "_mir", False))
    ax.tick_params(axis="both", which="major", width=1, length=4,
                   direction="in", top=mirror, right=mirror)
    ax.tick_params(axis="both", which="minor", width=.8, length=2.5,
                   direction="in", top=mirror, right=mirror)
    ax.xaxis.set_minor_locator(ticker.AutoMinorLocator())
    ax.yaxis.set_minor_locator(ticker.AutoMinorLocator())
    for tick in ax.get_xticklabels() + ax.get_yticklabels():
        tick.set_family(tick_family)
        tick.set_fontsize(_number(style, prefix + "_nsz", 10, 4, 30))
        tick.set_weight(str(_value(style, prefix + "_nwt", "normal")))
        tick.set_style(str(_value(style, prefix + "_nst", "normal")))
    return label_font


def _legend(ax, style: dict, prefix: str):
    if not bool(_value(style, prefix + "_leg", True)):
        return
    position = str(_value(style, prefix + "_legpos", "Best (Auto)"))
    if position not in LEGEND_POSITIONS:
        raise ValueError(f"Unsupported {prefix} legend position")
    outside = position == "Right (Outside)"
    ax.legend(loc=LEGEND_POSITIONS[position],
              bbox_to_anchor=(1.02, 1.0) if outside else None,
              frameon=bool(_value(style, prefix + "_legbox", False)),
              fontsize=_number(style, prefix + "_legfont", 8, 4, 16),
              ncol=int(_number(style, prefix + "_legncol", 1, 1, 10)),
              columnspacing=1.0, handletextpad=.5)


def _limits(ax, style: dict, prefix: str):
    if not bool(_value(style, prefix + "_clim", False)):
        return
    bounds = [_number(style, prefix + "_" + axis, 0, -1e12, 1e12)
              for axis in ("xmin", "xmax", "ymin", "ymax")]
    if bounds[0] >= bounds[1] or bounds[2] >= bounds[3]:
        raise ValueError(f"{prefix}: manual bounds must be increasing")
    if ax.get_xscale() == "log" and bounds[0] <= 0:
        raise ValueError(f"{prefix}: logarithmic X bounds must be positive")
    if ax.get_yscale() == "log" and bounds[2] <= 0:
        raise ValueError(f"{prefix}: logarithmic Y bounds must be positive")
    ax.set_xlim(bounds[0], bounds[1])
    ax.set_ylim(bounds[2], bounds[3])


def _groups(runs: list[dict], windows: dict | None, property_name: str):
    """Group pinned revisions by sample and apply independent °C windows."""
    groups = defaultdict(list)
    for run in runs:
        sample_id = run["sample_id"]
        # 1000/T and Eyring logarithms require physical absolute temperatures.
        # Reject invalid metadata before applying a sample window so malformed
        # measurements cannot be silently hidden by filtering.
        temperature_c = float(run["temperature_c"])
        if not math.isfinite(temperature_c) or temperature_c <= -273.15:
            raise ValueError("Saved analysis temperature must be finite and above absolute zero")
        bounds = (windows or {}).get(sample_id)
        if bounds is not None:
            if (len(bounds) != 2 or not all(math.isfinite(float(v)) for v in bounds)
                    or float(bounds[0]) > float(bounds[1])):
                raise ValueError("Each sample window must be a finite [min °C, max °C] interval")
            if not float(bounds[0]) <= float(run["temperature_c"]) <= float(bounds[1]):
                continue
        if property_name == "tau":
            value = run["analysis"]["results"].get("tau_s")
        else:
            # v1 Publication Fig. 4 uses Raw.G0 measured at the start of the
            # fitting interval, not the fitted long-time plateau modulus.
            value = run["analysis"]["results"].get("reference_modulus_mpa")
            if value is None:
                # Legacy pinned results may lack the explicit reference value.
                # Never substitute a fitted plateau or silently accept an
                # empty/nonphysical measurement array as an observed G0.
                measured = run.get("modulus_mpa")
                if measured is None or len(measured) == 0:
                    raise ValueError("Missing observed reference modulus in saved analysis")
                value = measured[0]
        if value is None or not math.isfinite(float(value)) or float(value) <= 0:
            raise ValueError(f"Invalid {property_name} in saved analysis")
        groups[sample_id].append((run, float(value)))
    if not groups:
        raise ValueError("No measurements remain within the selected temperature windows")
    return groups


def draw_eyring(ax, runs: list[dict], style: dict, windows: dict | None):
    """Figure 3, ln(tau * T) vs 1000/T; parameters are *apparent*.

    The inverse-rate interpretation of tau is an assumption. These parameters
    do not independently establish a specific covalent exchange mechanism.
    """
    # Multiple fits of one measured curve are alternative analyses, not replicates.
    # Reject them before kinetics to avoid pseudoreplication and biased weights.
    curve_ids = [r["curve_id"] for r in runs]
    if len(set(curve_ids)) != len(curve_ids):
        raise ValueError("Eyring: select only one analysis run per measured curve")
    definitions = {r["analysis"]["tau_definition"] for r in runs}
    if len(definitions) != 1:
        raise ValueError("Eyring comparison requires one consistent relaxation-time definition")
    font = _axes(ax, style, "eyr")
    groups = _groups(runs, windows, "tau")
    one_sample = len(groups) == 1
    metrics = []
    for i, (_, points) in enumerate(groups.items()):
        temps = [r["temperature_c"] for r, _ in points]
        taus = [value for _, value in points]
        fit = KineticsEngine().fit_eyring(temps, taus)
        name = points[0][0]["sample_name"]
        if fit is None:
            raise ValueError(f"{name}: Eyring fit requires at least 2 distinct measured temperatures")
        x = np.asarray(fit["Plot"]["x"], dtype=float) * 1000.0
        y = np.asarray(fit["Plot"]["y"], dtype=float)
        curve_x = np.linspace(x.min(), x.max(), 100)
        curve_y = fit["Params"]["slope"] * curve_x / 1000.0 + fit["Params"]["intercept"]
        color = "steelblue" if one_sample else MULTI_COLORS[i % len(MULTI_COLORS)]
        line_color = "red" if one_sample else color
        ax.scatter(x, y, s=_number(style, "eyr_ms", 6, 1, 15) ** 2,
                   alpha=.8, edgecolors="black", linewidth=.8, color=color, zorder=3)
        label = (r"$\Delta H^\ddagger = %.1f\ \mathrm{kJ\ mol}^{-1}$" % fit["dH"]
                 + "\n" + r"$\Delta S^\ddagger = %.1f\ \mathrm{J\ mol}^{-1}\mathrm{K}^{-1}$" % fit["dS"])
        if not one_sample:
            label = f"{name}\n" + label
        ax.plot(curve_x, curve_y, "--", color=line_color,
                linewidth=_number(style, "eyr_lw", 1.5, .5, 6),
                label=label, zorder=2)
        metrics.append({"sample": name, "dH_kj_mol": float(fit["dH"]),
                        "dS_j_mol_k": float(fit["dS"]), "r2": float(fit["R2"]),
                        "temperature_min_c": min(temps), "temperature_max_c": max(temps)})
    ax.set_xlabel(r"$1000/T\ (\mathrm{K}^{-1})$", fontdict=font)
    ax.set_ylabel(r"$\ln(\tau \cdot T)$", fontdict=font)
    _limits(ax, style, "eyr")
    _legend(ax, style, "eyr")
    return metrics


def draw_van_t_hoff(ax, runs: list[dict], style: dict, windows: dict | None):
    """Figure 4, observed reference modulus G0 vs 1000/T.

    The fit is empirical. An equilibrium dissociation thermodynamic
    interpretation requires independent evidence, because acquisition delay
    alone can generate temperature-dependent apparent modulus.
    """
    # Avoid counting repeated fits of the same prepared curve as independent G0.
    ids = [r["curve_id"] for r in runs]
    if len(set(ids)) != len(ids):
        raise ValueError("Van 't Hoff: select only one analysis run per measured curve")
    font = _axes(ax, style, "vh")
    groups = _groups(runs, windows, "reference modulus")
    one_sample = len(groups) == 1
    metrics = []
    for i, (_, points) in enumerate(groups.items()):
        temps = [r["temperature_c"] for r, _ in points]
        values = [v for _, v in points]
        fit = KineticsEngine().fit_van_t_hoff(temps, values)
        name = points[0][0]["sample_name"]
        if fit is None:
            raise ValueError(f"{name}: empirical Van 't Hoff fit requires 4 distinct temperatures and valid reference moduli")
        x = np.asarray(fit["Plot"]["x"], dtype=float)
        y = np.asarray(fit["Plot"]["y"], dtype=float)
        color = "steelblue" if one_sample else MULTI_COLORS[i % len(MULTI_COLORS)]
        line_color = "red" if one_sample else color
        ax.scatter(x, y, s=_number(style, "vh_ms", 6, 1, 15) ** 2,
                   alpha=.8, edgecolors="black", linewidth=.8, color=color, zorder=3)
        curve_x = np.linspace(x.min(), x.max(), 100)
        prediction = predict_van_t_hoff(1000.0/curve_x, **fit["Params"])
        label = ("Empirical modulus fit\n" +
                 r"$\Delta H_{diss} = %.1f\ \mathrm{kJ\ mol}^{-1}$" % fit["dH_diss"])
        if not one_sample:
            label = f"{name}\n" + label
        ax.plot(curve_x, prediction, "--", color=line_color,
                linewidth=_number(style, "vh_lw", 1.5, .5, 6),
                label=label, zorder=2)
        metrics.append({"sample": name, "dH_kj_mol": float(fit["dH_diss"]),
                        "dS_j_mol_k": float(fit["dS_diss"]), "r2": float(fit["R2"]),
                        "temperature_min_c": min(temps), "temperature_max_c": max(temps),
                        "interpretation": "empirical reference-modulus trend"})
    scale = str(_value(style, "vh_yscale", "Linear"))
    if scale not in ("Linear", "Log"):
        raise ValueError("Van 't Hoff Y-axis scale must be Linear or Log")
    if scale == "Log":
        ax.set_yscale("log")
        ax.yaxis.set_major_locator(ticker.LogLocator(base=10))
        ax.yaxis.set_minor_locator(ticker.LogLocator(base=10, subs=(2,3,4,5,6,7,8,9)))
    ax.set_xlabel(r"$1000/T\ (\mathrm{K}^{-1})$", fontdict=font)
    ax.set_ylabel(r"$G_0$ (MPa)", fontdict=font)
    _limits(ax, style, "vh")
    _legend(ax, style, "vh")
    return metrics
