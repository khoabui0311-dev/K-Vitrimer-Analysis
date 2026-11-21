"""Reproducible v2 figure exports using the v1 publication visual conventions.

The v1 Matplotlib Publication tab remains authoritative for its four figure
types. This module adds standalone exports from persisted, pinned analyses;
it deliberately reuses can_relax.gui.exporting.figure_bytes and the v1
publication setting names rather than redefining file formats or DPI behavior.
"""
from __future__ import annotations

from collections import defaultdict
from contextlib import contextmanager
import math

import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np

from can_relax.core.kinetics import KineticsEngine
from can_relax.core.observations import relaxation_crossing
from can_relax.gui.exporting import MIME_TYPES, figure_bytes
from .thermodynamic_figures import draw_eyring, draw_van_t_hoff
from .persistence import VitriFitStore

# Same sequence as can_relax.gui.app.PLOTLY_STYLE["colorway"].
V1_PALETTE = ("#6366f1", "#f43f5e", "#10b981", "#f59e0b", "#3b82f6", "#8b5cf6")
SINGLE_COLUMN = "ACS/RSC Single-Column (85 x 75 mm)"
DOUBLE_COLUMN = "ACS/RSC Double-Column (170 x 140 mm)"


def _val(s: dict, key: str, default):
    return s[key] if key in s and s[key] is not None else default


def _physical_size(style: dict) -> tuple[float, float]:
    preset = _val(style, "pub_preset", SINGLE_COLUMN)
    if preset == SINGLE_COLUMN:
        return 8.5, 7.5
    if preset == DOUBLE_COLUMN:
        return 17.0, 14.0
    if preset != "Custom":
        raise ValueError("Unknown journal-size preset")
    w, h = float(_val(style, "pub_w", 12.7)), float(_val(style, "pub_h", 10.0))
    if not (math.isfinite(w) and math.isfinite(h) and 1 <= w <= 40 and 1 <= h <= 40):
        raise ValueError("Custom publication dimensions must be between 1 and 40 cm")
    if w*h > 400:
        raise ValueError("Custom publication area must not exceed 400 cm²")
    return w, h


def _validated_number(style: dict, key: str, default: float, lo: float, hi: float) -> float:
    number = float(_val(style, key, default))
    if not math.isfinite(number) or number < lo or number > hi:
        raise ValueError(f"Invalid publication setting '{key}'; expected {lo}–{hi}")
    return number


def _legend(ax, style: dict, prefix: str) -> None:
    # Matches the accepted v1 options and placement in tab_pub_main.apply_legend.
    show = bool(_val(style, prefix+"leg", True))
    if not show:
        return
    position = _val(style, prefix+"pos", "Best (Auto)")
    positions = {
        "Best (Auto)": "best", "Upper Right": "upper right",
        "Upper Left": "upper left", "Lower Left": "lower left",
        "Lower Right": "lower right", "Right (Outside)": "upper left",
    }
    if position not in positions:
        raise ValueError("Unknown legacy legend position")
    fontsize = _validated_number(style, prefix+"font", 8, 4, 16)
    ncol = int(_validated_number(style, prefix+"ncol", 1, 1, 10))
    anchor = (1.02, 1.0) if position == "Right (Outside)" else None
    ax.legend(frameon=bool(_val(style, prefix+"box", False)),
              loc=positions[position], bbox_to_anchor=anchor, fontsize=fontsize,
              ncol=ncol, columnspacing=1.0, handletextpad=0.5)


