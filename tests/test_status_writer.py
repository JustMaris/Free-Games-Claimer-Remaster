import json

import pytest

from src.core.status import write_status_json


def test_status_writer_writes_json(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True)

    import src.core.config as config
    monkeypatch.setattr(config.cfg, "_data_dir", data_dir, raising=False)
    monkeypatch.setattr("src.core.status.cfg", config.cfg, raising=False)

    monkeypatch.setattr(config.cfg, "vnc_mode", "off", raising=False)
    write_status_json(
        selected_stores=["steam"],
        run_state="waiting_for_you",
        last_summary={"claimed": 1, "failed": 2, "skipped": 3},
    )

    payload = json.loads((data_dir / "status.json").read_text("utf-8"))

    assert payload["vnc_mode"] == "off"
    assert payload["selected_stores"] == ["steam"]
    assert payload["run_state"] == "waiting_for_you"
    assert payload["last_summary"]["claimed"] == 1
