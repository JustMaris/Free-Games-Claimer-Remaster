"""The NOTIFY_* switches do what .env.example says, in every store.

NOTIFY_SKIP_STORES=itchio used to pass the settings check and silence nothing, and a crashed store
still sent its alert with NOTIFY_ERRORS=false.
"""

import asyncio
from pathlib import Path

import main
import pytest

from src.core import claimer as claimer_module
from src.core import run_state
from src.stores import gamerpower as gp

ROOT = Path(__file__).resolve().parent.parent
MAIN_SOURCE = (ROOT / "main.py").read_text(encoding="utf-8")


class TestSkipStoresTakesEveryStoreName:
    @pytest.mark.parametrize("written,store", [
        ("ms", "microsoft"), ("xbox", "microsoft"), ("ubi", "ubisoft"),
        ("itch", "itchio"), ("awa", "alienware"), ("epic-games", "epic"),
    ])
    def test_an_alias_silences_its_store(self, monkeypatch, written, store):
        monkeypatch.setattr(main.cfg, "notify_skip_stores", {written})
        main._resolve_skip_stores()
        assert main.cfg.store_notify_enabled(store) is False

    def test_it_runs_before_the_settings_are_checked(self):
        body = MAIN_SOURCE.split("async def main()", 1)[1]
        assert body.index("_resolve_skip_stores()") < body.index("_warn_about_settings()")


class TestASiteIsSilencedByItsOwnName:
    """GamerPower's sites run inside one claimer called "gamerpower", but you name the site."""

    @pytest.fixture()
    def sent(self, monkeypatch):
        messages = []

        async def _capture(message, **_kwargs):
            messages.append(message)

        async def _no_wait(_seconds):
            return None

        run_state.reset_run_state()
        monkeypatch.setattr("src.core.notifier.notify", _capture)
        monkeypatch.setattr(claimer_module.asyncio, "sleep", _no_wait)
        monkeypatch.setattr(claimer_module.cfg, "notify_login_request", True)
        monkeypatch.setattr(claimer_module.cfg, "notify_skip_stores", {"itchio"})
        yield messages
        run_state.reset_run_state()

    def _prompt(self, site):
        claimer = gp.GamerPowerClaimer.__new__(gp.GamerPowerClaimer)

        async def _done() -> bool:
            return True

        return asyncio.run(claimer._wait_for_vnc_login(_done, timeout=10, store_key=site))

    def test_its_vnc_prompt_stays_quiet(self, sent):
        assert self._prompt("itchio") is True
        assert sent == []

    def test_another_site_still_asks(self, sent):
        self._prompt("indiegala")
        assert len(sent) == 1

    @pytest.mark.parametrize("site,kept", [("itchio", 0), ("indiegala", 1)])
    def test_its_giveaways_leave_the_summary(self, monkeypatch, site, kept):
        monkeypatch.setattr(gp.cfg, "notify_skip_stores", {"itchio"})
        claimer = gp.GamerPowerClaimer.__new__(gp.GamerPowerClaimer)
        claimer.notify_games = []

        async def _handler(game):
            claimer.notify_games.append({"title": game["title"], "url": "", "status": "claimed"})

        monkeypatch.setattr(claimer, "_side_store", lambda _store: ("site", _handler))
        asyncio.run(claimer._process_side_store(site, {"title": "A game"}))
        assert len(claimer.notify_games) == kept


class TestTheRestOfTheSummary:
    def test_a_crashed_store_minds_notify_errors(self):
        line = next(l for l in MAIN_SOURCE.splitlines() if "claimer crashed with an unhandled" in l)
        guard = MAIN_SOURCE.split(line, 1)[0].rsplit("\n", 2)[-2]
        assert "cfg.notify_errors" in guard and "store_notify_enabled" in guard

    def test_no_store_sends_its_own_failure_message(self):
        # A failure is one line in the summary, never a second message on top of it.
        for path in (ROOT / "src" / "stores").glob("*.py"):
            assert "cfg.notify_claim_fails" not in path.read_text(encoding="utf-8"), path.name
