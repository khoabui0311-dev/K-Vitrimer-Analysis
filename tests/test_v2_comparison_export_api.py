"""API regression: comparison CSV download is local and preserves provenance."""
import csv
from io import StringIO

from fastapi.testclient import TestClient

from vitrifit2.api import app, get_store
from vitrifit2.persistence import VitriFitStore


def test_comparison_csv_download_and_missing_session(tmp_path):
    store = VitriFitStore(tmp_path / "research")
    project = store.create_project("Synthetic")
    run_ids = []
    for name in ("LCE2", "VUGT"):
        sample = store.create_sample(project, name)
        experiment = store.import_experiment(
            sample, name + ".csv", name.encode(),
            [{"source_curve_id": "relax", "temperature_c": 100,
              "time_s": [0.01, 1, 10], "modulus_mpa": [1, .8, .3]}])
        run_ids.append(store.save_analysis(
            experiment["curve_ids"][0], "KWW", "1/e", {},
            {"tau_s": 10.0}))
    comparison_id = store.save_comparison(
        "100C synthetic", "fixed_temperature", run_ids)
    app.dependency_overrides[get_store] = lambda: store
    try:
        with TestClient(app) as client:
            response = client.get(f"/api/comparisons/{comparison_id}/export.csv")
            assert response.status_code == 200
            assert "text/csv" in response.headers["content-type"]
            assert "attachment" in response.headers["content-disposition"]
            assert response.headers["cache-control"] == "no-store"
            rows = list(csv.DictReader(StringIO(response.content.decode("utf-8-sig"))))
            assert [row["sample_name"] for row in rows] == ["LCE2", "VUGT"]
            assert [row["run_id"] for row in rows] == run_ids
            assert all(row["is_current"] == "True" for row in rows)
            missing = client.get("/api/comparisons/missing/export.csv")
            assert missing.status_code == 404
    finally:
        app.dependency_overrides.clear()
