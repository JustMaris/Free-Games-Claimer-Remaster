import asyncio

from src.core.browser import BrowserAdapter
from src.core.claimer import open_first_tab


class FakePage:
    def __init__(self) -> None:
        self.urls = []

    async def goto(self, url, **kwargs):
        self.urls.append(url)


class FakeContext:
    def __init__(self, pages=None) -> None:
        self.pages = list(pages or [])
        self.created = 0

    async def new_page(self):
        self.created += 1
        page = FakePage()
        self.pages.append(page)
        return page


def _open(context):
    return asyncio.run(open_first_tab(BrowserAdapter(context)))


class TestOpenFirstTab:
    def test_existing_page_is_reused(self):
        page = FakePage()
        context = FakeContext([page])

        result = _open(context)

        assert result._page is page
        assert page.urls == ["about:blank"]
        assert context.created == 0

    def test_page_is_created_when_context_is_empty(self):
        context = FakeContext()

        result = _open(context)

        assert result._page is context.pages[0]
        assert result._page.urls == ["about:blank"]
        assert context.created == 1
