"""Shared geometry builders for DWG extraction backends."""

from __future__ import annotations

import math
from typing import Iterable

from shapely.geometry import LineString


def buffered_linestring(
    points: Iterable[tuple[float, float]],
    *,
    width_mm: float,
) -> list[tuple[float, float]] | None:
    line = LineString(list(points))
    if line.is_empty or line.length <= 0.0:
        return None
    polygon = line.buffer(width_mm, cap_style=2, join_style=2)
    if not polygon.is_valid:
        polygon = polygon.buffer(0)
    if polygon.geom_type == "MultiPolygon":
        polygon = max(polygon.geoms, key=lambda item: item.area, default=polygon)
    if polygon.is_empty or polygon.area <= 0.0:
        return None
    return [(float(x), float(y)) for x, y in polygon.exterior.coords[:-1]]


def buffered_arc(
    *,
    center_x: float,
    center_y: float,
    radius: float,
    start_angle_rad: float,
    end_angle_rad: float,
    width_mm: float,
    chord_error_mm: float,
) -> list[tuple[float, float]] | None:
    if radius <= 0.0:
        return None
    end = end_angle_rad
    if end <= start_angle_rad:
        end += 2.0 * math.pi
    arc_len = abs(end - start_angle_rad) * radius
    steps = max(8, int(math.ceil(arc_len / max(chord_error_mm, 1.0))))
    points = [
        (
            center_x + radius * math.cos(start_angle_rad + (end - start_angle_rad) * step / steps),
            center_y + radius * math.sin(start_angle_rad + (end - start_angle_rad) * step / steps),
        )
        for step in range(steps + 1)
    ]
    return buffered_linestring(points, width_mm=width_mm)
