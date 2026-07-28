from __future__ import annotations

import ctypes
import ctypes.wintypes
import os
import time
from typing import Any

from .geometry import WindowRect, WorkArea


def enable_dpi_awareness() -> None:
    if os.name != "nt":
        return

    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
        return
    except (AttributeError, OSError):
        pass

    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except (AttributeError, OSError):
        pass


def load_win32api() -> Any:
    if os.name != "nt":
        raise RuntimeError("This library currently supports Windows only.")

    try:
        import win32api
    except ImportError as exc:
        raise RuntimeError(
            "pywin32 is not installed. Run:\n"
            "  py -m pip install -U pywin32"
        ) from exc

    return win32api


def get_work_areas() -> list[WorkArea]:
    win32api = load_win32api()
    raw_areas: list[tuple[bool, int, int, int, int, str]] = []

    for monitor_handle, _monitor_dc, _monitor_rect in win32api.EnumDisplayMonitors():
        info = win32api.GetMonitorInfo(monitor_handle)
        left, top, right, bottom = info["Work"]
        primary = bool(info.get("Flags", 0) & 1)
        device = str(info.get("Device", "Unknown"))

        raw_areas.append(
            (primary, int(left), int(top), int(right), int(bottom), device)
        )

    raw_areas.sort(key=lambda item: (not item[0], item[1], item[2]))

    return [
        WorkArea(
            index=index,
            left=left,
            top=top,
            right=right,
            bottom=bottom,
            primary=primary,
            device=device,
        )
        for index, (primary, left, top, right, bottom, device) in enumerate(
            raw_areas
        )
    ]


def select_work_areas(monitor: str) -> list[WorkArea]:
    areas = get_work_areas()

    if monitor.lower() == "all":
        return areas

    try:
        monitor_index = int(monitor)
    except ValueError as exc:
        raise ValueError("monitor must be a monitor index or 'all'.") from exc

    if monitor_index < 0 or monitor_index >= len(areas):
        raise ValueError(
            f"Monitor {monitor_index} does not exist. "
            f"This machine has {len(areas)} monitor(s)."
        )

    return [areas[monitor_index]]


def find_hwnd_by_pid(pid: int, timeout: float = 10.0) -> int | None:
    import win32con
    import win32gui
    import win32process

    def collect() -> list[int]:
        found: list[int] = []

        def callback(hwnd: int, _param: Any) -> bool:
            if not win32gui.IsWindowVisible(hwnd):
                return True

            _thread_id, window_pid = win32process.GetWindowThreadProcessId(hwnd)
            if window_pid == pid:
                style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
                if style & win32con.WS_CAPTION:
                    found.append(hwnd)

            return True

        win32gui.EnumWindows(callback, None)
        return found

    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        handles = collect()
        if handles:
            return handles[0]
        time.sleep(0.2)

    return None


def find_hwnd_by_title_marker(marker: str, timeout: float = 10.0) -> int | None:
    import win32gui

    def collect() -> list[int]:
        found: list[int] = []

        def callback(hwnd: int, _param: Any) -> bool:
            if win32gui.IsWindowVisible(hwnd):
                if marker in win32gui.GetWindowText(hwnd):
                    found.append(hwnd)
            return True

        win32gui.EnumWindows(callback, None)
        return found

    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        handles = collect()
        if handles:
            return handles[0]
        time.sleep(0.2)

    return None


def is_window_alive(hwnd: int) -> bool:
    import win32gui

    try:
        return bool(win32gui.IsWindow(hwnd))
    except Exception:
        return False


def get_invisible_border(hwnd: int) -> tuple[int, int, int, int]:
    import win32gui

    try:
        rect = ctypes.wintypes.RECT()
        DWMWA_EXTENDED_FRAME_BOUNDS = 9
        ctypes.windll.dwmapi.DwmGetWindowAttribute(
            ctypes.wintypes.HWND(hwnd),
            ctypes.wintypes.DWORD(DWMWA_EXTENDED_FRAME_BOUNDS),
            ctypes.byref(rect),
            ctypes.sizeof(rect),
        )
        window_rect = win32gui.GetWindowRect(hwnd)

        return (
            rect.left - window_rect[0],
            rect.top - window_rect[1],
            window_rect[2] - rect.right,
            window_rect[3] - rect.bottom,
        )
    except (AttributeError, OSError):
        return (0, 0, 0, 0)


def move_window_native(hwnd: int, rect: WindowRect) -> None:
    import win32con
    import win32gui

    placement = win32gui.GetWindowPlacement(hwnd)
    if placement[1] in (win32con.SW_SHOWMAXIMIZED, win32con.SW_SHOWMINIMIZED):
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)

    left, top, right, bottom = get_invisible_border(hwnd)

    win32gui.SetWindowPos(
        hwnd,
        0,
        rect.x - left,
        rect.y - top,
        rect.width + left + right,
        rect.height + top + bottom,
        win32con.SWP_NOZORDER | win32con.SWP_NOACTIVATE,
    )
