from app.store import JobStore


def test_job_lifecycle(tmp_path):
    store = JobStore(tmp_path / "jobs.sqlite3")
    job = store.create("convert", {"input_path": "in"})
    assert job["status"] == "queued"

    claimed = store.claim_next()
    assert claimed["id"] == job["id"]
    assert claimed["status"] == "running"

    store.progress(job["id"], 0.4, "processing")
    store.append_log(job["id"], "hello")
    store.complete(job["id"], {"summary": "done", "files": []})
    finished = store.get(job["id"])
    assert finished["status"] == "succeeded"
    assert finished["progress"] == 1
    assert "hello" in finished["logs"]
    assert finished["result"]["summary"] == "done"
    assert store.delete(job["id"])


def test_cancel_queued_job_is_immediate(tmp_path):
    store = JobStore(tmp_path / "jobs.sqlite3")
    job = store.create("cut", {})
    cancelled = store.request_cancel(job["id"])
    assert cancelled["status"] == "cancelled"
    assert store.claim_next() is None


def test_worker_heartbeat(tmp_path):
    store = JobStore(tmp_path / "jobs.sqlite3")
    assert store.worker_state() is None
    store.touch_worker()
    assert store.worker_state()["value"] == "alive"
