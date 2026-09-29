from __future__ import annotations

import asyncio
import os
import socket
import subprocess
from contextlib import asynccontextmanager

from src.core.config import cfg


class VNCManager:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._leases = 0
        self._idle_task: asyncio.Task | None = None
        self._x11vnc: subprocess.Popen | None = None
        self._websockify: subprocess.Popen | None = None

    @property
    def available(self) -> bool:
        return cfg.vnc_mode != "off"

    async def start(self) -> None:
        if not self.available:
            return
        async with self._lock:
            if self._running():
                return
            await asyncio.to_thread(self._stop_processes)
            auth = ["-rfbauth", "/tmp/x11vnc.pass"] if os.path.exists("/tmp/x11vnc.pass") else ["-nopw"]
            self._x11vnc = subprocess.Popen([
                "x11vnc", "-display", os.getenv("DISPLAY", ":1"), "-forever", "-shared",
                "-rfbport", os.getenv("VNC_PORT", "5900"), "-o", "/fgc/data/x11vnc.log", *auth,
            ])
            await self._wait_for_port(int(os.getenv("VNC_PORT", "5900")))
            self._websockify = subprocess.Popen([
                "websockify", "--web", "/usr/share/novnc/", cfg.novnc_port,
                f"localhost:{os.getenv('VNC_PORT', '5900')}",
            ])
            await self._wait_for_port(int(cfg.novnc_port))

    async def stop(self) -> None:
        async with self._lock:
            await asyncio.to_thread(self._stop_processes)

    async def initialize(self) -> None:
        if cfg.vnc_mode == "on":
            await self.start()

    @asynccontextmanager
    async def lease(self):
        if not self.available:
            yield False
            return
        self._leases += 1
        if self._idle_task:
            self._idle_task.cancel()
            self._idle_task = None
        try:
            await self.start()
            yield True
        finally:
            self._leases -= 1
            if cfg.vnc_mode == "auto" and self._leases == 0:
                self._idle_task = asyncio.create_task(self._stop_after_idle())

    async def close(self) -> None:
        if self._idle_task:
            self._idle_task.cancel()
            self._idle_task = None
        await self.stop()

    def _running(self) -> bool:
        return bool(
            self._x11vnc and self._x11vnc.poll() is None
            and self._websockify and self._websockify.poll() is None
        )

    async def _stop_after_idle(self) -> None:
        try:
            await asyncio.sleep(cfg.vnc_idle_timeout)
            if self._leases == 0:
                await self.stop()
        except asyncio.CancelledError:
            pass

    async def _wait_for_port(self, port: int) -> None:
        for _ in range(100):
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=0.1):
                    return
            except OSError:
                await asyncio.sleep(0.05)
        await asyncio.to_thread(self._stop_processes)
        raise RuntimeError(f"VNC service did not open port {port}")

    def _stop_processes(self) -> None:
        for process in (self._websockify, self._x11vnc):
            if process and process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
        self._websockify = None
        self._x11vnc = None


vnc_manager = VNCManager()
