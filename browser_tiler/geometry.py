from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Sequence


MIN_RECOMMENDED_WIDTH = 400
MIN_RECOMMENDED_HEIGHT = 260


@dataclass(frozen=True)
class WorkArea:
    index: int
    left: int
    top: int
    right: int
    bottom: int
    primary: bool
    device: str

    @property
    def width(self) -> int:
        return self.right - self.left

    @property
    def height(self) -> int:
        return self.bottom - self.top


@dataclass(frozen=True)
class WindowRect:
    x: int
    y: int
    width: int
    height: int


def choose_grid(
    count: int,
    area_width: int,
    area_height: int,
    target_aspect_ratio: float = 1.45,
) -> tuple[int, int]:
    if count <= 0:
        return 0, 0

    best_score = float("inf")
    best_columns = 1
    best_rows = count

    for columns in range(1, count + 1):
        rows = math.ceil(count / columns)
        cell_width = area_width / columns
        cell_height = area_height / rows
        aspect_ratio = cell_width / max(cell_height, 1)
        empty_cells = columns * rows - count

        aspect_score = abs(math.log(max(aspect_ratio, 0.01) / target_aspect_ratio))
        empty_score = (empty_cells / count) * 0.35
        score = aspect_score + empty_score

        if score < best_score:
            best_score = score
            best_columns = columns
            best_rows = rows

    return best_columns, best_rows


def divide_evenly(items: Sequence[Any], group_count: int) -> list[list[Any]]:
    groups: list[list[Any]] = [[] for _ in range(group_count)]

    for index, item in enumerate(items):
        groups[index % group_count].append(item)

    return groups


def build_layout(
    item_count: int,
    areas: Sequence[WorkArea],
    gap: int,
) -> list[WindowRect]:
    if item_count <= 0:
        return []

    if not areas:
        raise RuntimeError("No monitors found.")

    indexed_items = list(range(item_count))
    groups = divide_evenly(indexed_items, len(areas))
    result: list[WindowRect | None] = [None] * item_count

    for area, group in zip(areas, groups):
        if not group:
            continue

        columns, rows = choose_grid(
            count=len(group),
            area_width=area.width,
            area_height=area.height,
        )

        cell_width = area.width // columns
        cell_height = area.height // rows

        for local_index, original_index in enumerate(group):
            row, column = divmod(local_index, columns)

            x = area.left + column * cell_width + gap
            y = area.top + row * cell_height + gap
            width = max(100, cell_width - gap * 2)
            height = max(100, cell_height - gap * 2)

            result[original_index] = WindowRect(
                x=x,
                y=y,
                width=width,
                height=height,
            )

    if any(rect is None for rect in result):
        raise RuntimeError("Failed to compute positions for all windows.")

    return [rect for rect in result if rect is not None]
