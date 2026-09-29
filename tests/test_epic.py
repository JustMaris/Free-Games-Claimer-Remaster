"""Epic claim verification (issue #39).

Walking Epic's checkout only proves what that page displayed, so a claim counts
only once the product page itself reports the game as owned.
"""

import asyncio
from pathlib import Path

import pytest

from src.stores.epic import CHECKOUT_ACTIONS_JS, EpicGamesClaimer, PAGE_STATE_JS, is_owned


class TestOwnedState:
    def test_an_owned_page_is_owned(self):
        assert is_owned({"flow": "owned", "text": "in library"})

    def test_the_button_text_counts_whatever_the_flow_says(self):
        assert is_owned({"flow": "old_cta", "text": "IN LIBRARY"})

    @pytest.mark.parametrize("state", [
        {"flow": "new_get", "text": "get"},
        {"flow": "new_add", "text": "add to library"},
        {"flow": "old_cta", "text": "buy now"},
    ])
    def test_a_page_that_still_offers_the_game_is_not_owned(self, state):
        assert not is_owned(state)

    def test_the_offer_text_is_not_a_confirmation(self):
        # "Add it to your library" is what Epic says before you own anything.
        assert not is_owned({"flow": "new_get", "text": "add it to your library"})

    @pytest.mark.parametrize("state", [{"flow": "unknown", "text": ""}, {}, None])
    def test_an_unreadable_page_is_not_owned(self, state):
        assert not is_owned(state)


class TestPageStateOrder:
    """An "In Library" chip in a recommendation row must not outrank this product's own button."""

    def test_every_claim_button_is_checked_before_ownership(self):
        owned_at = PAGE_STATE_JS.index("'owned'")
        for flow in ("'new_add'", "'new_get'", "'old_cta'"):
            assert PAGE_STATE_JS.index(flow) < owned_at

    def test_the_reader_returns_json(self):
        # page.evaluate() hands back a CDP structure for a plain object, a string survives.
        assert PAGE_STATE_JS.strip().startswith("JSON.stringify(")


class TestCheckoutPolling:
    def test_one_main_dom_read_collects_all_loop_signals(self):
        assert "return { add, accept }" in CHECKOUT_ACTIONS_JS
        assert CHECKOUT_ACTIONS_JS.count("querySelectorAll('button')") == 1

    def test_checkout_action_reader_handles_json_and_bad_results(self):
        claimer = EpicGamesClaimer()

        class Page:
            def __init__(self, result):
                self.result = result

            async def evaluate(self, script):
                assert script == CHECKOUT_ACTIONS_JS
                return self.result

        claimer.page = Page('{"add":true,"accept":false}')
        assert asyncio.run(claimer._checkout_actions()) == {"add": True, "accept": False}
        claimer.page = Page("not json")
        assert asyncio.run(claimer._checkout_actions()) == {}

    def test_new_checkout_loop_uses_one_combined_reader(self):
        source = Path(__file__).resolve().parent.parent / "src" / "stores" / "epic.py"
        block = source.read_text(encoding="utf-8").split("for attempt in range(25):", 1)[1]
        block = block.split("if not add_clicked:", 1)[0]
        assert block.count("_checkout_actions()") == 1
        assert "page.evaluate" not in block


class TestPromotionDeduplication:
    def test_promotion_urls_use_constant_time_membership(self):
        source = Path(__file__).resolve().parent.parent / "src" / "stores" / "epic.py"
        block = source.read_text(encoding="utf-8").split("async def _detect_free_games_api", 1)[1]
        block = block.split("@staticmethod", 1)[0]
        assert "seen_urls: set[str] = set()" in block
        assert "url not in seen_urls" in block
        assert "any(g[\"url\"] == url" not in block


class TestClaimHonesty:
    """Mobile games were reported as claimed on the strength of the checkout page alone."""

    SOURCE = (Path(__file__).resolve().parent.parent / "src" / "stores" / "epic.py").read_text(encoding="utf-8")
    BLOCK = SOURCE.split("async def _claim_game", 1)[1].split("async def _handle_new_checkout", 1)[0]

    def test_the_checkout_result_no_longer_decides(self):
        assert "claimed = await self._handle" not in self.SOURCE

    def test_the_library_decides(self):
        assert "_confirm_in_library" in self.BLOCK

    def test_an_unconfirmed_claim_is_reported_as_such(self):
        assert "failed:unconfirmed" in self.BLOCK

    def test_success_checks_ignore_the_offer_text(self):
        checkout = self.SOURCE.split("async def _handle_new_checkout", 1)[1]
        assert "add it to your library" in checkout


class TestTheCodeScreenIsNotAbandoned:
    """A rejected 2FA code used to spin for two minutes and then take the page away (issue #46)."""

    SOURCE = (Path(__file__).resolve().parent.parent / "src" / "stores" / "epic.py").read_text(encoding="utf-8")
    LOOP = SOURCE.split("otp_tried = 0", 1)[1].split('if "login/review"', 1)[0]

    def test_a_rejected_code_is_retried_once_after_a_reload(self):
        # Epic answers a stale request with "Incorrect response. Please refresh the page."
        assert "page.reload()" in self.LOOP
        assert "otp_tried >= OTP_KEY_ATTEMPTS" in self.LOOP

    def test_the_second_rejection_hands_over_to_the_user(self):
        assert "mfa_manual = True" in self.LOOP

    def test_the_page_is_not_taken_away_while_the_code_screen_is_up(self):
        # The guard has to sit between the wait loop and the navigation that verifies success.
        block = self.SOURCE.split("otp_tried = 0", 1)[1]
        assert block.index("if not mfa_manual and await self._mfa_prompt_present():") < block.index("# verify success")

    def test_what_epic_said_reaches_the_log(self):
        assert "_mfa_error_text" in self.SOURCE


