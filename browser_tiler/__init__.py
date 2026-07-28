from .adapters import (
    BrowserAdapter,
    PlaywrightAdapter,
    SeleniumAdapter,
    wrap,
)
from .geometry import WindowRect, WorkArea, build_layout, choose_grid
from .tiler import TiledWindow, WindowTiler
from .winapi import enable_dpi_awareness, get_work_areas

__version__ = "0.1.1"

__all__ = [
    "BrowserAdapter",
    "PlaywrightAdapter",
    "SeleniumAdapter",
    "TiledWindow",
    "WindowRect",
    "WindowTiler",
    "WorkArea",
    "build_layout",
    "choose_grid",
    "enable_dpi_awareness",
    "get_work_areas",
    "wrap",
]
