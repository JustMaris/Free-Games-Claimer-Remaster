from __future__ import annotations

import json
import os
from datetime import datetime

from src.core.config import cfg
from src.core.run_state import waiting_for_you


def write_status_json(*, selected_stores: list[str], run_state: str | None = None,
                      started_at: datetime | None = None, finished_at: datetime | None = None,
                      last_summary: dict | None = None) -> None:
    """Write data/status.json atomically. run_state defaults to idle, or waiting_for_you after skips."""
    waiting = waiting_for_you()
    payload = {
        "vnc_mode": cfg.vnc_mode,
        "last_run_started_at": started_at and started_at.isoformat(),
        "last_run_finished_at": finished_at and finished_at.isoformat(),
        "selected_stores": selected_stores,
        "run_state": run_state or ("waiting_for_you" if waiting else "idle"),
        "last_summary": last_summary or {},
        "waiting_for_you": waiting,
    }
    cfg._data_dir.mkdir(parents=True, exist_ok=True)
    out_path = cfg._data_dir / "status.json"
    tmp = out_path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    os.replace(tmp, out_path)
