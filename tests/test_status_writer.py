import json

import pytest

from src.core.status import write_status_json, RunTiming


def test_status_writer_writes_json(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True)

    import src.core.config as config
    monkeypatch.setattr(config.cfg, "_data_dir", data_dir, raising=False)
    monkeypatch.setattr("src.core.status.cfg", config.cfg, raising=False)

    write_status_json(
        vnc_mode="off",
        selected_stores=["steam"],
        run_state="waiting_for_you",
        run_timing=RunTiming(last_run_started_at=None, last_run_finished_at=None),
        last_summary={"claimed": 1, "failed": 2, "skipped": 3},
    )

    payload = json.loads((data_dir / "status.json").read_text("utf-8"))

    assert payload["vnc_mode"] == "off"
    assert payload["selected_stores"] == ["steam"]
    assert payload["run_state"] == "waiting_for_you"
    assert payload["last_summary"]["claimed"] == 1