class TestRememberThisBrowser:
    """Ticking it makes the store stop asking for a code on this profile."""

    ROOT = Path(__file__).resolve().parent.parent

    def test_epic_ticks_it_before_submitting(self):
        source = (self.ROOT / "src" / "stores" / "epic.py").read_text(encoding="utf-8")
        block = source.split("async def _fill_code", 1)[1].split("\n    async def ", 1)[0]
        assert block.index("_remember_this_browser()") < block.index("submit.click()")

    def test_prime_ticks_it_before_submitting(self):
        source = (self.ROOT / "src" / "stores" / "prime.py").read_text(encoding="utf-8")
        block = source.split("otp_input.send_keys(self._last_totp)", 1)[1][:600]
        assert "_remember_this_browser()" in block

    def test_it_never_unticks_a_box_the_store_already_ticked(self):
        source = (self.ROOT / "src" / "core" / "claimer.py").read_text(encoding="utf-8")
        block = source.split("async def _remember_this_browser", 1)[1].split("\n    async def ", 1)[0]
        assert "box.checked" in block


class TestBackupCodeScreen:
    """Epic keeps backup codes behind their own screen, verified live on 2026-09-11."""

    SOURCE = (Path(__file__).resolve().parent.parent / "src" / "stores" / "epic.py").read_text(encoding="utf-8")

    def test_the_screen_is_opened_before_a_code_is_typed(self):
        block = self.SOURCE.split("async def _fill_backup_code", 1)[1].split('\n    async def ', 1)[0]
        assert block.index("_open_backup_code_screen()") < block.index("_fill_code(")

    def test_no_code_is_spent_when_the_screen_does_not_open(self):
        block = self.SOURCE.split("async def _fill_backup_code", 1)[1].split('\n    async def ', 1)[0]
        opened = block.index("_open_backup_code_screen()")
        assert block.index("_mark_code_used(") > opened
        assert "leaving your codes alone" in block

    def test_it_clicks_epics_own_option(self):
        block = self.SOURCE.split("async def _open_backup_code_screen", 1)[1].split('\n    async def ', 1)[0]
        assert "#option-backupCode" in block and "another way" in block

    def test_eight_boxes_mean_the_backup_screen(self):
        # The authenticator screen has six numeric boxes, the backup one eight text boxes.
        block = self.SOURCE.split("BACKUP_SCREEN_JS", 1)[1][:400]
        assert "boxes.length > 6" in block


class TestAccountPicker:
    """After a half-finished sign-in Epic asks which account to continue with."""

    SOURCE = (Path(__file__).resolve().parent.parent / "src" / "stores" / "epic.py").read_text(encoding="utf-8")

    def test_the_login_loop_answers_it(self):
        assert "/id/login/switch-account" in self.SOURCE

    def test_it_clicks_the_account_tile(self):
        # Verified live: that screen has no Continue button, only a list of accounts.
        block = self.SOURCE.split("/id/login/switch-account", 1)[1][:700]
        assert "[id^=\"account-\"]" in block


class TestRecoveryCodeBookkeeping:
    """One code per sign-in, never the same one twice, and no crash once they run out."""

    def _claimer(self, tmp_path, monkeypatch):
        # Patch the claimer module's own cfg: reloading config elsewhere leaves it holding the old one.
        from src.core import claimer as claimer_module
        from src.stores.epic import EpicGamesClaimer

        monkeypatch.setattr(claimer_module.cfg, "_data_dir", tmp_path)
        return EpicGamesClaimer()

    def test_it_starts_with_the_first_code(self, tmp_path, monkeypatch):
        claimer = self._claimer(tmp_path, monkeypatch)
        assert claimer._next_unused_code(["aaa", "bbb", "ccc"], "used.txt") == "aaa"

    def test_a_spent_code_is_skipped(self, tmp_path, monkeypatch):
        claimer = self._claimer(tmp_path, monkeypatch)
        claimer._mark_code_used("aaa", "used.txt", ["aaa", "bbb", "ccc"])
        assert claimer._next_unused_code(["aaa", "bbb", "ccc"], "used.txt") == "bbb"

    def test_running_out_is_not_a_crash(self, tmp_path, monkeypatch):
        claimer = self._claimer(tmp_path, monkeypatch)
        for code in ("aaa", "bbb"):
            claimer._mark_code_used(code, "used.txt", ["aaa", "bbb"])
        assert claimer._next_unused_code(["aaa", "bbb"], "used.txt") is None

    def test_no_codes_configured_is_not_a_crash(self, tmp_path, monkeypatch):
        claimer = self._claimer(tmp_path, monkeypatch)
        assert claimer._next_unused_code([], "used.txt") is None

    def test_the_login_loop_tries_a_code_before_giving_up(self):
        source = (Path(__file__).resolve().parent.parent / "src" / "stores" / "epic.py").read_text(encoding="utf-8")
        loop = source.split("otp_tried = 0", 1)[1].split('if "login/review"', 1)[0]
        assert loop.index("_fill_backup_code()") < loop.index("mfa_manual = True")
