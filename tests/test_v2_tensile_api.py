"""HTTP regression for tensile sample-profile integration."""
import json
import pytest

from fastapi.testclient import TestClient

from vitrifit2.api import app


def test_tensile_http_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("VITRIFIT2_DATA_DIR", str(tmp_path / "data"))
    client = TestClient(app)
    project = client.post("/api/projects", json={"name": "P"}).json()["id"]
    sample = client.post(f"/api/projects/{project}/samples",
                         json={"name": "LCE2"}).json()["id"]
    specimen = client.post(f"/api/v2/samples/{sample}/specimens",
                           json={"label": "film"}).json()["id"]
    mid = client.post(f"/api/v2/specimens/{specimen}/measurements",
                      json={"technique": "Tensile", "method": "tensile_test"}).json()["id"]
    raw = b"extension,load\n0,0\n.01,1\n.02,2\n.03,3\n.04,4\n.05,5\n"
    response = client.post(
        f"/api/v2/measurements/{mid}/tensile/import",
        files={"file": ("tensile.csv", raw, "text/csv")},
        data={"columns_json": json.dumps({
            "displacement_mm": "extension", "force_n": "load"}),
              "gauge_length_mm": "10", "width_mm": "2", "thickness_mm": "1"})
    assert response.status_code == 201, response.text
    result = response.json()
    assert result["results"]["youngs_modulus_mpa"] == pytest.approx(500)
    history = client.get(f"/api/v2/measurements/{mid}/tensile/analyses")
    assert history.status_code == 200
    assert history.json()[0]["analysis_id"] == result["analysis_id"]
    profile = client.get(f"/api/v2/samples/{sample}/profile").json()
    assert profile["techniques"]["Tensile"][0]["files"][0]["sha256"]
    assert client.get(f"/api/v2/files/{result['file_id']}/raw").content == raw
