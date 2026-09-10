"""UTC stage, elapsed-time, and periodic heartbeat logging."""

import json
import threading
import time
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any


class Progress:
    def __init__(self, heartbeat_seconds: float = 15) -> None:
        if heartbeat_seconds <= 0:
            raise ValueError("heartbeat_seconds must be positive")
        self.started = time.monotonic()
        self.heartbeat_seconds = heartbeat_seconds

    def log(self, event: str, stage: str, start: float, **details: Any) -> None:
        now = time.monotonic()
        print(
            json.dumps(
                {
                    "utc": datetime.now(UTC).isoformat(timespec="seconds"),
                    "event": event,
                    "stage": stage,
                    "stage_elapsed_seconds": round(now - start, 3),
                    "total_elapsed_seconds": round(now - self.started, 3),
                    **details,
                }
            ),
            flush=True,
        )

    @contextmanager
    def stage(self, name: str):
        start = time.monotonic()
        stop = threading.Event()

        def heartbeat() -> None:
            while not stop.wait(self.heartbeat_seconds):
                self.log("heartbeat", name, start)

        thread = threading.Thread(target=heartbeat, daemon=True)
        self.log("started", name, start)
        thread.start()
        try:
            yield
        except BaseException:
            self.log("failed", name, start)
            raise
        else:
            self.log("completed", name, start)
        finally:
            stop.set()
            thread.join()
