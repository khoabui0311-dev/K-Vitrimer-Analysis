"""Scientific cross-sample comparison using explicit saved analysis revisions.

No hidden interpolation between measurement temperatures. Kinetic regressions
reuse the existing KineticsEngine and permit a separate window per sample.
"""
from __future__ import annotations

from collections import defaultdict
import math

from scipy.stats import t as student_t

from can_relax.core.kinetics import KineticsEngine
from .persistence import VitriFitStore


def _finite(value):
    value = float(value)
    return value if math.isfinite(value) else None


def compare_runs(store: VitriFitStore, run_ids: list[str], mode: str,
                 temperature_c: float | None = None,
                 kinetic_model: str = "Arrhenius",
                 windows: dict[str, list[float]] | None = None) -> dict:
    if not run_ids or len(set(run_ids)) < 2:
        raise ValueError("Select at least two different analysis runs")
    if mode not in ("curves", "fixed_temperature", "kinetics"):
        raise ValueError("Unknown comparison mode")
    catalog = {row["id"]: row for row in store.list_analysis_runs()}
    missing = [key for key in run_ids if key not in catalog]
    if missing:
        raise KeyError(f"Unknown analysis run: {missing[0]}")
    records = [catalog[r] for r in run_ids]
    definitions = {r["tau_definition"] for r in records}
    if len(definitions) != 1:
        raise ValueError("Comparisons require a consistent relaxation-time definition")
    if any(not r["is_current"] for r in records):
        raise ValueError("A selected fit is stale after trimming; re-fit or explicitly restore its revision")

    rows = []
    for r in records:
        result = r["results"]
        tau = result.get("tau_s")
        if tau is None or not math.isfinite(float(tau)) or tau <= 0:
            raise ValueError(f"Missing valid tau in analysis {r['id']}")
        rows.append({
            "run_id": r["id"], "curve_id": r["curve_id"],
            "sample_id": r["sample_id"], "sample": r["sample_name"],
            "project": r["project_name"],
            "temperature_c": float(r["temperature_c"]),
            "model": r["model"], "tau_definition": r["tau_definition"],
            "tau_s": float(tau),
            "r2": result.get("r2"),
            "fit_flags": list(result.get("flags") or []),
        })
    if mode == "fixed_temperature":
        if temperature_c is None or not math.isfinite(float(temperature_c)):
            raise ValueError("Select the measured comparison temperature")
        selected = [r for r in rows if abs(r["temperature_c"] - float(temperature_c)) < 1e-6]
        if len(selected) < 2:
            raise ValueError(f"At least two matching measurements at {temperature_c} °C are needed; no interpolation was performed")
        return {"mode": mode, "temperature_c": temperature_c, "rows": selected,
                "missing_run_ids": [r["run_id"] for r in rows if r not in selected],
                "tau_definition": rows[0]["tau_definition"],
                "interpolation": False}

    if mode == "curves":
        overlays = []
        for row in rows:
            curve = store.get_curve(row["curve_id"])
            t = [v for v, use in zip(curve["time_s"], curve["mask"]) if use]
            g = [v for v, use in zip(curve["modulus_mpa"], curve["mask"]) if use]
            if not t or not g:
                continue
            overlays.append({**row, "time_s": t, "modulus_mpa": g,
                             "normalized_modulus": [v/g[0] for v in g]})
        return {"mode": mode, "curves": overlays,
                "tau_definition": rows[0]["tau_definition"]}

    if kinetic_model not in ("Arrhenius", "VFT"):
        raise ValueError("Unknown kinetic model")
    grouped = defaultdict(list)
    excluded_unresolved = []
    for row in rows:
        if any("Tau outside measurement window" in str(flag)
               for flag in row["fit_flags"]):
            excluded_unresolved.append(row["run_id"])
            continue
        bounds = (windows or {}).get(row["sample_id"])
        if bounds is not None:
            if len(bounds) != 2 or bounds[0] > bounds[1]:
                raise ValueError("Each sample window needs [minimum °C, maximum °C]")
            if not bounds[0] <= row["temperature_c"] <= bounds[1]:
                continue
        grouped[row["sample_id"]].append(row)
    samples = []
    for sample_id, group in grouped.items():
        ts = [r["temperature_c"] for r in group]
        taus = [r["tau_s"] for r in group]
        engine = KineticsEngine()
        fit = engine.fit_arrhenius(ts, taus) if kinetic_model == "Arrhenius" else engine.fit_vft(ts, taus)
        entry = {"sample_id": sample_id, "sample": group[0]["sample"],
                 "project": group[0]["project"],
                 "observations": group, "fit_available": fit is not None,
                 "n_observations": len(group),
                 "n_distinct_temperatures": len(set(ts)),
                 "retained_temperature_range_c": [min(ts), max(ts)]}
        if fit is None:
            entry["warning"] = "Insufficient distinct temperatures or unsuccessful fit"
        else:
            entry["r2"] = _finite(fit["R2"])
            if kinetic_model == "Arrhenius":
                entry["Ea_kj_mol"] = _finite(fit["Ea"])
                entry["Ea_std_kj_mol"] = _finite(fit["Ea_std"])
                entry["slope"] = _finite(fit["Params"]["slope"])
                entry["intercept"] = _finite(fit["Params"]["intercept"])
                n_distinct = len(set(ts))
                if n_distinct == 2:
                    entry["r2"] = None
                    entry["Ea_std_kj_mol"] = None
                    entry["Ea_ci95_kj_mol"] = None
                    entry["warning"] = "Two-point slope only; R² and confidence interval are undefined"
                else:
                    stderr = entry["Ea_std_kj_mol"]
                    if stderr is not None and math.isfinite(stderr):
                        margin = float(student_t.ppf(0.975, n_distinct - 2) * stderr)
                        entry["Ea_ci95_kj_mol"] = [
                            entry["Ea_kj_mol"] - margin, entry["Ea_kj_mol"] + margin]
                    else:
                        entry["Ea_ci95_kj_mol"] = None
                    entry["warning"] = (
                        "Only three distinct temperatures; confidence interval is highly uncertain"
                        if n_distinct == 3 else fit.get("Warning"))
            else:
                entry["parameters"] = {k: _finite(v) for k,v in fit["Params"].items()}
                if len(set(ts)) < 5:
                    entry["warning"] = "VFT with fewer than five distinct temperatures: T0 is poorly constrained"
            # Publication/interactive plot points are generated from the fitted
            # equation strictly within this sample's selected measured window.
            # This is not extrapolation and cannot fill missing experimental data.
            low_x = 1000.0 / (max(ts) + 273.15)
            high_x = 1000.0 / (min(ts) + 273.15)
            x_grid = [low_x + (high_x - low_x) * i / 99 for i in range(100)]
            if kinetic_model == "Arrhenius":
                predictions = [fit["Params"]["slope"] * x / 1000.0
                               + fit["Params"]["intercept"] for x in x_grid]
            else:
                params = fit["Params"]
                predictions = [params["A"] + params["B"] /
                               (1000.0 / x - params["T0"]) for x in x_grid]
            if all(math.isfinite(value) for value in predictions):
                entry["fitted_curve"] = {
                    "x_1000_per_k": x_grid,
                    "ln_tau": predictions,
                    "measured_window_c": [min(ts), max(ts)],
                    "extrapolated": False,
                }
        samples.append(entry)
    return {"mode": mode, "kinetic_model": kinetic_model, "samples": samples,
            "tau_definition": rows[0]["tau_definition"],
            "windows_c": windows or {},
            "excluded_unresolved_run_ids": excluded_unresolved,
            "exclusion_policy": "Exclude fitted tau outside measured time window from kinetics",
            "fit_input": "measured fitted relaxation times; independent windows per sample"}