def _style_axes(ax, style: dict, kind: str) -> dict:
    is_kin = kind == "kinetics"
    prefix = "pub_kin_" if is_kin else "pub_rel_"
    family = str(_val(style, "pub_kinfont_family" if is_kin else "pub_relfont_family", "Arial"))
    lab_size = _validated_number(style, prefix+"lbl_sz", 12, 4, 30)
    tick_size = _validated_number(style, prefix+"num_sz", 10, 4, 30)
    tick_family = str(_val(style, prefix+"num_font", "Same as Label"))
    if tick_family == "Same as Label":
        tick_family = family
    ax.set_facecolor("white")
    ax.grid(False)
    for spine in ax.spines.values():
        spine.set_linewidth(1)
        spine.set_color("black")
    mirror = bool(_val(style, prefix+"mirror", False))
    ax.tick_params(axis="both", which="major", direction="in", color="black",
                   width=1, length=4, top=mirror, right=mirror)
    ax.tick_params(axis="both", which="minor", direction="in", color="black",
                   width=0.8, length=2.5, top=mirror, right=mirror)
    ax.xaxis.set_minor_locator(ticker.AutoMinorLocator())
    ax.yaxis.set_minor_locator(ticker.AutoMinorLocator())
    weight = str(_val(style, prefix+"num_wt", "normal"))
    font_style = str(_val(style, prefix+"num_sty", "normal"))
    for label in ax.get_xticklabels() + ax.get_yticklabels():
        label.set_fontfamily(tick_family)
        label.set_fontsize(tick_size)
        label.set_fontweight(weight)
        label.set_fontstyle(font_style)
    return {
        "family": family, "size": lab_size,
        "weight": str(_val(style, prefix+"lbl_wt", "normal")),
        "style": str(_val(style, prefix+"lbl_sty", "normal")),
    }


def _panel(ax, style: dict, number: int) -> None:
    label = str(_val(style, f"pl_{number}", chr(96+number)))
    if label:
        x = _validated_number(style, f"plx_{number}", -0.12, -1, 2)
        y = _validated_number(style, f"ply_{number}", 1.02, -1, 2)
        ax.text(x, y, f"({label})", transform=ax.transAxes,
                fontfamily=str(_val(style, "pub_panel_font_family", "Arial")),
                fontsize=_validated_number(style, "pub_panel_size", 12, 4, 30),
                fontweight=str(_val(style, "pub_panel_weight", "normal")),
                fontstyle=str(_val(style, "pub_panel_style", "normal")),
                va="bottom", ha="right")


def _limits(ax, style: dict, prefix: str) -> bool:
    if not bool(_val(style, prefix+"cust_lims", False)):
        return False
    xmin, xmax = float(style[prefix+"xmin"]), float(style[prefix+"xmax"])
    ymin, ymax = float(style[prefix+"ymin"]), float(style[prefix+"ymax"])
    if not all(math.isfinite(x) for x in (xmin, xmax, ymin, ymax)) or xmin >= xmax or ymin >= ymax:
        raise ValueError("Publication axis limits must be finite and strictly increasing")
    if ax.get_xscale() == "log" and xmin <= 0:
        raise ValueError("Logarithmic X-axis limits must be positive")
    if ax.get_yscale() == "log" and ymin <= 0:
        raise ValueError("Logarithmic Y-axis limits must be positive")
    ax.set_xlim(xmin, xmax)
    ax.set_ylim(ymin, ymax)
    return True


def _get_pinned_runs(store: VitriFitStore, run_ids: list[str]) -> list[dict]:
    if not run_ids or len(run_ids) != len(set(run_ids)):
        raise ValueError("Select distinct saved analysis runs")
    if len(run_ids) > 100:
        raise ValueError("Publication export supports at most 100 saved analysis runs")
    catalog = {r["id"]: r for r in store.list_analysis_runs()}
    records = []
    for run_id in run_ids:
        if run_id not in catalog:
            raise KeyError("Unknown saved analysis run")
        meta = catalog[run_id]
        analysis = store.get_analysis(run_id)
        pinned = store.get_curve_revision(meta["curve_id"], analysis["revision_id"])
        times = np.asarray(pinned["time_s"], dtype=float)[pinned["mask"]]
        modulus = np.asarray(pinned["modulus_mpa"], dtype=float)[pinned["mask"]]
        if len(times) < 2:
            raise ValueError("Saved processing revision has fewer than two points")
        records.append({**meta, "analysis": analysis, "time_s": times,
                        "modulus_mpa": modulus,
                        "revision_id": analysis["revision_id"]})
    return records


