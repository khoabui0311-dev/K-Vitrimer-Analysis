"""Publication exports from pinned scientific revisions.

Compare the saved image *pixels* after further trimming to guarantee that a
later editing action cannot silently change an older manuscript figure.
"""
from io import BytesIO
import math

import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from vitrifit2.api import app, get_store
from vitrifit2.persistence import VitriFitStore
from vitrifit2.publication_export import export_publication_figure


@pytest.fixture
def populated(tmp_path):
    store = VitriFitStore(tmp_path / "research")
    p = store.create_project("LCE IPN")
    ids = {}
    for material, energy in (("LCE2", 55000.0), ("VUGT", 87000.0)):
        s = store.create_sample(p, material)
        ids[material] = []
        for temperature in (90, 100, 110, 120):
            t = np.geomspace(.01, 200, 80)
            g = 1.8 * np.exp(-(t/45)**.73)
            imported = store.import_experiment(
                s, material + str(temperature) + ".csv",
                (material + str(temperature)).encode(),
                [{"source_curve_id": "relaxation", "temperature_c": temperature,
                  "time_s": t.tolist(), "modulus_mpa": g.tolist()}])
            curve = imported["curve_ids"][0]
            tau = 25.0 * math.exp(energy/8.314462*(1/(temperature+273.15)-1/373.15))
            run = store.save_analysis(curve, "Single_KWW",
                                      "fit:Single_KWW:characteristic",
                                      {"plateau_mode": "Zero"},
                                      {"tau_s": tau, "beta": .73, "r2": .99})
            ids[material].append((curve, run))
    return store, ids


def test_pinned_revision_does_not_follow_new_mask(populated):
    store, ids = populated
    first_curve, first_run = ids["LCE2"][0]
    other_run = ids["VUGT"][0][1]
    settings = {"pub_preset": "ACS/RSC Single-Column (85 x 75 mm)",
                "pub_relfont_family": "DejaVu Sans",
                "pub_taustar": False, "pub_relleg": False}
    saved = store.save_figure("Figure 1", [first_run, other_run], None,
                              {"plot_type": "curves"}, settings)
    prior, _ = export_publication_figure(
        store, store.get_figure(saved)["run_ids"], "relaxation",
        settings, fmt="png", dpi=300)
    pinned = store.get_analysis(first_run)["revision_id"]
    store.apply_region(first_curve, "keep", 1, 120)
    assert store.get_analysis(first_run)["is_current"] is False
    original = store.get_curve_revision(first_curve, pinned)
    assert sum(original["mask"]) == len(original["mask"])
    next_image, _ = export_publication_figure(
        store, store.get_figure(saved)["run_ids"], "relaxation",
        settings, fmt="png", dpi=300)
    with Image.open(BytesIO(prior)) as before, Image.open(BytesIO(next_image)) as after:
        np.testing.assert_array_equal(np.array(before), np.array(after))
    assert sum(store.get_curve(first_curve)["mask"]) < len(original["mask"])


def test_publication_formats_physical_dimensions_and_color(populated):
    store, ids = populated
    runs = [ids["LCE2"][1][1], ids["VUGT"][1][1]]
    settings = {"pub_preset": "ACS/RSC Single-Column (85 x 75 mm)",
                "pub_relfont_family": "DejaVu Sans",
                "pub_ynorm": "Normalized (G/G₀ or E/E₀)",
                "pub_relleg": True,
                "pub_colorspace": "RGB"}
    png, mime = export_publication_figure(store, runs, "relaxation", settings,
                                          fmt="png", dpi=300)
    assert mime == "image/png"
    with Image.open(BytesIO(png)) as img:
        assert img.mode in ("RGB", "RGBA")
        assert abs(img.width - round(8.5/2.54*300)) <= 2
        assert abs(img.height - round(7.5/2.54*300)) <= 2
    svg, svg_mime = export_publication_figure(
        store, runs, "relaxation", settings, fmt="svg", dpi=300)
    assert svg_mime == "image/svg+xml"
    assert b"<svg" in svg and b"font" in svg
    pdf, pdf_mime = export_publication_figure(
        store, runs, "relaxation", settings, fmt="pdf", dpi=300)
    assert pdf_mime == "application/pdf" and pdf.startswith(b"%PDF")
    cmyk = dict(settings, pub_colorspace="CMYK (for Print/Publication)")
    tiff, _ = export_publication_figure(
        store, runs, "relaxation", cmyk, fmt="tiff", dpi=300)
    with Image.open(BytesIO(tiff)) as img:
        assert img.mode == "CMYK"
        assert img.info["dpi"][0] == pytest.approx(300, abs=3)
    with pytest.raises(ValueError, match="CMYK"):
        export_publication_figure(store, runs, "relaxation", cmyk, fmt="svg", dpi=300)


