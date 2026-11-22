"""HTTP integration tests for the sample-centric v2 workspace.

No external network or paid CI is required; TestClient runs locally.
"""
import json

import pytest
from fastapi.testclient import TestClient

from vitrifit2.api import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("VITRIFIT2_DATA_DIR", str(tmp_path / "vitrifit"))
    return TestClient(app)


def test_profile_rheology_import_reanalysis_and_manifest(client):
    project = client.post("/api/projects", json={"name": "LCE"}).json()["id"]
    sample = client.post(f"/api/projects/{project}/samples",
                         json={"name": "VUGT"}).json()["id"]
    specimen_response = client.post(
        f"/api/v2/samples/{sample}/specimens",
        json={"label": "disc-1", "metadata": {"thickness_mm": 1}})
    assert specimen_response.status_code == 201, specimen_response.text
    specimen = specimen_response.json()["id"]
    conditions = {"temperature_c": 40, "frequency_hz": 1,
                  "geometry_id": "plate-8mm", "material_state_id": "annealed"}
    measurement_response = client.post(
        f"/api/v2/specimens/{specimen}/measurements",
        json={"technique": "Rheology", "method": "amplitude_sweep",
              "conditions": conditions})
    assert measurement_response.status_code == 201, measurement_response.text
    mid = measurement_response.json()["id"]
    raw = b"strain,Gp\n.01,1000\n.02,1000\n.03,1000\n.04,1000\n.05,1000\n.1,990\n.2,900\n"
    response = client.post(
        f"/api/v2/measurements/{mid}/rheology/import",
        files={"file": ("lvr.csv", raw, "text/csv")},
        data={"method": "amplitude_sweep",
              "columns_json": json.dumps({
                  "strain_percent": "strain", "storage_modulus": "Gp"})})
    assert response.status_code == 201, response.text
    original = response.json()
    assert original["results"]["status"] == "departure_detected"
    profile = client.get(f"/api/v2/samples/{sample}/profile").json()
    assert len(profile["techniques"]["Rheology"]) == 1
    assert profile["techniques"]["DSC"] == []
    assert len(profile["techniques"]["Rheology"][0]["files"]) == 1
    new_response = client.post(
        f"/api/v2/rheology/analyses/{original['analysis_id']}/reanalyze",
        json={"departure_fraction": .15})
    assert new_response.status_code == 201, new_response.text
    assert new_response.json()["results"]["status"] == "no_departure_in_measured_range"
    history = client.get(
        f"/api/v2/measurements/{mid}/rheology/analyses").json()
    assert len(history) == 2
    assert history[0]["file_id"] == history[1]["file_id"]
    manifest = client.post(
        "/api/v2/rheology/manifest",
        json={"analysis_ids": [original["analysis_id"]]})
    assert manifest.status_code == 200, manifest.text
    assert manifest.json()["analyses"][0]["sample_id"] == sample
    downloaded = client.get(f"/api/v2/files/{original['file_id']}/raw")
    assert downloaded.content == raw


def test_invalid_csv_does_not_create_raw_attachment(client):
    project = client.post("/api/projects", json={"name": "P"}).json()["id"]
    sample = client.post(f"/api/projects/{project}/samples",
                         json={"name": "S"}).json()["id"]
    specimen = client.post(f"/api/v2/samples/{sample}/specimens",
                           json={"label": "disc"}).json()["id"]
    mid = client.post(f"/api/v2/specimens/{specimen}/measurements",
                      json={"technique": "Rheology", "method": "frequency_sweep"}).json()["id"]
    response = client.post(
        f"/api/v2/measurements/{mid}/rheology/import",
        files={"file": ("bad.csv", b"f,Gp,Gp\n1,1000,200\n", "text/csv")},
        data={"method": "frequency_sweep",
              "columns_json": json.dumps({
                  "frequency": "f", "storage_modulus": "Gp",
                  "loss_modulus": "Gpp"})})
    assert response.status_code == 422
    assert client.get(f"/api/v2/measurements/{mid}/files").json() == []


def test_missing_sample_returns_404(client):
    assert client.get("/api/v2/samples/not-found/profile").status_code == 404