def _relaxation(ax, runs: list[dict], style: dict) -> None:
    norm = str(_val(style, "pub_ynorm", "Normalized (G/G₀ or E/E₀)")).startswith("Normalized")
    modulus_type = str(_val(style, "pub_ylabel", "G (Shear Modulus)"))
    data_style = _val(style, "pub_style", "Continuous Lines (Raw)")
    if data_style not in ("Continuous Lines (Raw)", "Markers Only", "Lines + Markers"):
        raise ValueError("Unknown legacy curve display style")
    xscale = str(_val(style, "pub_xscale", "Log"))
    yscale = str(_val(style, "pub_yscale", "Linear"))
    units = str(_val(style, "pub_xunit", "Seconds (s)"))
    factors = {"Seconds (s)": (1, "s"), "Minutes (min)": (60, "min"),
               "Hours (h)": (3600, "h")}
    if units not in factors or xscale not in ("Log", "Linear") or yscale not in ("Linear", "Log"):
        raise ValueError("Invalid legacy axis unit/scale setting")
    factor, label_unit = factors[units]
    line = _validated_number(style, "pub_rel_lw", 1.5, .5, 6)
    marker = _validated_number(style, "pub_rel_ms", 4, 1, 15)
    density = int(_validated_number(style, "pub_rel_md", 20, 0, 100))
    if data_style == "Markers Only" and density == 0:
        raise ValueError("Markers Only requires a positive marker density")
    step = max(1, int(100/density)) if density else 0
    fit_overlay = bool(_val(style, "pub_showfit", False))
    tau_mark = bool(_val(style, "pub_taustar", True))
    tau_label = bool(_val(style, "pub_taulabel", False))
    ylabel_symbol = "G" if modulus_type.startswith("G") else "E"
    for i, item in enumerate(runs):
        t, g = item["time_s"], item["modulus_mpa"]
        if not np.all(np.isfinite(t)) or not np.all(np.isfinite(g)) or np.any(np.diff(t) <= 0):
            raise ValueError("Selected curve contains invalid or unordered times")
        if g[0] <= 0:
            raise ValueError("Reference modulus must be positive")
        color = V1_PALETTE[i % len(V1_PALETTE)]
        x = t/factor
        y = g/g[0] if norm else g
        if xscale == "Log" and np.any(x <= 0):
            raise ValueError("Log time axis requires positive times; trim the initial zero or use Linear")
        if yscale == "Log" and np.any(y <= 0):
            raise ValueError("Log modulus axis requires positive values; trim artifacts first")
        name = f"{item['sample_name']} · {item['temperature_c']:g} °C"
        if data_style in ("Continuous Lines (Raw)", "Lines + Markers"):
            line_label = name if data_style == "Continuous Lines (Raw)" or density == 0 else None
            ax.plot(x, y, "-", linewidth=line, color=color, label=line_label)
        if data_style in ("Markers Only", "Lines + Markers") and density > 0:
            ax.plot(x[::step], y[::step], "o", markersize=marker, color=color,
                    alpha=.8, label=name)
        if fit_overlay:
            predicted = item["analysis"]["results"]
            fit_t = np.asarray(predicted.get("fit_time_s", []), dtype=float)
            fit_g = np.asarray(predicted.get("fit_normalized_prediction", []), dtype=float)
            if fit_t.size or fit_g.size:
                if fit_t.size != fit_g.size or not np.all(np.isfinite(fit_t)) or not np.all(np.isfinite(fit_g)):
                    raise ValueError("Saved fit overlay must have equal-length finite time and prediction arrays")
                if np.any(np.diff(fit_t) <= 0):
                    raise ValueError("Saved fit overlay times must be strictly increasing")
                if xscale == "Log" and np.any(fit_t <= 0):
                    raise ValueError("Saved fit overlay requires positive times on a log X-axis")
                if yscale == "Log" and np.any(fit_g <= 0):
                    raise ValueError("Saved fit overlay requires positive predictions on a log Y-axis")
                ax.plot(fit_t/factor, fit_g if norm else fit_g*g[0], ":",
                        color="black", linewidth=1, alpha=.7)
        if tau_mark:
            crossing = relaxation_crossing(t, g)
            if crossing["status"] == "observed":
                cross = crossing["crossing_time"]/factor
                reference = 1/math.e if norm else g[0]/math.e
                ax.plot(cross, reference, "o", color=color, markersize=marker+1,
                        markeredgecolor="black", markeredgewidth=.8, zorder=5)
                if not norm:
                    ax.hlines(reference, xmin=x.min()*.8, xmax=cross, colors=color,
                              linestyles="--", linewidths=.8, alpha=.5)
                if tau_label:
                    ax.text(cross*1.15, reference*(1.02 if not norm else 1)+(.02 if norm else 0),
                            r"$\tau^* = %.1f\ \mathrm{%s}$" %
                            (crossing["tau"]/factor, label_unit), fontsize=7, color=color)
    if tau_mark and norm:
        ax.axhline(1/math.e, color="gray", linestyle="--", linewidth=1)
    ax.set_xscale("log" if xscale == "Log" else "linear")
    ax.set_yscale("log" if yscale == "Log" else "linear")
    ax.xaxis.set_minor_locator(ticker.LogLocator(base=10, subs=(2,3,4,5,6,7,8,9))
                               if xscale == "Log" else ticker.AutoMinorLocator())
    ax.yaxis.set_minor_locator(ticker.LogLocator(base=10, subs=(2,3,4,5,6,7,8,9))
                               if yscale == "Log" else ticker.AutoMinorLocator())
    symbol = r"G" if ylabel_symbol == "G" else r"E"
    ax.set_xlabel(r"Time, $t$ (%s)" % label_unit)
    ax.set_ylabel(r"$%s(t)/%s_0$" % (symbol, symbol) if norm
                  else r"$%s(t)$ (MPa)" % symbol)
    if not _limits(ax, style, "pub_rel_"):
        xx = np.concatenate([r["time_s"]/factor for r in runs])
        yy = np.concatenate([r["modulus_mpa"]/(r["modulus_mpa"][0] if norm else 1)
                             for r in runs])
        min_x = np.min(xx[xx > 0]) if xscale == "Log" else float(np.min(xx))
        ax.set_xlim(min_x*.8 if min_x != 0 else 0, float(np.max(xx))*1.2)
        if norm:
            # Preserve observed overshoots above G/G0 = 1 and measured
            # relaxation tails below 1e-3 rather than silently clipping them.
            upper = max(1.05, float(np.max(yy))*1.05)
            if yscale == "Log":
                ax.set_ylim(float(np.min(yy[yy > 0]))*.8, upper)
            else:
                ax.set_ylim(min(0.0, float(np.min(yy))), upper)
        elif yscale == "Linear":
            ax.set_ylim(min(0.0, float(np.min(yy))), float(np.max(yy))*1.05)
        else:
            ax.set_ylim(float(np.min(yy[yy > 0]))*.8, float(np.max(yy))*1.2)
    _legend(ax, style, "pub_rel")
    _panel(ax, style, 1)