def test_cross_sample_kinetics_and_measured_temperature_exports(populated):
    store, ids = populated
    runs = [rid for group in ids.values() for _, rid in group]
    settings = {"pub_preset": "ACS/RSC Single-Column (85 x 75 mm)",
                "pub_kinfont_family": "DejaVu Sans"}
    arrhenius, _ = export_publication_figure(
        store, runs, "kinetics", settings, fmt="png", dpi=300,
        kinetic_model="Arrhenius")
    vft, _ = export_publication_figure(
        store, runs, "kinetics", settings, fmt="png", dpi=300,
        kinetic_model="VFT",
        windows={store.list_analysis_runs()[0]["sample_id"]: [100, 120]})
    assert len(arrhenius) > 1000 and len(vft) > 1000
    fixed, _ = export_publication_figure(
        store, runs, "fixed_temperature", settings, fmt="png", dpi=300,
        temperature_c=100)
    assert len(fixed) > 1000
    with pytest.raises(ValueError, match="At least two measured"):
        export_publication_figure(store, runs, "fixed_temperature", settings,
                                  fmt="png", dpi=300, temperature_c=105)


def test_export_figure_api_reopens_saved_overrides(populated):
    store, ids = populated
    app.dependency_overrides[get_store] = lambda: store
    try:
        with TestClient(app) as client:
            runs = [ids["LCE2"][1][1], ids["VUGT"][1][1]]
            preset = client.post("/api/figures/presets", json={
                "name": "ACS default", "settings": {
                    "pub_preset": "ACS/RSC Single-Column (85 x 75 mm)",
                    "pub_relfont_family": "DejaVu Sans",
                    "pub_colorspace": "RGB"}})
            assert preset.status_code == 201, preset.text
            figure = client.post("/api/figures", json={
                "name": "Relaxation comparison", "run_ids": runs,
                "preset_id": preset.json()["id"],
                "composition": {"plot_type": "curves"},
                "overrides": {"pub_rel_lw": 2.0}})
            assert figure.status_code == 201, figure.text
            fid = figure.json()["id"]
            response = client.get("/api/figures/" + fid + "/export?fmt=pdf&dpi=300")
            assert response.status_code == 200, response.text[:500] if response.status_code != 200 else ""
            assert response.headers["content-type"].startswith("application/pdf")
            assert response.content.startswith(b"%PDF")
            other = client.get("/api/figures/" + fid + "/export?fmt=tiff&dpi=1200")
            assert other.status_code == 200, other.text[:500] if other.status_code != 200 else ""
            assert other.headers["content-type"].startswith("image/tiff")
            no = client.get("/api/figures/" + fid + "/export?fmt=zip")
            assert no.status_code == 422
    finally:
        app.dependency_overrides.clear()


@pytest.mark.parametrize("model", ["Arrhenius", "VFT"])
def test_kinetic_publication_rejects_duplicate_fits_of_one_curve(populated, model):
    """Two fits of one measured trace cannot count as two observations."""
    store, ids = populated
    curve, _ = ids["LCE2"][0]
    alternate = store.save_analysis(
        curve, "Maxwell", "fit:Single_KWW:characteristic",
        {}, {"tau_s": 100., "r2": .98})
    runs = [rid for _, rid in ids["LCE2"]] + [alternate]
    with pytest.raises(ValueError, match="one analysis run per measured curve"):
        export_publication_figure(
            store, runs, "kinetics",
            {"pub_kinfont_family": "DejaVu Sans"}, fmt="png", dpi=300,
            kinetic_model=model)


@pytest.mark.parametrize("invalid", [float("nan"), float("inf"), -273.15, -300.])
@pytest.mark.parametrize("model", ["Arrhenius", "VFT"])
def test_kinetic_publication_rejects_invalid_temperatures_before_window_filter(
        populated, invalid, model):
    from vitrifit2.publication_export import _get_pinned_runs, _kinetics
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    store, ids = populated
    runs = _get_pinned_runs(store, [rid for _, rid in ids["LCE2"]])
    runs[0] = dict(runs[0], temperature_c=invalid)
    fig, ax = plt.subplots()
    try:
        with pytest.raises(ValueError, match="finite temperatures above absolute zero"):
            _kinetics(ax, runs, {}, model, {runs[0]["sample_id"]: [100, 120]})
    finally:
        plt.close(fig)


