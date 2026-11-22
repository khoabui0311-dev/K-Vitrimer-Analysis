"""HTTP-level DMA/DSC sample-profile regression coverage."""
import json

from fastapi.testclient import TestClient

from vitrifit2.api import app


def test_thermal_api_import_history_and_raw_file(tmp_path, monkeypatch):
    monkeypatch.setenv("VITRIFIT2_DATA_DIR", str(tmp_path / "workspace"))
    client = TestClient(app)
    project = client.post("/api/projects", json={"name": "P"}).json()["id"]
    sample = client.post(f"/api/projects/{project}/samples",
                         json={"name": "VUGT"}).json()["id"]
    specimen = client.post(f"/api/v2/samples/{sample}/specimens",
                           json={"label": "film"}).json()["id"]
    for technique, method, columns, raw in (
        ("DMA", "temperature_ramp",
         {"temperature_c": "T", "storage_modulus": "Ep",
          "loss_modulus": "Epp"},
         b"T,Ep,Epp\n20,1000,100\n30,900,180\n40,700,350\n50,500,100\n60,400,40\n"),
        ("DSC", "calorimetry",
         {"temperature_c": "T", "heat_flow": "heat"},
         b"T,heat\n20,1\n30,1.1\n40,1.8\n50,2.1\n60,2.2\n"),
    ):
        mid = client.post(f"/api/v2/specimens/{specimen}/measurements",
                          json={"technique": technique, "method": method}).json()["id"]
        response = client.post(
            f"/api/v2/measurements/{mid}/thermal/import",
            files={"file": (f"{technique}.csv", raw, "text/csv")},
            data={"method": method, "columns_json": json.dumps(columns),
                  "modulus_unit": "MPa", "heat_flow_unit": "mW",
                  "heating_rate_c_min": "5"})
        assert response.status_code == 201, response.text
        analysis = response.json()
        assert analysis["method"] == method
        assert client.get(f"/api/v2/files/{analysis['file_id']}/raw").content == raw
        history = client.get(f"/api/v2/measurements/{mid}/thermal/analyses")
        assert history.status_code == 200
        assert len(history.json()) == 1
        if technique == "DSC":
            assert analysis["results"]["t_g_onset_c"] is None
        else:
            assert analysis["results"]["tan_delta_peak_temperature_c"] == 40
    profile = client.get(f"/api/v2/samples/{sample}/profile").json()
    assert len(profile["techniques"]["DMA"]) == 1
    assert len(profile["techniques"]["DSC"]) == 1
