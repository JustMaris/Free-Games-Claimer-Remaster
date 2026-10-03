# Open investigations

These are open questions about the fork (Playwright engine, on-demand Xvfb/VNC, status page) that the tests can't answer. Each one needs a live run or a decision. Delete an entry once it's settled, and add the outcome to the CHANGELOG.

## 1. Browser engine: does Playwright/Patchright draw more challenges than nodriver?

**Why:** upstream picked nodriver to avoid CDP fingerprinting (MODIFICATIONS.md §1). Stock Playwright leaks `Runtime.enable` and its binding/utility world, and Cloudflare, hCaptcha and Arkose look for both. The fork now runs on **patchright**, a drop-in Playwright build that patches those leaks. Nobody has measured whether that is enough.

**How to check:** run this fork's image next to an upstream `v1.9` container for about a week. Use separate data volumes, the same accounts, and the same `STORES`. Both log the same warning from `BaseClaimer._wait_out_challenge`, so count it per container:

```bash
docker logs fgc-fork 2>&1 | grep -oE "[^ ]+( [^ ]+)? is behind a Cloudflare" | sort | uniq -c
```

| Store | upstream v1.9 (nodriver) | fork (patchright) |
|---|---|---|
| epic | | |
| fab | | |
| steam (SteamDB) | | |
| prime | | |
| gog | | |

The log only counts challenges that didn't clear within the settle window. If that's too coarse, add a counter to `status.json`.

**Evidence so far (homelab, one Epic account):**
- Sep 29, upstream `p-adamiec:latest` (nodriver): 4 of 4 Epic claims went through unattended, about 75 s each.
- Oct 1 to Oct 3, this fork on Playwright and then patchright: 0 unattended Epic claims. Every checkout hit an hCaptcha inside the cross-origin checkout iframe (screenshot `epic_checkout_*.png`, frame buttons `Add to library`, `TRY AGAIN`). Patchright made no difference.
- Oct 3: with the iframe captcha detected and handed to VNC, BURIED STARS was claimed after a manual solve.
- Still to do: one upstream v1.9 run on the same account against the same pending games, to rule out Epic's risk scoring changing between those dates.

**Decision it feeds:** keep patchright, go back to nodriver (better upstream fit), or try patchright with real Chrome (`channel="chrome"`, x86-64 only).

## 2. Debian `chromium` driven by the pip Playwright driver

**Why:** Playwright supports only the Chromium revision it ships. The image installs Debian's `chromium`, whose version moves with apt. Skew can break protocol calls without any warning.

**How to check:** in the container, compare `chromium --version` with `python -c "import patchright, json, pathlib; print(json.loads((pathlib.Path(patchright.__file__).parent/'driver/package/browsers.json').read_text()))"`. Either pin a known-good pair in the Dockerfile or document how far apart they can drift.

As of October 2026: Debian ships Chromium 154.0.8037.92 and patchright 1.63.0 expects 153.0.8010.12. Launch, navigation and evaluate all work at that one-major skew.

## 3. Removing `--restore-last-session` and GOG sessions

**Why:** upstream used this flag to keep GOG's `gog-al` session cookie across Docker restarts (MODIFICATIONS.md, `gog.py`). The fork dropped it in the Playwright move. A persistent context keeps cookies that have an expiry, but drops session-only cookies when it closes.

**How to check:** restart the container between runs for a few days and watch for GOG asking to log in again.

## 4. Manual steps when `SHOW=0`

**Why:** every store except Epic runs headless when `SHOW=0`. When one needs a human, the VNC lease starts Xvfb and noVNC, but the headless browser isn't on that display, so the user sees an empty screen.

**How to check:** set `SHOW=0` and force a login on a non-Epic store. Then decide whether to relaunch that store headful for the manual step, or skip it with a clear log line.

Related: headless mode reports `HeadlessChrome/154` in `navigator.userAgent`, which anti-bot scripts check for. That alone may be a reason to keep `SHOW=1` (the default), now that Xvfb only runs while a browser is open.

## 5. The V8 heap cap (`--js-flags=--max-old-space-size=512`)

**Why:** until now the flag was passed as two separate args, so Chromium ignored it. It's applied correctly now, and 512 MB could crash heavy pages: Epic store, Fab listing, AliExpress.

**How to check:** look for "Aw, Snap!" or `Target crashed` in the logs and screenshots for a week. Raise or remove the cap if it happens.

## 6. `BROWSER_CACHE_DIR` and memory

**Why:** `.env.example` says it moves the cache "to disk (lower RAM)". Chromium's default disk cache is already on disk, inside the profile dir on the data volume. The flag only moves where it lives.

**How to check:** compare RSS with and without the setting. If there's no difference, correct the doc or drop the setting.

## 7. Memory baseline

**Why:** the memory commits (lazy imports, `__slots__`, which have since been removed) came with no before/after numbers. `docs/memory-profiling.md` assumes kubectl and `pympler` (not installed), and calls `engine.pool.size()` on what may be an async engine.

**How to check:** record container RSS when idle and at peak for one full run on the current image, and again after each memory change. Trim `memory-profiling.md` to the commands that actually work.

## 8. `PageAdapter.find` CSS-vs-text heuristic

**Why:** `src/core/browser.py` guesses whether a string is a CSS selector by its prefix (`a`, `button`, `div`, `label`, ...). A text search such as `"accept all"` or `"label printer"` gets routed to `wait_for_selector`. An invalid selector raises `Error`, not `TimeoutError`, and that escapes the `except`.

**How to check:** grep the `find(` call sites in `src/stores/` for text arguments that start with those prefixes. Consider an explicit `text=` prefix.

## 9. Drop the nodriver-shaped adapter (long term)

**Why:** `browser.py` keeps nodriver's API (`send_keys("\r")`, `apply`, `evaluate` with an "Illegal return statement" retry) so the store code didn't have to change. If the engine decision (item 1) lands on Playwright/patchright, calling `Page`/`Locator` directly removes a layer, and the guessing from item 8 goes with it.

## 10. Exposure of the status server and VNC

**Why:** the status server binds `0.0.0.0:7080` without auth, and x11vnc runs with `-nopw` when `VNC_PASSWORD` is unset. That's fine on a LAN, but needs documenting for anyone who puts the port behind a reverse proxy.

## 11. Python 3.14 compatibility

**Why:** the image runs Python 3.14. CI now runs tests on 3.14, but the local `.venv` is 3.12, and greenlet/patchright/aiosqlite on 3.14 haven't been exercised end to end.

**How to check:** run one full `--once` run in the image on every dependency bump.

## 12. Stale docs

- MODIFICATIONS.md still describes nodriver (5 mentions), TurboVNC/VirtualGL, `google-chrome-stable` on x86 and `bookworm-slim`.
- The README project tree says `Debian bookworm-slim`. The base image is now `python:3.14-slim` (trixie).

## 13. Fork identity and upstream

**Why:** `docker-compose.yml` still pulls `ghcr.io/p-adamiec/free-games-claimer-remaster`, and `docker-publish.yml` pushes to Docker Hub using `DOCKERHUB_*` secrets the fork may not have.

**Decision:** either publish the fork's own image and point compose at it, or upstream the pieces that don't depend on the browser engine as small PRs: native arm64 CI, the pytest CI step, Dockerfile/`.dockerignore` slimming, the healthcheck fix. The engine change should wait for the data from item 1.
