"""HTTP-level read-only backup verification regressions."""
import io
import zipfile

from fastapi.testclient import TestClient

from vitrifit2.api import app
from vitrifit2.persistence import VitriFitStore


def test_backup_verification_endpoint_does_not_change_workspace(tmp_path, monkeypatch):
    root = tmp_path / "workspace"
    monkeypatch.setenv("VITRIFIT2_DATA_DIR", str(root))
    store = VitriFitStore(root)
    project = store.create_project("LCE")
    sample = store.create_sample(project, "LCE2")
    backup = store.export_backup_bytes()
    client = TestClient(app)
    before = (root / "vitrifit.sqlite3").read_bytes()
    response = client.post(
        "/api/v2/backup/verify",
        files={"file": ("backup.zip", backup, "application/zip")})
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "verified"
    assert (root / "vitrifit.sqlite3").read_bytes() == before
    assert store.list_samples(project)[0]["id"] == sample


def test_backup_verification_rejects_invalid_upload(tmp_path, monkeypatch):
    monkeypatch.setenv("VITRIFIT2_DATA_DIR", str(tmp_path))
    client = TestClient(app)
    response = client.post(
        "/api/v2/backup/verify",
        files={"file": ("notzip.zip", b"invalid", "application/zip")})
    assert response.status_code == 422
    assert "detail" in response.json()


def test_backup_verification_rejects_compression_bomb_metadata(tmp_path, monkeypatch):
    monkeypatch.setenv("VITRIFIT2_DATA_DIR", str(tmp_path))
    client = TestClient(app)
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", b"{}")
        archive.writestr("vitrifit.sqlite3", b"0" * (2 * 1024 * 1024))
    response = client.post(
        "/api/v2/backup/verify",
        files={"file": ("zipbomb.zip", payload.getvalue(), "application/zip")})
    assert response.status_code == 422
    assert "compression" in response.json()["detail"].lower()
