from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from src.core.config import cfg
from src.core.run_state import waiting_for_you


STATUS_RELATIVE_PATH = Path("status.json")


def _iso_utc(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


@dataclass
class RunTiming:
    last_run_started_at: datetime | None = None
    last_run_finished_at: datetime | None = None


def status_path() -> Path:
    return cfg._data_dir / STATUS_RELATIVE_PATH


def write_status_json(*, vnc_mode: str, selected_stores: list[str], run_state: str, run_timing: RunTiming, last_summary: dict | None = None) -> None:
    cfg._data_dir.mkdir(parents=True, exist_ok=True)

    payload = {
        "vnc_mode": vnc_mode,
        "last_run_started_at": _iso_utc(run_timing.last_run_started_at),
        "last_run_finished_at": _iso_utc(run_timing.last_run_finished_at),
        "selected_stores": selected_stores,
        "run_state": run_state,
        "last_summary": last_summary or {},
        "waiting_for_you": waiting_for_you(),
    }

    out_path = status_path()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = out_path.with_suffix(out_path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=False), encoding="utf-8")
    os.replace(tmp, out_path)
