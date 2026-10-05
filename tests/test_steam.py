"""Steam: what may be claimed on a store page."""

from pathlib import Path

import pytest

from src.stores.steam import (DEMO_JS, KEY_OUTCOMES, REMEMBER_ME_JS, REMEMBER_ME_STATE_JS,
                              activation_outcome, is_waiting_steam_key)

SOURCE = (Path(__file__).resolve().parent.parent / "src" / "stores" / "steam.py").read_text(encoding="utf-8")


class TestRememberMe:
    """Issue #65: read live on 4.10, the box is a div with role="checkbox" and starts ticked."""

    def test_the_box_is_found_by_its_role_inside_the_login_form(self):
        assert '[role="checkbox"]' in REMEMBER_ME_JS and 'data-featuretarget="login"' in REMEMBER_ME_JS
        assert 'input[type="checkbox"]' not in SOURCE

    def test_a_ticked_box_is_never_clicked(self):
        # Clicking a box Steam already ticks would switch "Remember me" off.
        assert REMEMBER_ME_JS.index("=== 'true'") < REMEMBER_ME_JS.index("box.click()")

    def test_the_result_is_read_back_after_react_applies_it(self):
        assert "aria-checked" in REMEMBER_ME_STATE_JS
        block = SOURCE.split("# --- Remember Me", 1)[1].split("# --- Submit", 1)[0]
        assert block.index("REMEMBER_ME_JS") < block.index("self.sleep(0.5)") < block.index("REMEMBER_ME_STATE_JS")


class TestDemosAreNeverTheGiveaway:
    """Issue #62: a game's demo was added while checking a DLC's base game.

    Replayed in a real browser on the Explosive Odds page: with the demo button reading
    "Add to Library", the old base-game helper clicked it, and the price check took the demo
    block for a free one. Both now pass the demo by.
    """

    def test_demo_blocks_are_known_by_steams_own_markup(self):
        assert ".demo_above_purchase" in DEMO_JS and "#demoGameBtn" in DEMO_JS

    def test_every_script_that_judges_or_clicks_uses_it(self):
        for name in ("is_unclaimed_f2p", "price_check_raw", "claimed_raw", "add_raw"):
            call = SOURCE.split(f"{name} = await self.page.evaluate(", 1)[1][:200]
            assert "DEMO_JS" in call, name

    def test_the_base_game_helper_skips_demo_buttons(self):
        helper = SOURCE.split("async def _ensure_base_game", 1)[1]
        assert helper.count("isDemoBtn(") >= 3

    def test_no_backspace_hides_in_a_regex(self):
        # A \b in a plain Python string reaches the browser as a backspace and the regex never matches.
        assert chr(8) not in SOURCE
        assert "price_check_raw = await self.page.evaluate(r'''" in SOURCE


class TestActivatingKeysOnSteam:
    """Fanatical giveaways hand out Steam keys; the bot enters them on Steam's own key page."""


    # Word for word what Steam showed on 4.10 for an invalid key.
    INVALID = ("The product code you've entered is not valid or is not a product code. Please double check to see "
               "if you've mistyped your key. I, L, and 1 can look alike, as can V and Y, and 0 and O.")

    @pytest.mark.parametrize("text,receipt,outcome", [
        ("", True, "activated"),
        (INVALID, False, "invalid"),
        ("This Steam account already owns the product(s) contained in this offer.", False, "owned"),
        ("The product code you've entered has already been activated by a different Steam account.", False, "used"),
        ("There have been too many recent activation attempts from this account or Internet address.", False,
         "rate-limited"),
        ("This product requires ownership of another product before activation.", False, "needs-base"),
        ("", False, "unknown"),
    ])
    def test_steams_answer_is_read(self, text, receipt, outcome):
        assert activation_outcome(text, receipt) == outcome

    def test_every_final_answer_has_a_status(self):
        assert set(KEY_OUTCOMES) == {"activated", "owned", "used", "invalid", "needs-base", "region"}
        assert KEY_OUTCOMES["needs-base"][1] == "failed:missing_base"

    @pytest.mark.parametrize("status,code,extra,waiting", [
        ("claimed", "AAAAA-BBBBB-CCCCC", '{"external_store": "steam"}', True),
        ("claimed and activated", "AAAAA-BBBBB-CCCCC", '{"external_store": "steam"}', False),
        ("claimed", "", '{"external_store": "steam"}', False),
        ("claimed", "TKT8ED0BC5D94D2EBC", '{"external_store": "gog"}', False),
        ("claimed", "AAAAA-BBBBB-CCCCC", None, False),
        ("claimed", "AAAAA-BBBBB-CCCCC", "not json", False),
    ])
    def test_only_keys_left_for_steam_are_picked(self, status, code, extra, waiting):
        assert is_waiting_steam_key(status, code, extra) is waiting

    def test_a_dry_run_activates_nothing(self):
        block = SOURCE.split("async def _activate_key", 1)[1].split("\n    async def ", 1)[0]
        assert block.index("if cfg.dryrun:") < block.index("send_keys(key)")

    def test_the_key_never_reaches_the_log_whole(self):
        block = SOURCE.split("async def _activate_key", 1)[1].split("\n    async def ", 1)[0]
        assert "key[:5]" in block and '", key)' not in block and "%s\", key" not in block

    def test_it_runs_after_the_sites_that_hand_keys_out(self):
        main = (Path(__file__).resolve().parent.parent / "main.py").read_text(encoding="utf-8")
        assert main.index("claim_side_stores(routed)") < main.index("redeem_pending_keys()")
        assert '"Steam" in store_names' in main.split("redeem_pending_keys()", 1)[0][-700:]
