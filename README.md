# browser-tiler

A Python library that tiles browser testing windows into a non-overlapping grid
on Windows. Supports **selenium**, **undetected-chromedriver**, **Playwright**
(headed), and other frameworks via custom adapters.

Advantages over plain `set_window_rect`:

- Positions windows via the Windows API (`SetWindowPos`) in **physical
  pixels** — no offset issues when Windows uses 125% / 150% display scaling.
- Automatically compensates for the **invisible borders** of Windows 10/11
  windows, so cells fit tightly without spilling off screen.
- Multi-monitor support with automatic grid selection (prefers landscape
  windows, minimizes empty cells).
- Automatically rearranges when the user closes some windows (`watch()`).

## Installation

```bash
pip install browser-tiler
```

Install with the framework you use:

```bash
pip install browser-tiler[selenium]     # with selenium
pip install browser-tiler[uc]           # with undetected-chromedriver
pip install browser-tiler[playwright]   # with playwright
```

Or install from source (from this directory):

```bash
pip install -e .
```

## Quick start

```python
from browser_tiler import WindowTiler

tiler = WindowTiler(monitor="0", gap=6)   # monitor="all" to use every monitor

tiler.add(driver)   # selenium WebDriver or undetected-chromedriver
tiler.add(page)     # Playwright Page (headless=False)

tiler.arrange()     # tile everything into a grid
tiler.watch()       # rearrange when a window closes; Ctrl+C to exit
tiler.close_all()   # close everything
```

`add()` auto-detects the object type. You can mix selenium and Playwright in
the same grid.

### As a context manager

```python
with WindowTiler(gap=6) as tiler:
    for _ in range(4):
        driver = webdriver.Chrome()
        tiler.add(driver, arrange=False)
    tiler.arrange()
    tiler.watch()
# all browsers are closed when the with block exits
```

## Supporting a new framework

Write a class that satisfies `BrowserAdapter` (4 methods) and pass it directly
to `tiler.add()`:

```python
class MyAdapter:
    def is_alive(self) -> bool: ...
    def resolve_hwnd(self, timeout: float = 10.0) -> int | None: ...
    def fallback_set_rect(self, rect) -> None: ...
    def close(self) -> None: ...
```

Framework-independent window discovery: inject a temporary marker into
`document.title` and scan all visible window titles (see
`_resolve_hwnd_via_title` in `adapters.py`).

## Examples

- `examples/selenium_grid.py` — 4 selenium Chrome windows.
- `examples/playwright_grid.py` — 4 Playwright Chromium windows.
- `resize.py` — CLI that opens a batch of undetected-chromedriver windows:
  `py resize.py --count 6 --url https://google.com --chrome-major 150`

## Limitations

- **Windows only** (uses the win32 API). All OS-specific code lives in
  `browser_tiler/winapi.py`, so macOS/Linux support can be added later.
- Playwright must run **headed**; each window needs its own browser instance
  (pages in the same browser open as tabs).