def _kinetics(ax, runs: list[dict], style: dict, model: str,
              windows: dict[str, list[float]] | None) -> None:
    if model not in ("Arrhenius", "VFT"):
        raise ValueError("Kinetic publication plots support Arrhenius or VFT")
    # Distinct fit runs of the same measured curve are alternative models,
    # never independent kinetic observations. Validate before window filtering.
    curve_ids = [r["curve_id"] for r in runs]
    if len(curve_ids) != len(set(curve_ids)):
        raise ValueError("Kinetics: select only one analysis run per measured curve")
    defs = {r["tau_definition"] for r in runs}
    if len(defs) != 1:
        raise ValueError("Do not mix different definitions of relaxation time")
    grouped = defaultdict(list)
    for r in runs:
        temperature_c = float(r["temperature_c"])
        if not math.isfinite(temperature_c) or temperature_c <= -273.15:
            raise ValueError("Kinetics requires finite temperatures above absolute zero")
        window = (windows or {}).get(r["sample_id"])
        if window is not None:
            if (len(window) != 2 or
                    not all(math.isfinite(float(v)) for v in window) or
                    float(window[0]) > float(window[1])):
                raise ValueError("Invalid independent sample temperature window")
            if not float(window[0]) <= temperature_c <= float(window[1]):
                continue
        tau = r["analysis"]["results"].get("tau_s")
        if tau is None or not math.isfinite(float(tau)) or float(tau) <= 0:
            raise ValueError("Selected analysis does not contain a positive relaxation time")
        grouped[r["sample_id"]].append((r, float(tau)))
    if not grouped:
        raise ValueError("No points within the selected sample temperature windows")
    for sample_points in grouped.values():
        if len({float(r["temperature_c"]) for r, _ in sample_points}) < 2:
            raise ValueError("Kinetic comparison requires at least two distinct measured temperatures per sample")
    for i, group in enumerate(grouped.values()):
        temps = np.array([r["temperature_c"] for r, _ in group], dtype=float)
        taus = np.array([tau for _, tau in group], dtype=float)
        color = V1_PALETTE[i%len(V1_PALETTE)]
        name = group[0][0]["sample_name"]
        x = 1000/(temps+273.15)
        ax.scatter(x, np.log(taus),
                   s=_validated_number(style, "pub_kin_ms", 6, 1, 15)**2,
                   alpha=.8, edgecolors="black", linewidth=.8, color=color,
                   label=name, zorder=3)
        engine = KineticsEngine()
        fit = engine.fit_arrhenius(temps, taus) if model == "Arrhenius" else engine.fit_vft(temps, taus)
        if fit is None:
            raise ValueError(f"{name}: {model} fit could not be determined from the selected measurements")
        if fit:
            tc = np.linspace(temps.min(), temps.max(), 100)
            if model == "Arrhenius":
                params = fit["Params"]
                yfit = params["slope"]/(tc+273.15) + params["intercept"]
                description = (r"$E_\mathrm{a} = %.1f\ \mathrm{kJ\,mol}^{-1}$" %
                               fit["Ea"])
            else:
                params = fit["Params"]
                yfit = params["A"] + params["B"]/(tc+273.15-params["T0"])
                description = ("VFT B=%.0f K, T0=%.1f °C" %
                               (params["B"], params["T0"]-273.15))
            ax.plot(1000/(tc+273.15), yfit, "--", color=color,
                    linewidth=_validated_number(style, "pub_kin_lw", 1.5, .5, 6),
                    label=f"{name} fit: {description}", zorder=2)
    ax.set_xlabel(r"$1000/T\ (\mathrm{K}^{-1})$")
    ax.set_ylabel(r"$\ln(\tau)$")
    if not _limits(ax, style, "pub_kin_"):
        ax.autoscale(enable=True, axis="both", tight=False)
    _legend(ax, style, "pub_kin")
    _panel(ax, style, 2)


