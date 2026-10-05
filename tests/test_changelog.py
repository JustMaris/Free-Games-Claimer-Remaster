"""CHANGELOG.md follows Keep a Changelog 1.1.0, https://keepachangelog.com/en/1.1.0/.

Every rule below is one of that page's, so a release note that drifts from it fails here first.
"""

import re
from pathlib import Path

import pytest

from src.version import __version__

TEXT = (Path(__file__).resolve().parent.parent / "CHANGELOG.md").read_text(encoding="utf-8")
REPO = "https://github.com/P-Adamiec/Free-Games-Claimer-Remaster"
TYPES = ["Added", "Changed", "Deprecated", "Removed", "Fixed", "Security"]
HEADING = re.compile(r"^## \[(Unreleased|\d+\.\d+)\](?: - (\d{4}-\d{2}-\d{2}))?$")
LINK = re.compile(r"^\[([^\]]+)\]: (\S+)$", re.M)

HEADER, *_SECTIONS = re.split(r"(?m)^(?=## )", TEXT)
SECTIONS = {part.split("\n", 1)[0]: LINK.sub("", part.split("\n", 1)[1]) for part in _SECTIONS}
NAMES = [HEADING.match(h).group(1) if HEADING.match(h) else h for h in SECTIONS]
RELEASES = [n for n in NAMES if n != "Unreleased"]


def _number(name: str) -> tuple:
    return tuple(int(part) for part in name.split("."))


class TestTheFile:
    def test_the_header_names_the_format_and_the_versioning(self):
        assert "[Keep a Changelog](https://keepachangelog.com/en/1.1.0/)" in HEADER
        assert "Semantic Versioning" in HEADER

    @pytest.mark.parametrize("heading", list(SECTIONS))
    def test_every_version_heading_has_the_standard_form(self, heading):
        match = HEADING.match(heading)
        assert match, f"{heading!r} is not '## [X.Y] - YYYY-MM-DD' or '## [Unreleased]'"
        assert bool(match.group(2)) == (match.group(1) != "Unreleased"), heading

    def test_unreleased_comes_first(self):
        assert NAMES[0] == "Unreleased"

    def test_the_newest_version_comes_first(self):
        assert RELEASES == sorted(RELEASES, key=_number, reverse=True)
        dates = [HEADING.match(h).group(2) for h in SECTIONS if HEADING.match(h) and HEADING.match(h).group(2)]
        assert dates == sorted(dates, reverse=True)

    def test_the_newest_release_is_the_running_version(self):
        assert RELEASES[0] == __version__

    @pytest.mark.parametrize("name", ["unreleased"] + RELEASES)
    def test_every_version_is_linkable(self, name):
        links = {label.lower(): url for label, url in LINK.findall(TEXT)}
        assert name.lower() in links, f"no '[{name}]: …' link at the bottom"
        assert links[name.lower()].startswith(REPO + "/")

    def test_no_em_dash(self):
        assert "\u2014" not in TEXT


class TestEveryVersion:
    @pytest.mark.parametrize("heading", list(SECTIONS))
    def test_only_the_six_types_in_their_order(self, heading):
        types = re.findall(r"(?m)^### (.+)$", SECTIONS[heading])
        assert all(t in TYPES for t in types), f"{heading}: {types}"
        assert types == sorted(types, key=TYPES.index) and len(types) == len(set(types)), f"{heading}: {types}"

    @pytest.mark.parametrize("heading", list(SECTIONS))
    def test_no_type_is_left_empty(self, heading):
        for name, body in re.findall(r"(?ms)^### (.+?)$(.*?)(?=^### |\Z)", SECTIONS[heading]):
            assert body.strip(), f"{heading}: '### {name}' has no entries"
