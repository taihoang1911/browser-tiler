from __future__ import annotations

import uuid
from typing import Any, Protocol, runtime_checkable

from .geometry import WindowRect
from .winapi import find_hwnd_by_title_marker


@runtime_checkable
class BrowserAdapter(Protocol):
    def is_alive(self) -> bool:
        ...

    def resolve_hwnd(self, timeout: float = 10.0) -> int | None:
        ...

    def fallback_set_rect(self, rect: WindowRect) -> None:
        ...

    def close(self) -> None:
        ...


def _resolve_hwnd_via_title(
    get_title: Any,
    set_title: Any,
    timeout: float,
) -> int | None:
    marker = f"tiler-{uuid.uuid4().hex[:12]}"

    try:
        original_title = get_title()
    except Exception:
        original_title = ""

    try:
        set_title(f"{marker} {original_title}")
        return find_hwnd_by_title_marker(marker, timeout=timeout)
    finally:
        try:
            set_title(original_title)
        except Exception:
            pass


class SeleniumAdapter:
    def __init__(self, driver: Any) -> None:
        self.driver = driver

    def is_alive(self) -> bool:
        try:
            return bool(self.driver.window_handles)
        except Exception:
            return False

    def resolve_hwnd(self, timeout: float = 10.0) -> int | None:
        pid = getattr(self.driver, "browser_pid", None)
        if pid:
            from .winapi import find_hwnd_by_pid

            hwnd = find_hwnd_by_pid(int(pid), timeout=timeout)
            if hwnd is not None:
                return hwnd

        def get_title() -> str:
            return str(self.driver.execute_script("return document.title;") or "")

        def set_title(value: str) -> None:
            self.driver.execute_script(
                "document.title = arguments[0];", value
            )

        return _resolve_hwnd_via_title(get_title, set_title, timeout)

    def fallback_set_rect(self, rect: WindowRect) -> None:
        self.driver.set_window_rect(
            x=rect.x,
            y=rect.y,
            width=rect.width,
            height=rect.height,
        )

    def close(self) -> None:
        self.driver.quit()


class PlaywrightAdapter:
    def __init__(self, page: Any) -> None:
        self.page = page

    def is_alive(self) -> bool:
        try:
            return not self.page.is_closed()
        except Exception:
            return False

    def resolve_hwnd(self, timeout: float = 10.0) -> int | None:
        def get_title() -> str:
            return str(self.page.title() or "")

        def set_title(value: str) -> None:
            self.page.evaluate("value => { document.title = value; }", value)

        return _resolve_hwnd_via_title(get_title, set_title, timeout)

    def fallback_set_rect(self, rect: WindowRect) -> None:
        self.page.set_viewport_size(
            {"width": rect.width, "height": rect.height}
        )

    def close(self) -> None:
        try:
            context = self.page.context
            browser = context.browser
            self.page.close()
            if browser is not None and not browser.contexts:
                browser.close()
        except Exception:
            pass


def wrap(target: Any) -> BrowserAdapter:
    if isinstance(target, BrowserAdapter) and not hasattr(target, "window_handles"):
        return target

    if hasattr(target, "window_handles") and hasattr(target, "execute_script"):
        return SeleniumAdapter(target)

    if hasattr(target, "is_closed") and hasattr(target, "evaluate"):
        return PlaywrightAdapter(target)

    raise TypeError(
        "Unrecognized browser object: "
        f"{type(target).__name__}. Pass a selenium WebDriver, "
        "undetected-chromedriver, Playwright Page, or a custom BrowserAdapter."
    )
