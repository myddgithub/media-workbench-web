from __future__ import annotations

import sys
from datetime import datetime, timezone

from .config import get_settings
from .store import JobStore


def main() -> None:
    target = sys.argv[1] if len(sys.argv) > 1 else "worker"
    if target != "worker":
        raise SystemExit(f"unknown healthcheck: {target}")
    settings = get_settings()
    state = JobStore(settings.database_path).worker_state()
    if not state:
        raise SystemExit("worker heartbeat missing")
    age = (datetime.now(timezone.utc) - datetime.fromisoformat(state["updated_at"])).total_seconds()
    if age >= 45:
        raise SystemExit(f"worker heartbeat stale: {age:.1f}s")
    print(f"worker ok ({age:.1f}s)")


if __name__ == "__main__":
    main()
