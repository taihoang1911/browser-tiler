from selenium import webdriver

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from browser_tiler import WindowTiler


def main() -> None:
    with WindowTiler(monitor="0", gap=6) as tiler:
        for _ in range(4):
            driver = webdriver.Chrome()
            driver.get("https://example.com")
            tiler.add(driver, arrange=False)

        tiler.arrange()
        print("Arranged. Press Ctrl+C to close everything.")

        try:
            tiler.watch()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
