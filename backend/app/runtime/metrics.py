from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class ExecutionMetricsStore:
    def __init__(self, root: str | Path | None = None) -> None:
        self.root = Path(root or "/tmp/synzept-execution-metrics")
        self.root.mkdir(parents=True, exist_ok=True)

    def append(self, payload: dict[str, Any]) -> dict[str, Any]:
        record = {
            **payload,
            "recorded_at": payload.get("recorded_at") or datetime.now(timezone.utc).isoformat(),
        }
        path = self.root / f"{record['execution_id']}.json"
        path.write_text(json.dumps(record, indent=2, sort_keys=True), encoding="utf-8")
        return record

    def list(self) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        if not self.root.exists():
            return records
        for path in sorted(self.root.glob("*.json")):
            try:
                records.append(json.loads(path.read_text(encoding="utf-8")))
            except Exception:
                continue
        return records
