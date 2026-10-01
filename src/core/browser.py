from __future__ import annotations

from typing import Any

from playwright.async_api import BrowserContext, ElementHandle, Page, TimeoutError as PlaywrightTimeoutError


class Element:
    __slots__ = ('_handle',)
    
    def __init__(self, handle: ElementHandle) -> None:
        self._handle = handle

    async def click(self, *args, **kwargs) -> None:
        await self._handle.click(*args, **kwargs)

    async def clear_input(self) -> None:
        await self._handle.fill("")

    async def send_keys(self, value: str) -> None:
        if value == "\r":
            await self._handle.press("Enter")
        else:
            await self._handle.type(value)

    async def apply(self, script: str) -> Any:
        return await self._handle.evaluate(script)


class PageAdapter:
    __slots__ = ('_page',)
    
    def __init__(self, page: Page) -> None:
        self._page = page

    @property
    def url(self) -> str:
        return self._page.url

    async def get(self, url: str) -> PageAdapter:
        await self._page.goto(url, wait_until="domcontentloaded")
        return self

    async def reload(self) -> None:
        await self._page.reload(wait_until="domcontentloaded")

    async def evaluate(self, expression: str, await_promise: bool = False) -> Any:
        try:
            return await self._page.evaluate(expression)
        except Exception as exc:
            if "Illegal return statement" not in str(exc):
                raise
            return await self._page.evaluate(f"() => {{ {expression} }}")

    async def find(self, selector: str, timeout: float = 10) -> Element | None:
        timeout_ms = timeout * 1000
        try:
            css = selector.startswith((
                "#", ".", "[", "a", "button", "div", "form", "iframe", "input",
                "label", "option", "select", "span", "textarea",
            )) or any(token in selector for token in (" > ", " + ", " ~ ", "::"))
            if css:
                handle = await self._page.wait_for_selector(selector, timeout=timeout_ms)
            else:
                locator = self._page.get_by_text(selector, exact=False).first
                await locator.wait_for(timeout=timeout_ms)
                handle = await locator.element_handle()
            return Element(handle) if handle else None
        except PlaywrightTimeoutError:
            return None

    async def select(self, selector: str, timeout: float = 10) -> Element | None:
        try:
            handle = await self._page.wait_for_selector(selector, timeout=timeout * 1000)
            return Element(handle) if handle else None
        except PlaywrightTimeoutError:
            return None

    async def save_screenshot(self, path: str) -> None:
        await self._page.screenshot(path=path)

    async def scroll_down(self, amount: int) -> None:
        await self._page.mouse.wheel(0, amount)

    async def scroll_up(self, amount: int) -> None:
        await self._page.mouse.wheel(0, -amount)


class BrowserAdapter:
    __slots__ = ('context',)
    
    def __init__(self, context: BrowserContext) -> None:
        self.context = context

    @property
    def tabs(self) -> list[PageAdapter]:
        return [PageAdapter(page) for page in self.context.pages]

    async def get(self, url: str, new_tab: bool = False, new_window: bool = False) -> PageAdapter:
        page = await self.context.new_page() if new_tab or new_window or not self.context.pages else self.context.pages[0]
        adapter = PageAdapter(page)
        await adapter.get(url)
        return adapter

    async def update_targets(self) -> None:
        return None

    async def stop(self) -> None:
        await self.context.close()
