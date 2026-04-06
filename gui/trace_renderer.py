"""Trace rendering functions — draws points with brushes, mirrors, symmetry, and 3D."""

import math
import numpy as np
from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QPainter, QPen, QColor

from effects.color import ColorConfig
from effects.brushes import draw_segment


def draw_trace_chunk(painter: QPainter, x, y, t_start: float, t_end: float,
                     color_config: ColorConfig, speed_range: tuple,
                     canvas_w: int, canvas_h: int):
    """Draw a chunk of trace points with all visual features.

    Handles symmetry, mirrors, velocity sensitivity, and brush types.
    """
    n = len(x)
    if n < 2:
        return

    cc = color_config
    needs_velocity = cc.velocity_width or cc.velocity_opacity
    speeds = _compute_speeds(x, y, speed_range) if needs_velocity else None

    cx = canvas_w / 2.0
    cy = canvas_h / 2.0

    # Build list of transform functions for symmetry + mirrors
    transforms = _build_transforms(cc, cx, cy)

    # Check for NaN (from strobe blanking)
    import math as _math

    for transform in transforms:
        for i in range(n - 1):
            # Skip NaN segments (strobe off-periods)
            if _math.isnan(x[i]) or _math.isnan(x[i + 1]):
                continue

            t = t_start + (t_end - t_start) * (i / max(n - 1, 1))
            color = cc.color_at(t)

            if speeds is not None and i < len(speeds):
                spd = speeds[i]
                width = cc.width_at_speed(spd) if cc.velocity_width else cc.line_width
                if cc.velocity_opacity:
                    color.setAlpha(cc.alpha_at_speed(spd))
            else:
                width = cc.line_width

            x1, y1 = transform(x[i], y[i])
            x2, y2 = transform(x[i + 1], y[i + 1])

            draw_segment(painter, x1, y1, x2, y2, color, width, cc.brush_type)


def _build_transforms(cc: ColorConfig, cx: float, cy: float) -> list:
    """Build list of coordinate transform functions for symmetry and mirrors."""
    transforms = []
    sym = max(1, cc.symmetry_order)

    for rot in range(sym):
        angle = (2.0 * math.pi * rot / sym) if sym > 1 else 0.0
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)

        # Base rotation
        def make_rot(c=cos_a, s=sin_a):
            if sym <= 1:
                return lambda px, py: (px, py)
            return lambda px, py: (
                cx + (px - cx) * c - (py - cy) * s,
                cy + (px - cx) * s + (py - cy) * c,
            )

        base = make_rot()
        transforms.append(base)

        # Mirror variants
        if cc.mirror_horizontal:
            def make_mh(base_fn=base):
                return lambda px, py: _mirror_h(*base_fn(px, py), cx)
            transforms.append(make_mh())

        if cc.mirror_vertical:
            def make_mv(base_fn=base):
                return lambda px, py: _mirror_v(*base_fn(px, py), cy)
            transforms.append(make_mv())

        if cc.mirror_horizontal and cc.mirror_vertical:
            def make_mhv(base_fn=base):
                return lambda px, py: _mirror_v(*_mirror_h(*base_fn(px, py), cx), cy)
            transforms.append(make_mhv())

    return transforms


def _mirror_h(px, py, cx):
    """Mirror horizontally around center X."""
    return 2 * cx - px, py


def _mirror_v(px, py, cy):
    """Mirror vertically around center Y."""
    return px, 2 * cy - py


def _compute_speeds(x, y, speed_range):
    """Compute normalized speed (0-1) for each segment."""
    dx = np.diff(x)
    dy = np.diff(y)
    speed = np.sqrt(dx * dx + dy * dy)
    s_min, s_max = speed_range
    span = s_max - s_min
    if span < 1e-10:
        return np.zeros(len(speed))
    return np.clip((speed - s_min) / span, 0.0, 1.0)