@pytest.mark.parametrize("invalid", [float("nan"), float("inf"), -273.15, -300.0])
def test_fixed_temperature_rejects_invalid_saved_metadata(populated, invalid):
    from vitrifit2.publication_export import _fixed_temperature, _get_pinned_runs
    import matplotlib.pyplot as plt
    store, ids = populated
    selected = [rid for group in ids.values() for _, rid in group]
    runs = _get_pinned_runs(store, selected)
    runs[0] = dict(runs[0], temperature_c=invalid)
    fig, ax = plt.subplots()
    try:
        with pytest.raises(ValueError, match="finite and above absolute zero"):
            _fixed_temperature(ax, runs, {}, 100)
    finally:
        plt.close(fig)


def test_fixed_temperature_rejects_alternative_fits_as_replicates(populated):
    store, ids = populated
    curve, _ = ids["LCE2"][1]
    duplicate = store.save_analysis(
        curve, "Maxwell", "fit:Single_KWW:characteristic",
        {}, {"tau_s": 200.0, "r2": .95})
    runs = [ids["LCE2"][1][1], ids["VUGT"][1][1], duplicate]
    with pytest.raises(ValueError, match="one analysis run per measured curve"):
        export_publication_figure(
            store, runs, "fixed_temperature",
            {"pub_relfont_family": "DejaVu Sans"}, fmt="png", dpi=300,
            temperature_c=100)


def test_fixed_temperature_rejects_nonphysical_requested_temperature(populated):
    store, ids = populated
    runs = [ids["LCE2"][1][1], ids["VUGT"][1][1]]
    with pytest.raises(ValueError, match="above absolute zero"):
        export_publication_figure(
            store, runs, "fixed_temperature",
            {"pub_relfont_family": "DejaVu Sans"}, fmt="png", dpi=300,
            temperature_c=-273.15)


@pytest.mark.parametrize("axis", ["x", "y"])
def test_logarithmic_publication_rejects_nonpositive_manual_limits(populated, axis):
    store, ids = populated
    runs = [ids["LCE2"][1][1], ids["VUGT"][1][1]]
    settings = {
        "pub_relfont_family": "DejaVu Sans",
        "pub_xscale": "Log", "pub_yscale": "Log",
        "pub_rel_cust_lims": True,
        "pub_rel_xmin": 0.01, "pub_rel_xmax": 200,
        "pub_rel_ymin": 0.001, "pub_rel_ymax": 2,
    }
    settings[f"pub_rel_{axis}min"] = 0
    with pytest.raises(ValueError, match=f"Logarithmic {axis.upper()}-axis limits must be positive"):
        export_publication_figure(
            store, runs, "relaxation", settings, fmt="png", dpi=300)


def test_marker_only_publication_requires_visible_markers(populated):
    store, ids = populated
    runs = [ids["LCE2"][1][1], ids["VUGT"][1][1]]
    with pytest.raises(ValueError, match="positive marker density"):
        export_publication_figure(store, runs, "relaxation", {
            "pub_relfont_family": "DejaVu Sans",
            "pub_style": "Markers Only", "pub_rel_md": 0,
        }, fmt="png", dpi=300)


@pytest.mark.parametrize("fit_t,fit_g,expected", [
    ([0.01, 1.0], [1.0], "equal-length finite"),
    ([0.01, float("nan")], [1.0, .8], "equal-length finite"),
    ([1.0, 0.01], [1.0, .8], "strictly increasing"),
    ([0.0, 1.0], [1.0, .8], "positive times"),
    ([0.01, 1.0], [1.0, 0.0], "positive predictions"),
])
def test_publication_rejects_invalid_saved_fit_overlays(
        populated, fit_t, fit_g, expected):
    from vitrifit2.publication_export import _get_pinned_runs, _relaxation
    import matplotlib.pyplot as plt
    store, ids = populated
    runs = _get_pinned_runs(store, [ids["LCE2"][1][1]])
    runs[0] = dict(runs[0])
    runs[0]["analysis"] = dict(runs[0]["analysis"])
    results = dict(runs[0]["analysis"]["results"])
    results.update(fit_time_s=fit_t, fit_normalized_prediction=fit_g)
    runs[0]["analysis"]["results"] = results
    fig, ax = plt.subplots()
    try:
        with pytest.raises(ValueError, match=expected):
            _relaxation(ax, runs, {
                "pub_showfit": True, "pub_xscale": "Log",
                "pub_yscale": "Log", "pub_taustar": False,
            })
    finally:
        plt.close(fig)


