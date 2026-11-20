"""Eyring and empirical Van 't Hoff reproduction from saved analysis versions.

Scientific baselines are synthetic and never contain laboratory observations.
These tests verify the *existing* KineticsEngine equations, journal controls,
temperature windows and immutable prepared-curve references.
"""
from io import BytesIO
import math

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from can_relax.core.kinetics import (
    KineticsEngine, H_PLANCK, K_BOLTZMANN, R_GAS, predict_van_t_hoff
)
from vitrifit2.api import app, get_store
from vitrifit2.persistence import VitriFitStore
from vitrifit2.publication_export import _get_pinned_runs, export_publication_figure
from vitrifit2.thermodynamic_figures import draw_eyring, draw_van_t_hoff


@pytest.fixture
def saved(tmp_path):
    store = VitriFitStore(tmp_path / "science")
    project = store.create_project("LCE2–VUGT comparison")
    runs = {}
    for sample_name, dH, dS, A, vh_enthalpy, vh_entropy in (
        ("LCE2", 75000., -100., .010, 80000., 180.),
        ("VUGT", 82000., -75., .012, 89000., 192.),
    ):
        sample_id = store.create_sample(project, sample_name)
        runs[sample_name] = []
        for temp in [70., 90., 110., 130., 150.]:
            T_K = temp + 273.15
            ln_tau_T = math.log(H_PLANCK / K_BOLTZMANN) - dS / R_GAS + dH/(R_GAS*T_K)
            tau = math.exp(ln_tau_T) / T_K
            g0 = float(predict_van_t_hoff(T_K, A, vh_enthalpy, vh_entropy))
            source = (sample_name + str(temp)).encode()
            imported = store.import_experiment(
                sample_id, sample_name + ".csv", source,
                [{"source_curve_id": "relaxation", "temperature_c": temp,
                  "time_s": [.01, 1, 10, 100, 500],
                  "modulus_mpa": [g0, g0*.9, g0*.7, g0*.4, g0*.15]}])
            cid = imported["curve_ids"][0]
            rid = store.save_analysis(cid, "Single_KWW",
                                      "fit:Single_KWW:characteristic",
                                      {"plateau_mode": "Zero"},
                                      {"tau_s": tau, "reference_modulus_mpa": g0,
                                       "r2": .999, "beta": .7})
            runs[sample_name].append((cid, rid))
    return store, runs


def test_eyring_uses_existing_equations_and_selected_temperature_window(saved):
    store, runs = saved
    chosen = [r for _, r in runs["LCE2"]]
    all_points = _get_pinned_runs(store, chosen)
    fig, ax = plt.subplots(figsize=(4, 3))
    try:
        metrics = draw_eyring(ax, all_points, {
            "eyr_ff": "DejaVu Sans", "eyr_lw": 2.5, "eyr_ms": 9,
            "eyr_mir": True, "eyr_legpos": "Upper Left"}, windows=None)
        assert len(metrics) == 1
        assert metrics[0]["dH_kj_mol"] == pytest.approx(75, abs=.01)
        assert metrics[0]["dS_j_mol_k"] == pytest.approx(-100, abs=.01)
        assert "1000/T" in ax.get_xlabel()
        assert r"\ln(\tau \cdot T)" in ax.get_ylabel()
        assert ax.get_lines()[0].get_linewidth() == pytest.approx(2.5)
        assert ax.get_lines()[0].get_color() == "red"
        # No silently extrapolated points outside the selected measurements.
        actual_x = [1000/(r["temperature_c"]+273.15) for r in all_points]
        assert min(ax.get_lines()[0].get_xdata()) == pytest.approx(min(actual_x))
        assert max(ax.get_lines()[0].get_xdata()) == pytest.approx(max(actual_x))
    finally:
        plt.close(fig)

    fig, ax = plt.subplots()
    try:
        sample_id = all_points[0]["sample_id"]
        narrowed = draw_eyring(ax, all_points, {}, {sample_id: [90, 130]})
        assert narrowed[0]["temperature_min_c"] == 90
        assert narrowed[0]["temperature_max_c"] == 130
    finally:
        plt.close(fig)


def test_mixed_relaxation_time_definitions_are_rejected(saved):
    store, runs = saved
    curve, _ = runs["LCE2"][0]
    extra = store.save_analysis(curve, "Maxwell", "fit:Maxwell:characteristic",
                                {}, {"tau_s": 80., "reference_modulus_mpa": 2.0})
    mixed = _get_pinned_runs(store, [runs["LCE2"][1][1], extra])
    fig, ax = plt.subplots()
    try:
        with pytest.raises(ValueError, match="consistent relaxation-time definition"):
            draw_eyring(ax, mixed, {}, None)
    finally:
        plt.close(fig)