def _fixed_temperature(ax, runs: list[dict], style: dict, temp: float | None) -> None:
    if temp is None or not math.isfinite(float(temp)):
        raise ValueError("Select a measured comparison temperature")
    if float(temp) <= -273.15:
        raise ValueError("Comparison temperature must be above absolute zero")
    # Alternative fits to one instrument curve are not independent replicates.
    curve_ids = [r["curve_id"] for r in runs]
    if len(curve_ids) != len(set(curve_ids)):
        raise ValueError("Select only one analysis run per measured curve")
    defs = {r["tau_definition"] for r in runs}
    if len(defs) != 1:
        raise ValueError("Do not mix different definitions of relaxation time")
    # Validate all metadata before filtering; invalid values must not be hidden
    # simply because they do not match the requested comparison temperature.
    if any(not math.isfinite(float(r["temperature_c"])) or
           float(r["temperature_c"]) <= -273.15 for r in runs):
        raise ValueError("Saved temperatures must be finite and above absolute zero")
    matched = [r for r in runs if abs(float(r["temperature_c"])-float(temp)) < 1e-6]
    if len(matched) < 2:
        raise ValueError("At least two measured relaxation times at that temperature are required")
    if len({r["sample_id"] for r in matched}) < 2:
        raise ValueError("Fixed-temperature comparison requires at least two distinct samples")
    taus = [float(r["analysis"]["results"].get("tau_s", 0)) for r in matched]
    if any(not math.isfinite(t) or t <= 0 for t in taus):
        raise ValueError("All selected comparisons must have positive tau values")
    xx = np.arange(len(matched))
    names = [r["sample_name"] for r in matched]
    # Independent measured replicates retain separate bars, with unambiguous
    # labels; do not silently average or treat alternative fits as replicates.
    counts = defaultdict(int)
    totals = {name: names.count(name) for name in set(names)}
    labels = []
    for name in names:
        counts[name] += 1
        labels.append(f"{name} (rep {counts[name]})" if totals[name] > 1 else name)
    ax.bar(xx, taus, color=[V1_PALETTE[i%len(V1_PALETTE)] for i in range(len(matched))])
    ax.set_xticks(xx, labels=labels)
    ax.set_yscale("log")
    ax.set_ylabel(r"Relaxation time, $\tau$ (s)")
    ax.set_title(f"Measured at {temp:g} °C", fontsize=10)
    _panel(ax, style, 1)


