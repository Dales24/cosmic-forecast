"""In-memory API health metrics for the admin monitor.

A single process-wide collector records every request (via middleware in
``api.py``) so admins can see uptime, request volume, status breakdown, error
rate, and the most recent server errors — no external dependencies. A second
collector records the last scene build's per-kind object caps, so admins can see
how much of each catalog the caps are holding back.
"""

from __future__ import annotations

import threading
import time
from collections import Counter, deque
from datetime import datetime, timezone

_MAX_RECENT_ERRORS = 25


class Metrics:
    """Thread-safe counters for request health."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.started_at = time.time()
        self.total = 0
        self.status_classes: Counter = Counter()
        self.by_path: Counter = Counter()
        self.recent_errors: deque = deque(maxlen=_MAX_RECENT_ERRORS)

    def record(self, method: str, path: str, status: int, duration_ms: float) -> None:
        with self._lock:
            self.total += 1
            self.status_classes[f"{status // 100}xx"] += 1
            self.by_path[path] += 1
            if status >= 500:
                self.recent_errors.append(
                    {
                        "method": method,
                        "path": path,
                        "status": status,
                        "duration_ms": round(duration_ms, 1),
                        "at": datetime.now(timezone.utc).isoformat(),
                    }
                )

    def snapshot(self) -> dict:
        with self._lock:
            uptime = time.time() - self.started_at
            total = self.total
            status_classes = dict(self.status_classes)
            top_paths = self.by_path.most_common(8)
            errors = list(self.recent_errors)
        error_count = status_classes.get("5xx", 0)
        return {
            "started_at": datetime.fromtimestamp(
                self.started_at, timezone.utc
            ).isoformat(),
            "uptime_seconds": round(uptime, 1),
            "total_requests": total,
            "status_classes": status_classes,
            "error_count": error_count,
            "error_rate": round(error_count / total, 4) if total else 0.0,
            "top_paths": [{"path": p, "count": c} for p, c in top_paths],
            "recent_errors": list(reversed(errors)),
        }

    def reset(self) -> None:
        with self._lock:
            self.started_at = time.time()
            self.total = 0
            self.status_classes.clear()
            self.by_path.clear()
            self.recent_errors.clear()


class SceneCapReport:
    """Thread-safe record of the last scene build's per-kind cap outcome.

    Only the latest build is kept: the caps are a property of the scene, not a
    running total, so "what did the last scene leave out?" is the useful answer.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._rows: list[dict] = []
        self._at: str | None = None

    def record(self, rows: list[dict]) -> None:
        """Replace the report with one row per capped kind (see api._scene_sources)."""
        with self._lock:
            self._rows = sorted(rows, key=lambda row: -row["hidden"])
            self._at = datetime.now(timezone.utc).isoformat()

    def snapshot(self) -> dict:
        with self._lock:
            rows = [dict(row) for row in self._rows]
            at = self._at
        return {
            "at": at,
            "total_shown": sum(row["shown"] for row in rows),
            "total_hidden": sum(row["hidden"] for row in rows),
            # False when any row's hidden count is a "there are more" floor
            # rather than a true count (see api._simbad_scene_objects).
            "total_hidden_exact": all(row["hidden_exact"] for row in rows),
            "kinds": rows,
        }

    def reset(self) -> None:
        with self._lock:
            self._rows = []
            self._at = None


class SourceFailureLog:
    """Thread-safe record of recent external-catalog fetch failures.

    Scene assembly swallows source errors so one outage can't take the map
    down; without this an admin can't tell "CelesTrak is rate-limiting us" from
    "that patch of sky is empty". Keeps the latest failure per (source, kind)
    plus a running count, which is what a repeated outage looks like.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._failures: dict[tuple[str, str], dict] = {}

    def record(self, source: str, kind: str, error: str) -> None:
        with self._lock:
            entry = self._failures.get((source, kind))
            if entry is None:
                entry = {"source": source, "kind": kind, "count": 0}
                self._failures[(source, kind)] = entry
            entry["count"] += 1
            entry["error"] = error
            entry["at"] = datetime.now(timezone.utc).isoformat()

    def snapshot(self) -> dict:
        with self._lock:
            rows = [dict(entry) for entry in self._failures.values()]
        rows.sort(key=lambda row: row["at"], reverse=True)
        return {
            "total": sum(row["count"] for row in rows),
            "sources": rows,
        }

    def reset(self) -> None:
        with self._lock:
            self._failures.clear()


metrics = Metrics()
scene_cap_report = SceneCapReport()
source_failures = SourceFailureLog()
