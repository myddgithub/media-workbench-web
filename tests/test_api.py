from fastapi.testclient import TestClient

from app.main import app, settings, store


client = TestClient(app)


def test_index_and_config_are_available():
    assert client.get("/").status_code == 200
    response = client.get("/api/config")
    assert response.status_code == 200
    assert response.json()["roots"][0]["label"] == "Test"


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