def export_publication_figure(store: VitriFitStore, run_ids: list[str],
                              kind: str, settings: dict,
                              fmt: str = "tiff", dpi: int = 300,
                              *, kinetic_model: str = "Arrhenius",
                              windows: dict[str, list[float]] | None = None,
                              temperature_c: float | None = None) -> tuple[bytes, str]:
    """Render saved analyses at exact pinned revisions; return bytes and MIME type.

    Uses the current v1 format serializer, RGB/CMYK restrictions, 40 MP pixel
    limit and embedded physical-DPI behavior. Does not mutate figures or fits.
    """
    fmt = str(fmt).lower()
    if fmt not in MIME_TYPES:
        raise ValueError("Unsupported publication export format")
    if type(dpi) is not int or dpi not in (300, 600, 1200):
        raise ValueError("Select 300, 600 or 1200 DPI")
    if kind not in ("relaxation", "kinetics", "fixed_temperature", "eyring", "van_t_hoff"):
        raise ValueError("Unsupported persisted comparison figure type")
    runs = _get_pinned_runs(store, run_ids)
    width, height = _physical_size(settings)
    # Figure 3/4 have their own long-established widget settings, not the
    # generic relaxation/Arrhenius keys. Preserve them for saved exports.
    if kind in ("eyring", "van_t_hoff"):
        prefix = "eyr" if kind == "eyring" else "vh"
        family = str(_val(settings, prefix+"_ff", "Arial"))
        num_family = str(_val(settings, prefix+"_nf", "Same as Label"))
        if num_family == "Same as Label":
            num_family = family
        tick_size = _validated_number(settings, prefix+"_nsz", 10, 4, 30)
    else:
        font_prefix = "pub_kin_" if kind == "kinetics" else "pub_rel_"
        family = str(_val(settings, "pub_kinfont_family" if kind == "kinetics"
                          else "pub_relfont_family", "Arial"))
        num_family = str(_val(settings, font_prefix+"num_font", "Same as Label"))
        if num_family == "Same as Label":
            num_family = family
        tick_size = _validated_number(settings, font_prefix+"num_sz", 10, 4, 30)
    with plt.rc_context({
        "font.family": num_family, "axes.unicode_minus": False,
        "svg.fonttype": "none", "pdf.fonttype": 42,
        "xtick.labelsize": tick_size,
        "ytick.labelsize": tick_size,
    }):
        fig, ax = plt.subplots(figsize=(width/2.54, height/2.54), facecolor="white")
        try:
            if kind in ("eyring", "van_t_hoff"):
                if kind == "eyring":
                    draw_eyring(ax, runs, settings, windows)
                    _panel(ax, settings, 3)
                else:
                    draw_van_t_hoff(ax, runs, settings, windows)
                    _panel(ax, settings, 4)
            else:
                labels = _style_axes(ax, settings,
                                     "kinetics" if kind == "kinetics" else "relaxation")
                if kind == "relaxation":
                    _relaxation(ax, runs, settings)
                elif kind == "kinetics":
                    _kinetics(ax, runs, settings, kinetic_model, windows)
                else:
                    _fixed_temperature(ax, runs, settings, temperature_c)
                ax.xaxis.label.set_fontproperties(mpl.font_manager.FontProperties(**labels))
                ax.yaxis.label.set_fontproperties(mpl.font_manager.FontProperties(**labels))
            fig.tight_layout()
            colorspace = str(_val(settings, "pub_colorspace", "RGB"))
            data = figure_bytes(fig, fmt, dpi=dpi, colorspace=colorspace)
        finally:
            plt.close(fig)
    return data, MIME_TYPES[fmt]
