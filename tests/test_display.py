import asyncio

from src.core.display import DisplayManager


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
