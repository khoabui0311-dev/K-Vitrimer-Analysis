"""End-to-end local API regressions for VitriFit 2.0."""
import math

import numpy as np
import pytest
from fastapi.testclient import TestClient

from vitrifit2.api import app, get_store
from vitrifit2.persistence import VitriFitStore


@pytest.fixture
def env(tmp_path):
    store = VitriFitStore(tmp_path / "v2")
    app.dependency_overrides[get_store] = lambda: store
    with TestClient(app) as client:
        yield client, store
    app.dependency_overrides.clear()


def make_csv(temp=100, tau=45):
    times = np.geomspace(.01, 400, 190)
    lines = [str(temp) + ",", "Time,Modulus"]
    for t in times:
        lines.append("{:.9f},{:.12f}".format(t, 1.25 * np.exp(-t / tau)))
    return ("\n".join(lines) + "\n").encode()


def test_api_import_trim_undo_fit_and_reopen(env):
    client, store = env
    assert client.get("/api/health").json()["status"] == "ok"
    project = client.post("/api/projects", json={"name": "LCE-IPN"}).json()["id"]
    sample = client.post("/api/projects/" + project + "/samples", json={"name": "VUGT"}).json()["id"]
    content = make_csv()
    response = client.post("/api/samples/" + sample + "/experiments",
                           files={"file": ("raw.csv", content, "text/csv")})
    assert response.status_code == 201, response.text
    exp = response.json()
    assert store.get_original_file(exp["experiment_id"]) == content
    cid = client.get("/api/experiments/" + exp["experiment_id"] + "/curves").json()[0]["id"]
    before = client.get("/api/curves/" + cid).json()
    assert len(before["mask"]) == 190
    update = client.post("/api/curves/" + cid + "/region",
                         json={"mode": "keep", "start_s": .2, "end_s": 300})
    assert update.status_code == 200, update.text
    trimmed = update.json()["curve"]
    assert sum(trimmed["mask"]) < len(before["mask"])
    assert trimmed["time_s"] == before["time_s"]
    fitted = client.post("/api/curves/" + cid + "/fit",
                         json={"model": "Single_KWW", "component": "characteristic"})
    assert fitted.status_code == 201, fitted.text
    analysis = fitted.json()
    assert analysis["results"]["tau_s"] == pytest.approx(45, rel=.05)
    assert analysis["results"]["r2"] > .99
    saved = client.get("/api/analyses/" + analysis["run_id"]).json()
    assert saved["is_current"]
    excluded = client.post("/api/curves/" + cid + "/region",
                           json={"mode": "exclude", "start_s": 80, "end_s": 100})
    assert excluded.status_code == 200
    assert not client.get("/api/analyses/" + analysis["run_id"]).json()["is_current"]
    client.post("/api/curves/" + cid + "/undo")
    assert client.get("/api/analyses/" + analysis["run_id"]).json()["is_current"]
    reopened = VitriFitStore(store.root)
    assert reopened.get_curve(cid)["active_revision_id"] == trimmed["active_revision_id"]


def test_kinetic_and_fixed_temperature_cross_sample(env):
    client, store = env
    project = store.create_project("LCE-IPN")
    all_runs = []
    for sample_name, activation in (("LCE2", 60000), ("VUGT", 85000)):
        sample = store.create_sample(project, sample_name)
        for tc in (90, 100, 110, 120):
            data = store.import_experiment(sample, "raw.csv", (sample_name+str(tc)).encode(),
                [{"source_curve_id": "curve", "temperature_c": tc,
                  "time_s": [0.01, 1.0, 2.0],
                  "modulus_mpa": [2.0, 1.5, 1.0]}])
            tau = 20 * math.exp(activation/8.314462 * (1/(tc+273.15)-1/373.15))
            run = store.save_analysis(data["curve_ids"][0], "Single_KWW",
                                      "fit:Single_KWW:characteristic", {},
                                      {"tau_s": tau, "r2": .99})
            all_runs.append(run)
    payload = {"run_ids": all_runs, "mode": "kinetics", "kinetic_model": "Arrhenius"}
    response = client.post("/api/compare", json=payload)
    assert response.status_code == 200, response.text
    sample_fits = response.json()["samples"]
    assert len(sample_fits) == 2
    assert sorted(round(x["Ea_kj_mol"]) for x in sample_fits) == [60,85]
    same_temp = client.post("/api/compare", json={"run_ids": all_runs,
                             "mode": "fixed_temperature", "temperature_c": 100})
    assert same_temp.status_code == 200
    assert len(same_temp.json()["rows"]) == 2
    no_measurement = client.post("/api/compare", json={"run_ids": all_runs,
                             "mode": "fixed_temperature", "temperature_c": 105})
    assert no_measurement.status_code == 422


def test_figure_presets_round_trip_and_stale_fit_rejection(env):
    client, store = env
    preset = client.post("/api/figures/presets", json={"name": "ACS 85 mm",
        "settings": {"pub_preset": "ACS/RSC Single-Column (85 x 75 mm)",
                     "pub_rel_lw": 2.5, "pub_rel_num_sz": 10}})
    assert preset.status_code == 201
    identifier = preset.json()["id"]
    assert client.get("/api/figures/presets/" + identifier).json()["settings"]["pub_rel_lw"] == 2.5

    sample = store.create_sample(store.create_project("Project"), "Sample")
    imported = store.import_experiment(sample, "test.csv", b"raw",
        [{"source_curve_id": "c1", "temperature_c": 100,
          "time_s": [0, 1, 2, 3], "modulus_mpa": [2, 1.5, 1, .5]},
         {"source_curve_id": "c2", "temperature_c": 100,
          "time_s": [0, 1, 2, 3], "modulus_mpa": [2, 1.6, 1.1, .6]}])
    r1, r2 = [store.save_analysis(cid, "Maxwell", "fit:Maxwell:characteristic", {},
                                   {"tau_s": 10}) for cid in imported["curve_ids"]]
    fig = client.post("/api/figures", json={"name": "Figure 1",
        "run_ids": [r1, r2], "preset_id": identifier,
        "composition": {"panels": ["a", "b"]}, "overrides": {"pub_rel_lw": 3.0}})
    assert fig.status_code == 201
    assert client.get("/api/figures/" + fig.json()["id"]).json()["overrides"]["pub_rel_lw"] == 3.0
    store.apply_region(imported["curve_ids"][0], "keep", 0, 2)
    response = client.post("/api/compare", json={"mode": "curves", "run_ids": [r1, r2]})
    assert response.status_code == 422
    assert "stale" in response.json()["detail"].lower()
