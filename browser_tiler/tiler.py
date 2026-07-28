from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from .adapters import BrowserAdapter, wrap
from .geometry import (
    MIN_RECOMMENDED_HEIGHT,
    MIN_RECOMMENDED_WIDTH,
    WindowRect,
    WorkArea,
    build_layout,
)
from .winapi import (
    enable_dpi_awareness,
    is_window_alive,
    move_window_native,
    select_work_areas,
)


@dataclass
class TiledWindow:
    number: int
    adapter: BrowserAdapter
    hwnd: int | None = None
    extra: dict[str, Any] = field(default_factory=dict)


class WindowTiler:
    def __init__(
        self,
        monitor: str = "0",
        gap: int = 6,
        hwnd_timeout: float = 10.0,
    ) -> None:
        if gap < 0:
            raise ValueError("Gap between windows cannot be negative.")

        enable_dpi_awareness()
        self.monitor = monitor
        self.gap = gap
        self.hwnd_timeout = hwnd_timeout
        self.windows: list[TiledWindow] = []
        self._warned_about_small_cells = False

    def add(self, target: Any, *, arrange: bool = True) -> TiledWindow:
        adapter = wrap(target)
        number = max((window.number for window in self.windows), default=0) + 1
        hwnd = adapter.resolve_hwnd(timeout=self.hwnd_timeout)

        window = TiledWindow(number=number, adapter=adapter, hwnd=hwnd)
        self.windows.append(window)

        if arrange:
            self.arrange()

        return window

    def remove_closed(self) -> int:
        active: list[TiledWindow] = []
        removed = 0

        for window in self.windows:
            alive = window.adapter.is_alive()

            if alive and window.hwnd is not None:
                alive = is_window_alive(window.hwnd)

            if alive:
                active.append(window)
            else:
                removed += 1

        if removed:
            self.windows = active
            self.arrange()

        return removed

    def selected_areas(self) -> list[WorkArea]:
        return select_work_areas(self.monitor)

    def planned_layout(self, count: int) -> list[WindowRect]:
        return build_layout(count, self.selected_areas(), self.gap)

    def arrange(self) -> None:
        if not self.windows:
            return

        rectangles = self.planned_layout(len(self.windows))

        for window, rect in zip(self.windows, rectangles):
            if (
                not self._warned_about_small_cells
                and (
                    rect.width < MIN_RECOMMENDED_WIDTH
                    or rect.height < MIN_RECOMMENDED_HEIGHT
                )
            ):
                print(
                    "[Warning] Too many windows for available screen area. "
                    "Browsers may not shrink enough and could overlap."
                )
                self._warned_about_small_cells = True

            try:
                if window.hwnd is not None and is_window_alive(window.hwnd):
                    move_window_native(window.hwnd, rect)
                else:
                    window.adapter.fallback_set_rect(rect)
            except Exception as exc:
                print(
                    f"[Warning] Failed to arrange window #{window.number}: {exc}"
                )

    def watch(self, interval: float = 1.0) -> None:
        if interval <= 0:
            raise ValueError("interval must be greater than 0.")

        while self.windows:
            time.sleep(interval)
            removed = self.remove_closed()
            if removed:
                print(
                    f"Detected {removed} closed window(s). Rearranging..."
                )

    def close_all(self) -> None:
        windows = self.windows[:]
        self.windows.clear()

        for window in windows:
            try:
                window.adapter.close()
            except Exception:
                pass

    def __enter__(self) -> "WindowTiler":
        return self

    def __exit__(self, *_exc: Any) -> None:
        self.close_all()
