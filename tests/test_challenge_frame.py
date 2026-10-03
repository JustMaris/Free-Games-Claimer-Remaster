import asyncio
from types import SimpleNamespace

from src.core.claimer import BaseClaimer


def _frame(url, box):
    async def bounding_box():
        return box

    async def frame_element():
        return SimpleNamespace(bounding_box=bounding_box)

    return SimpleNamespace(url=url, frame_element=frame_element)


def _visible(*frames):
    claimer = BaseClaimer()
    claimer.page = SimpleNamespace(_page=SimpleNamespace(frames=list(frames)))
    return asyncio.run(claimer._challenge_frame_visible())


CHALLENGE = "https://newassets.hcaptcha.com/captcha/v1/abc/static/hcaptcha.html#frame=challenge&id=1"


def test_on_screen_hcaptcha_challenge_counts():
    assert _visible(_frame(CHALLENGE, {"x": 380, "y": 70, "width": 520, "height": 580}))


def test_parked_off_screen_challenge_does_not_count():
    assert not _visible(_frame(CHALLENGE, {"x": 0, "y": -10000, "width": 400, "height": 600}))


def test_checkbox_frame_and_ordinary_frames_do_not_count():
    checkbox = CHALLENGE.replace("frame=challenge", "frame=checkbox")
    assert not _visible(
        _frame(checkbox, {"x": 10, "y": 10, "width": 300, "height": 150}),
        _frame("https://store.epicgames.com/purchase", {"x": 0, "y": 0, "width": 1280, "height": 720}),
    )
