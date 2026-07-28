from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Iterable, Sequence

from browser_tiler import WindowTiler, WorkArea, enable_dpi_awareness, get_work_areas
from browser_tiler.geometry import WindowRect


def load_undetected_chromedriver() -> Any:
    try:
        import undetected_chromedriver as uc
    except ImportError as exc:
        raise RuntimeError(
            "undetected-chromedriver is not installed. Run:\n"
            "  py -m pip install -U undetected-chromedriver selenium"
        ) from exc

    return uc


def launch_chrome(
    *,
    number: int,
    url: str,
    profile_root: Path,
    temporary_profile: bool,
    initial_rect: WindowRect,
    chrome_major: int | None,
) -> Any:
    uc = load_undetected_chromedriver()
    options = uc.ChromeOptions()

    options.add_argument(f"--window-position={initial_rect.x},{initial_rect.y}")
    options.add_argument(
        f"--window-size={initial_rect.width},{initial_rect.height}"
    )
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")
    options.add_argument("--disable-notifications")

    chrome_kwargs: dict[str, Any] = {
        "options": options,
        "use_subprocess": True,
    }

    if not temporary_profile:
        profile_dir = (profile_root / f"profile_{number:03d}").resolve()
        profile_dir.mkdir(parents=True, exist_ok=True)
        chrome_kwargs["user_data_dir"] = str(profile_dir)

    if chrome_major is not None:
        chrome_kwargs["version_main"] = chrome_major

    driver = uc.Chrome(**chrome_kwargs)
    driver.get(url)

    return driver


def print_monitors(areas: Iterable[WorkArea]) -> None:
    print("Monitors:")

    for area in areas:
        primary_text = " - primary" if area.primary else ""
        print(
            f"  {area.index}: {area.device} | "
            f"{area.width}x{area.height} | "
            f"position ({area.left}, {area.top}){primary_text}"
        )


def positive_integer(value: str) -> int:
    parsed = int(value)

    if parsed <= 0:
        raise argparse.ArgumentTypeError("Value must be greater than 0.")

    return parsed


def non_negative_integer(value: str) -> int:
    parsed = int(value)

    if parsed < 0:
        raise argparse.ArgumentTypeError("Value cannot be negative.")

    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Open and automatically tile multiple undetected-chromedriver "
            "windows on Windows."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "-n",
        "--count",
        type=positive_integer,
        default=4,
        help="Number of Chrome windows to open.",
    )
    parser.add_argument(
        "--url",
        default="about:blank",
        help="URL to open in every window.",
    )
    parser.add_argument(
        "--monitor",
        default="0",
        help="Monitor index to use; pass 'all' to use every monitor.",
    )
    parser.add_argument(
        "--gap",
        type=non_negative_integer,
        default=6,
        help="Gap between windows, in pixels.",
    )
    parser.add_argument(
        "--profile-root",
        type=Path,
        default=Path("chrome_profiles"),
        help="Directory holding separate Chrome profiles.",
    )
    parser.add_argument(
        "--temporary-profiles",
        action="store_true",
        help="Use temporary profiles and do not persist login state.",
    )
    parser.add_argument(
        "--chrome-major",
        type=positive_integer,
        default=None,
        help="Chrome major version, e.g. 150.",
    )
    parser.add_argument(
        "--watch-interval",
        type=float,
        default=1.0,
        help="Seconds between checks for closed windows.",
    )
    parser.add_argument(
        "--list-monitors",
        action="store_true",
        help="Only list monitors and exit.",
    )

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    enable_dpi_awareness()
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.watch_interval <= 0:
        parser.error("--watch-interval must be greater than 0.")

    try:
        all_areas = get_work_areas()
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if args.list_monitors:
        print_monitors(all_areas)
        return 0

    try:
        tiler = WindowTiler(monitor=args.monitor, gap=args.gap)
        initial_layout = tiler.planned_layout(args.count)
    except Exception as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 1

    print_monitors(all_areas)
    print(
        f"\nOpening {args.count} windows on "
        f"{'all monitors' if args.monitor.lower() == 'all' else f'monitor {args.monitor}'}..."
    )

    for index, initial_rect in enumerate(initial_layout, start=1):
        try:
            print(f"  Opening Chrome {index}/{args.count}...")
            driver = launch_chrome(
                number=index,
                url=args.url,
                profile_root=args.profile_root,
                temporary_profile=args.temporary_profiles,
                initial_rect=initial_rect,
                chrome_major=args.chrome_major,
            )
            tiler.add(driver, arrange=False)
        except Exception as exc:
            print(f"Failed to open Chrome #{index}: {exc}", file=sys.stderr)
            break

    if not tiler.windows:
        print("No Chrome windows were opened.", file=sys.stderr)
        return 1

    tiler.arrange()
    print(
        "\nDone arranging. You can close individual windows directly; "
        "the remaining windows will be rearranged."
    )
    print("Press Ctrl+C in this terminal to close everything and exit.")

    try:
        tiler.watch(interval=args.watch_interval)
    except KeyboardInterrupt:
        print("\nClosing all Chrome windows...")
    finally:
        tiler.close_all()

    print("Exited.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
