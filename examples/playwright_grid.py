import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from playwright.sync_api import sync_playwright

from browser_tiler import WindowTiler


def main() -> None:
    with sync_playwright() as p:
        tiler = WindowTiler(monitor="0", gap=6)

        for _ in range(4):
            browser = p.chromium.launch(headless=False)
            page = browser.new_page()
            page.goto("https://example.com")
            tiler.add(page, arrange=False)

        tiler.arrange()
        print("Arranged. Press Ctrl+C to close everything.")

        try:
            tiler.watch()
        except KeyboardInterrupt:
            pass
        finally:
            tiler.close_all()


if __name__ == "__main__":
    main()
