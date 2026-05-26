"""Database backup command helpers.

These helpers intentionally return shell-safe argument lists instead of running
shell strings. Operators can schedule them from Railway, cron, or CI.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path


def backup_filename(prefix: str = "synzept") -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{prefix}-{stamp}.dump"


def pg_dump_args(database_url: str, output_dir: str = "backups") -> list[str]:
    target = Path(output_dir) / backup_filename()
    return ["pg_dump", database_url, "--format=custom", "--no-owner", f"--file={target}"]


def pg_restore_args(database_url: str, dump_file: str) -> list[str]:
    return ["pg_restore", "--clean", "--if-exists", "--no-owner", f"--dbname={database_url}", dump_file]