def test_empirical_van_t_hoff_uses_observed_reference_modulus_and_v1_scale(saved):
    store, runs = saved
    points = _get_pinned_runs(store, [r for _, r in runs["LCE2"]])
    fig, ax = plt.subplots()
    try:
        metrics = draw_van_t_hoff(ax, points, {
            "vh_ff": "DejaVu Sans", "vh_lw": 2.5, "vh_ms": 8,
            "vh_yscale": "Log", "vh_leg": False,
        }, None)
        assert len(metrics) == 1
        assert metrics[0]["interpretation"] == "empirical reference-modulus trend"
        assert metrics[0]["dH_kj_mol"] == pytest.approx(80, abs=3)
        assert ax.get_yscale() == "log"
        assert ax.get_lines()[0].get_linewidth() == pytest.approx(2.5)
        assert ax.get_lines()[0].get_color() == "red"
        assert ax.get_legend() is None
        assert "$G_0$ (MPa)" == ax.get_ylabel()
        assert np.asarray(ax.collections[0].get_offsets())[:,1].tolist() == pytest.approx(
            [r["analysis"]["results"]["reference_modulus_mpa"] for r in points])
    finally:
        plt.close(fig)


def test_van_t_hoff_requires_four_distinct_temperatures_and_unique_curves(saved):
    store, runs = saved
    short = _get_pinned_runs(store, [r for _, r in runs["LCE2"][:3]])
    fig, ax = plt.subplots()
    try:
        with pytest.raises(ValueError, match="4 distinct"):
            draw_van_t_hoff(ax, short, {}, None)
    finally:
        plt.close(fig)
    chosen = [r for _, r in runs["LCE2"]]
    duplicated = _get_pinned_runs(store, chosen)
    duplicate_run = store.save_analysis(runs["LCE2"][0][0], "Maxwell",
        "fit:Maxwell:characteristic", {}, {"tau_s": 1, "reference_modulus_mpa": 2})
    duplicated += _get_pinned_runs(store, [duplicate_run])
    fig, ax = plt.subplots()
    try:
        with pytest.raises(ValueError, match="one analysis run per measured curve"):
            draw_van_t_hoff(ax, duplicated, {}, None)
    finally:
        plt.close(fig)


def test_stale_source_does_not_change_saved_figures(saved):
    store, runs = saved
    chosen = [r for _, r in runs["LCE2"]]
    styles = {"pub_preset": "ACS/RSC Single-Column (85 x 75 mm)",
              "eyr_ff": "DejaVu Sans", "vh_ff": "DejaVu Sans"}
    for kind in ("eyring", "van_t_hoff"):
        before, mime = export_publication_figure(
            store, chosen, kind, styles, fmt="png", dpi=300)
        assert mime == "image/png"
        assert len(before) > 1000
        cid = runs["LCE2"][0][0]
        store.apply_region(cid, "keep", 1, 100)
        after, _ = export_publication_figure(
            store, chosen, kind, styles, fmt="png", dpi=300)
        with Image.open(BytesIO(before)) as a, Image.open(BytesIO(after)) as b:
            np.testing.assert_array_equal(np.asarray(a), np.asarray(b))


def test_api_exports_saved_eyring_and_van_t_hoff_figures(saved):
    store, runs = saved
    app.dependency_overrides[get_store] = lambda: store
    try:
        with TestClient(app) as client:
            selected = [r for _, r in runs["LCE2"]]
            for figure_kind in ("eyring", "van_t_hoff"):
                response = client.post("/api/figures", json={
                    "name": figure_kind,
                    "run_ids": selected,
                    "composition": {"plot_type": figure_kind},
                    "overrides": {"pub_preset": "ACS/RSC Single-Column (85 x 75 mm)",
                                  "eyr_ff": "DejaVu Sans", "vh_ff": "DejaVu Sans",
                                  "vh_yscale": "Linear"}})
                assert response.status_code == 201, response.text
                identifier = response.json()["id"]
                exported = client.get("/api/figures/" + identifier +
                                      "/export?fmt=svg&dpi=300")
                assert exported.status_code == 200, exported.text[:500] if exported.status_code != 200 else ""
                assert exported.headers["content-type"].startswith("image/svg+xml")
                assert b"<svg" in exported.content
                exported_pdf = client.get("/api/figures/" + identifier +
                                          "/export?fmt=pdf&dpi=300")
                assert exported_pdf.status_code == 200
                assert exported_pdf.content.startswith(b"%PDF")
    finally:
        app.dependency_overrides.clear()
