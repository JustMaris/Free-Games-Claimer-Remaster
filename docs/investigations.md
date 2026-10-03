# Open investigations

These are open questions about the fork (on-demand Xvfb/VNC, status page, Python 3.14) that the tests can't answer. Each one needs a live run or a decision. Delete an entry once it's settled, and add the outcome to the CHANGELOG.

## 1. Manual steps when `SHOW=0`

**Why:** every store except Epic runs headless when `SHOW=0`. When one needs a human, the VNC lease starts Xvfb and noVNC, but the headless browser isn't on that display, so the user sees an empty screen.

**How to check:** set `SHOW=0` and force a login on a non-Epic store. Then decide whether to relaunch that store headful for the manual step, or skip it with a clear log line.

Related: headless mode reports `HeadlessChrome/154` in `navigator.userAgent`, which anti-bot scripts check for. That alone may be a reason to keep `SHOW=1` (the default), now that Xvfb only runs while a browser is open.

## 2. The V8 heap cap (`--js-flags=--max-old-space-size=512`)

**Why:** until now the flag was passed as two separate args, so Chromium ignored it. It's applied correctly now, and 512 MB could crash heavy pages: Epic store, Fab listing, AliExpress.

**How to check:** look for "Aw, Snap!" or `Target crashed` in the logs and screenshots for a week. Raise or remove the cap if it happens.

## 3. `BROWSER_CACHE_DIR` and memory

**Why:** `.env.example` says it moves the cache "to disk (lower RAM)". Chromium's default disk cache is already on disk, inside the profile dir on the data volume. The flag only moves where it lives.

**How to check:** compare RSS with and without the setting. If there's no difference, correct the doc or drop the setting.

## 4. Memory baseline

**Why:** the memory commits (lazy imports, `__slots__`, which have since been removed) came with no before/after numbers. `docs/memory-profiling.md` assumes kubectl and `pympler` (not installed), and calls `engine.pool.size()` on what may be an async engine.

**How to check:** record container RSS when idle and at peak for one full run on the current image, and again after each memory change. Trim `memory-profiling.md` to the commands that actually work.

## 5. Exposure of the status server and VNC

**Why:** the status server binds `0.0.0.0:7080` without auth, and x11vnc runs with `-nopw` when `VNC_PASSWORD` is unset. That's fine on a LAN, but needs documenting for anyone who puts the port behind a reverse proxy.

## 6. Python 3.14 compatibility

**Why:** the image runs Python 3.14, which upstream never did. nodriver 0.50.3 already needed a patch (a non-UTF-8 byte in `cdp/network.py`, fixed in the Dockerfile and CI), and nodriver and aiosqlite on 3.14 haven't been exercised end to end.

**How to check:** run one full `--once` run in the image on every dependency bump.

## 7. Stale docs

- MODIFICATIONS.md still describes TurboVNC/VirtualGL and `bookworm-slim`.
- The README project tree says `Debian bookworm-slim`. The base image is now `python:3.14-slim` (trixie).

## 8. Fork identity and upstream

**Why:** `docker-compose.yml` still pulls `ghcr.io/p-adamiec/free-games-claimer-remaster`, and `docker-publish.yml` pushes to Docker Hub using `DOCKERHUB_*` secrets the fork may not have.

**Decision:** either publish the fork's own image and point compose at it, or upstream the pieces that don't depend on the browser engine as small PRs: native arm64 CI, the pytest CI step, Dockerfile/`.dockerignore` slimming, the healthcheck fix. The fork is back on nodriver, so the remaining fork changes are engine-independent and could go upstream as they are.
