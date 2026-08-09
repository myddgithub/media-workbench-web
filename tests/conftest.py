import os
import shutil
import tempfile
from pathlib import Path

import pytest


TEST_BASE = Path(tempfile.mkdtemp(prefix="media-workbench-tests-"))
TEST_MEDIA = TEST_BASE / "media"
TEST_STATE = TEST_BASE / "state"
TEST_MEDIA.mkdir(parents=True)
TEST_STATE.mkdir(parents=True)

os.environ["MEDIA_ROOTS"] = f"Test={TEST_MEDIA}"
os.environ["STATE_DIR"] = str(TEST_STATE)
os.environ["DATABASE_PATH"] = str(TEST_STATE / "jobs.sqlite3")


@pytest.fixture(scope="session", autouse=True)
def cleanup_test_base():
    yield
    shutil.rmtree(TEST_BASE, ignore_errors=True)


@pytest.fixture
def media_root(tmp_path):
    path = tmp_path / "media"
    path.mkdir()
    return path
