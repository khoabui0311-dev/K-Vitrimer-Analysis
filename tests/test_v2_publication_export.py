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
