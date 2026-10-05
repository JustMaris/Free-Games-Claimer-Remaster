import asyncio

from pathlib import Path

from src.core.display import DisplayManager, screen_state


class FakeProcess:
    def __init__(self):
        self.returncode = None
        self.terminated = 0

    def poll(self):
        return self.returncode

    def terminate(self):
        self.terminated += 1
        self.returncode = 0

    def wait(self, timeout=None):
        return self.returncode


def test_display_is_shared_until_last_lease(monkeypatch):
    manager = DisplayManager()
    process = FakeProcess()

    monkeypatch.setattr("src.core.display.subprocess.Popen", lambda *args, **kwargs: process)
    monkeypatch.setattr(manager, "_wait_until_ready", lambda display: asyncio.sleep(0))
    monkeypatch.setattr(manager, "_remove_stale_files", lambda: None)

    async def scenario():
        await manager.acquire()
        await manager.acquire()
        await manager.release()
        assert process.terminated == 0
        await manager.release()

    asyncio.run(scenario())
    assert process.terminated == 1


ENTRYPOINT = (Path(__file__).resolve().parent.parent / "docker-entrypoint.sh").read_text(encoding="utf-8")
PUID_BLOCK = ENTRYPOINT.split('if [ -n "${PUID:-}" ]; then', 1)[1].split("\nfi\n", 1)[0]


def test_without_puid_nothing_changes():
    assert "run_as=()" in ENTRYPOINT
    assert 'exec "${run_as[@]}" tini -g -- "$@"' in ENTRYPOINT


def test_puid_switch_only_from_root_and_checks_capabilities_first():
    assert 'if [ "$run_uid" != "0" ]' in PUID_BLOCK
    assert PUID_BLOCK.index("can_switch_to") < PUID_BLOCK.index("useradd")
    assert '--reuid="$PUID" --regid="$PGID" --init-groups' in PUID_BLOCK


def test_puid_user_can_create_the_x_socket_and_read_the_vnc_password():
    assert "chmod 1777 /tmp/.X11-unix" in PUID_BLOCK
    assert 'chown "$run_uid" /tmp/x11vnc.pass' in ENTRYPOINT


def test_screen_state_names_xvfb():
    assert screen_state().startswith(":")
    assert "Xvfb=" in screen_state()
