from __future__ import annotations

import asyncio
import os
import subprocess

from src.core.config import cfg


class DisplayManager:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._leases = 0
        self._process: subprocess.Popen | None = None

    async def acquire(self) -> None:
        async with self._lock:
            self._leases += 1
            if self._process and self._process.poll() is None:
                return
            try:
                await asyncio.to_thread(self._remove_stale_files)
                display = os.getenv("DISPLAY", ":1")
                depth = os.getenv("DEPTH", "24")
                self._process = subprocess.Popen([
                    "Xvfb", display, "-screen", "0",
                    f"{cfg.width}x{cfg.height}x{depth}", "-nolisten", "tcp", "-ac",
                ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                await self._wait_until_ready(display)
            except Exception:
                self._leases -= 1
                await asyncio.to_thread(self._stop_process)
                raise

    async def release(self) -> None:
        async with self._lock:
            self._leases = max(0, self._leases - 1)
            if self._leases == 0:
                await asyncio.to_thread(self._stop_process)

    async def close(self) -> None:
        async with self._lock:
            self._leases = 0
            await asyncio.to_thread(self._stop_process)

    async def _wait_until_ready(self, display: str) -> None:
        display_number = int(display.rsplit(":", 1)[-1].split(".", 1)[0])
        socket_path = f"/tmp/.X11-unix/X{display_number}"
        for _ in range(100):
            if os.path.exists(socket_path):
                return
            if self._process and self._process.poll() is not None:
                break
            await asyncio.sleep(0.05)
        raise RuntimeError(f"Xvfb failed to start on {display}")

    @staticmethod
    def _remove_stale_files() -> None:
        display = os.getenv("DISPLAY", ":1")
        number = display.rsplit(":", 1)[-1].split(".", 1)[0]
        for path in (f"/tmp/.X{number}-lock", f"/tmp/.tX{number}-lock", f"/tmp/.X11-unix/X{number}"):
            try:
                os.unlink(path)
            except FileNotFoundError:
                pass

    def _stop_process(self) -> None:
        if self._process and self._process.poll() is None:
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
                self._process.wait(timeout=5)
        self._process = None


display_manager = DisplayManager()


def screen_state() -> str:
    """One readable summary of the screen, for the log."""
    number = os.getenv("DISPLAY", ":1").rsplit(":", 1)[-1].split(".", 1)[0]
    proc = display_manager._process
    return (f":{number} socket={os.path.exists(f'/tmp/.X11-unix/X{number}')} "
            f"Xvfb={bool(proc and proc.poll() is None)} leases={display_manager._leases}")


def running_as() -> str:
    """The user this process runs as, which on a NAS is often not root."""
    try:
        import pwd
        return f"{pwd.getpwuid(os.getuid()).pw_name}({os.getuid()})"
    except Exception:
        return "unknown"


def free_memory() -> str:
    """Memory the kernel says is still available, the usual reason Chrome dies at once."""
    try:
        with open("/proc/meminfo", encoding="utf-8") as f:
            for line in f:
                if line.startswith("MemAvailable:"):
                    return f"{int(line.split()[1]) / 1_000_000:.1f} GB available"
    except Exception:
        pass
    return "unknown"
