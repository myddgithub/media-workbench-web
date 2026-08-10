from fastapi.testclient import TestClient

from app.main import app, settings, store


client = TestClient(app)


def test_index_and_config_are_available():
    index = client.get("/")
    assert index.status_code == 200
    assert 'href="/static/favicon.png"' in index.text
    favicon = client.get("/static/favicon.png")
    assert favicon.status_code == 200
    assert favicon.headers["content-type"] == "image/png"
    response = client.get("/api/config")
    assert response.status_code == 200
    body = response.json()
    assert body["roots"][0]["label"] == "Test"
    assert body.get("deployment") in ("nas", "local")
    i18n = client.get("/static/i18n.js")
    assert i18n.status_code == 200
    assert "appTitleLocal" in i18n.text
    assert "setDeployment" in i18n.text


def test_create_scan_and_cancel_conversion_job():
    root = next(iter(settings.roots.values())).path
    (root / "api-test.mp4").write_bytes(b"placeholder")
    scan = client.post("/api/scan", json={"root": "Test", "path": "", "mode": "video_to_audio"})
    assert scan.status_code == 200
    assert scan.json()["count"] >= 1

    payload = {
        "input_root": "Test", "input_path": "api-test.mp4",
        "output_root": "Test", "output_path": "converted",
        "mode": "video_to_audio", "workers": 1,
    }
    response = client.post("/api/jobs", json={"kind": "convert", "payload": payload})
    assert response.status_code == 201
    job_id = response.json()["id"]
    assert client.post(f"/api/jobs/{job_id}/cancel").json()["status"] == "cancelled"


def test_path_traversal_is_rejected():
    response = client.get("/api/browse", params={"root": "Test", "path": "../"})
    assert response.status_code == 400
