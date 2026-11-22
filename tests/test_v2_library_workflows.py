"""Regression coverage for queue retries, sample notes, and draft figures."""
import json
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from vitrifit2.api import app, get_store
from vitrifit2.persistence import VitriFitStore


@pytest.fixture
def library(tmp_path):
    store = VitriFitStore(tmp_path)
    project = store.create_project("Project")
    sample_a = store.create_sample(project, "Sample A")
    sample_b = store.create_sample(project, "Sample B")
    app.dependency_overrides[get_store] = lambda: store
    try:
        with TestClient(app) as client:
            yield client, store, sample_a, sample_b
    finally:
        app.dependency_overrides.pop(get_store)


def test_queue_preserves_review_and_can_retry_without_duplicates(library):
    client, store, sample_a, sample_b = library
    upload = {"file": ("same-name.csv", b"Temp,Time,Modulus\n100,0,4\n,1,3\n,2,2\n")}
    preview = client.post("/api/import-preview", files=upload).json()
    assert preview["needs_review"]
    metadata = {
        "preview_sha256": preview["file_sha256"],
        "preview_curve_count": preview["curve_count"],
    }
    request_id = str(uuid4())

    def save(sample, key):
        return client.post(f"/api/samples/{sample}/experiments", files=upload,
                           data={"request_id": key, "metadata": json.dumps(metadata)})

    assert save(sample_a, request_id).status_code == 422
    assert store.list_experiments(sample_a) == []
    metadata["review_warnings_acknowledged"] = True
    first = save(sample_a, request_id)
    assert first.status_code == 201
    assert save(sample_a, request_id).json() == first.json()
    assert save(sample_b, request_id).status_code == 422
    second = save(sample_b, str(uuid4()))
    assert second.status_code == 201
    assert second.json()["experiment_id"] != first.json()["experiment_id"]
    assert len(store.list_experiments(sample_a)) == len(store.list_experiments(sample_b)) == 1
    assert len(list(store.blobs.iterdir())) == 1


def test_notes_are_sample_scoped_persistent_and_conflict_safe(library):
    client, store, sample_a, sample_b = library
    path = f"/api/samples/{sample_a}/notes"
    assert client.get(path).json() == {"text": "", "revision": 0, "updated_at": None}
    text = "Prepared at 110 °C\nRepeat DSC on next heating."
    saved = client.put(path, json={"text": text, "revision": 0}).json()
    assert saved["revision"] == 1
    assert client.put(path, json={"text": "Stale edit", "revision": 0}).status_code == 409
    assert VitriFitStore(store.root).get_sample_notes(sample_a) == saved
    assert client.get(f"/api/samples/{sample_b}/notes").json()["text"] == ""
    assert client.put(path, json={"text": "", "revision": 1}).json()["revision"] == 2


def test_preview_uses_saved_revision_without_creating_a_figure(library):
    client, store, sample_a, _ = library
    curve_id = store.import_experiment(
        sample_a, "run.csv", b"original bytes",
        [{"source_curve_id": "run", "temperature_c": 100,
          "time_s": [1, 2, 4, 8], "modulus_mpa": [4, 3, 2, 1]}],
    )["curve_ids"][0]
    revision = store.get_curve(curve_id)["active_revision_id"]
    store.apply_region(curve_id, "keep", 2, 8)
    run_id = store.save_analysis(
        curve_id, "Maxwell", "fit:Maxwell:characteristic", {}, {"tau_s": 4},
        revision_id=revision,
    )
    run = store.get_analysis(run_id)
    assert run["revision_id"] == revision
    assert not run["is_current"]

    response = client.post("/api/figures/preview", json={
        "run_ids": [run_id], "composition": {"plot_type": "curves"},
        "overrides": {"pub_relfont_family": "DejaVu Sans", "pub_colorspace": "CMYK"},
    })
    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("image/svg+xml")
    assert b"<svg" in response.content
    assert store.list_saved_figures() == []


def test_curve_overlay_reports_measured_excluded_and_fitted_series(library):
    client, store, *samples = library
    run_ids = []
    for name, sample in zip(("first.csv", "second.csv"), samples):
        curve_id = store.import_experiment(
            sample, name, name.encode(),
            [{"source_curve_id": "replicate", "temperature_c": 100,
              "time_s": [0, 1, 2, 3], "modulus_mpa": [8, 4, 2, 1]}],
        )["curve_ids"][0]
        store.apply_region(curve_id, "keep", 1, 3)
        run_ids.append(store.save_analysis(
            curve_id, "Maxwell", "fit:Maxwell:characteristic", {},
            {"tau_s": 2, "fit_time_s": [1, 2, 3],
             "fit_normalized_prediction": [1, 0.6, 0.36]},
        ))

    response = client.post("/api/compare", json={"run_ids": run_ids, "mode": "curves"})
    assert response.status_code == 200, response.text
    first, second = response.json()["curves"]
    assert first["sample_id"] != second["sample_id"]
    assert first["original_filename"] == "first.csv"
    assert first["normalized_modulus"] == [1, 0.5, 0.25]
    assert first["excluded_time_s"] == [0]
    assert first["excluded_normalized_modulus"] == [2]
    assert first["fit_normalized_prediction"] == [1, 0.6, 0.36]