@pytest.mark.parametrize("scale", ["Linear", "Log"])
def test_publication_autolimits_include_measured_overshoot_and_tail(populated, scale):
    from vitrifit2.publication_export import _get_pinned_runs, _relaxation
    import matplotlib.pyplot as plt
    import numpy as np
    store, ids = populated
    runs = _get_pinned_runs(store, [ids["LCE2"][1][1]])
    runs[0] = dict(runs[0], modulus_mpa=np.array([1.0, 1.3, 0.0001]))
    runs[0]["time_s"] = np.array([0.01, 1.0, 100.0])
    fig, ax = plt.subplots()
    try:
        _relaxation(ax, runs, {
            "pub_yscale": scale, "pub_taustar": False,
            "pub_ynorm": "Normalized (G/G₀ or E/E₀)",
        })
        lower, upper = ax.get_ylim()
        assert lower < 0.0001
        assert upper > 1.3
    finally:
        plt.close(fig)


def test_fixed_temperature_rejects_one_sample_replicates_as_comparison(populated):
    from vitrifit2.publication_export import _fixed_temperature, _get_pinned_runs
    import matplotlib.pyplot as plt
    store, ids = populated
    runs = _get_pinned_runs(store, [ids["LCE2"][0][1], ids["LCE2"][1][1]])
    runs[0] = dict(runs[0], temperature_c=100)
    fig, ax = plt.subplots()
    try:
        with pytest.raises(ValueError, match="at least two distinct samples"):
            _fixed_temperature(ax, runs, {}, 100)
    finally:
        plt.close(fig)


def test_fixed_temperature_labels_independent_replicates(populated):
    from vitrifit2.publication_export import _fixed_temperature, _get_pinned_runs
    import matplotlib.pyplot as plt
    store, ids = populated
    runs = _get_pinned_runs(store, [
        ids["LCE2"][0][1], ids["LCE2"][1][1], ids["VUGT"][1][1]])
    runs[0] = dict(runs[0], temperature_c=100)
    fig, ax = plt.subplots()
    try:
        _fixed_temperature(ax, runs, {}, 100)
        labels = [tick.get_text() for tick in ax.get_xticklabels()]
        assert "LCE2 (rep 1)" in labels
        assert "LCE2 (rep 2)" in labels
        assert "VUGT" in labels
    finally:
        plt.close(fig)


def test_kinetic_publication_rejects_one_temperature_per_sample(populated):
    store, ids = populated
    runs = [ids["LCE2"][1][1], ids["VUGT"][1][1]]
    with pytest.raises(ValueError, match="two distinct measured temperatures per sample"):
        export_publication_figure(store, runs, "kinetics",
                                  {"pub_kinfont_family": "DejaVu Sans"},
                                  fmt="png", dpi=300)


@pytest.mark.parametrize("dpi", [True, "300", 300.0, None])
def test_publication_rejects_noninteger_dpi(populated, dpi):
    store, ids = populated
    with pytest.raises(ValueError, match="300, 600 or 1200 DPI"):
        export_publication_figure(store, [ids["LCE2"][1][1]],
                                  "relaxation", {}, fmt="png", dpi=dpi)


def test_publication_rejects_excessive_pinned_run_selection(populated):
    from vitrifit2.publication_export import _get_pinned_runs
    store, ids = populated
    unique_runs = [f"run-{index}" for index in range(101)]
    with pytest.raises(ValueError, match="at most 100"):
        _get_pinned_runs(store, unique_runs)


@pytest.mark.parametrize("bad_id", ["", "   ", None, 42])
def test_publication_rejects_invalid_run_identifiers(populated, bad_id):
    from vitrifit2.publication_export import _get_pinned_runs
    store, _ = populated
    with pytest.raises(ValueError, match="nonempty strings"):
        _get_pinned_runs(store, [bad_id])


def test_publication_rejects_unhashable_run_identifier_cleanly(populated):
    from vitrifit2.publication_export import _get_pinned_runs
    store, _ = populated
    with pytest.raises(ValueError, match="nonempty strings"):
        _get_pinned_runs(store, [["not-an-id"]])


@pytest.mark.parametrize("selection", [None, "run-id", 3, {}])
def test_publication_rejects_nonsequence_run_selection(populated, selection):
    from vitrifit2.publication_export import _get_pinned_runs
    store, _ = populated
    with pytest.raises(ValueError, match="nonempty sequence"):
        _get_pinned_runs(store, selection)
