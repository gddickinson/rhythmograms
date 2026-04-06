"""Texture brush rendering — alternative drawing modes beyond simple lines."""

import random as _random
import math
from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QPainter, QPen, QColor, QBrush, QRadialGradient


BRUSH_TYPES = ["line", "dot", "airbrush", "chalk", "ribbon"]


def draw_segment(painter: QPainter, x1: float, y1: float, x2: float, y2: float,
                 color: QColor, width: float, brush_type: str):
    """Draw a single trace segment using the specified brush type."""
    if brush_type == "dot":
        _draw_dot(painter, x1, y1, x2, y2, color, width)
    elif brush_type == "airbrush":
        _draw_airbrush(painter, x1, y1, x2, y2, color, width)
    elif brush_type == "chalk":
        _draw_chalk(painter, x1, y1, x2, y2, color, width)
    elif brush_type == "ribbon":
        _draw_ribbon(painter, x1, y1, x2, y2, color, width)
    else:
        _draw_line(painter, x1, y1, x2, y2, color, width)


def _draw_line(painter, x1, y1, x2, y2, color, width):
    """Standard line segment (default)."""
    pen = QPen(color, width)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    painter.setPen(pen)
    painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))


def _draw_dot(painter, x1, y1, x2, y2, color, width):
    """Draw dots/circles at each point along the segment."""
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QBrush(color))
    radius = width * 1.5
    # Draw at midpoint of segment
    mx = (x1 + x2) / 2
    my = (y1 + y2) / 2
    painter.drawEllipse(QPointF(mx, my), radius, radius)


def _draw_airbrush(painter, x1, y1, x2, y2, color, width):
    """Soft airbrush — radial gradient circles with low opacity."""
    mx = (x1 + x2) / 2
    my = (y1 + y2) / 2
    radius = width * 4

    gradient = QRadialGradient(QPointF(mx, my), radius)
    center_color = QColor(color)
    center_color.setAlpha(min(80, color.alpha()))
    edge_color = QColor(color)
    edge_color.setAlpha(0)
    gradient.setColorAt(0, center_color)
    gradient.setColorAt(1, edge_color)

    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QBrush(gradient))
    painter.drawEllipse(QPointF(mx, my), radius, radius)


def _draw_chalk(painter, x1, y1, x2, y2, color, width):
    """Chalk/scattered dots around the line path."""
    painter.setPen(Qt.PenStyle.NoPen)
    scatter = width * 3
    count = max(2, int(width * 2))

    for _ in range(count):
        t = _random.random()
        px = x1 + t * (x2 - x1) + _random.gauss(0, scatter)
        py = y1 + t * (y2 - y1) + _random.gauss(0, scatter)
        dot_color = QColor(color)
        dot_color.setAlpha(max(10, color.alpha() // 3))
        painter.setBrush(QBrush(dot_color))
        r = width * _random.uniform(0.3, 1.0)
        painter.drawEllipse(QPointF(px, py), r, r)


def _draw_ribbon(painter, x1, y1, x2, y2, color, width):
    """Ribbon — variable-width line with perpendicular offset."""
    dx = x2 - x1
    dy = y2 - y1
    length = math.sqrt(dx * dx + dy * dy)
    if length < 0.1:
        return

    # Perpendicular direction
    nx = -dy / length
    ny = dx / length
    offset = width * 0.5

    # Draw two thinner parallel lines for a ribbon effect
    thin = max(0.5, width * 0.3)
    pen = QPen(color, thin)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    painter.setPen(pen)
    painter.drawLine(
        QPointF(x1 + nx * offset, y1 + ny * offset),
        QPointF(x2 + nx * offset, y2 + ny * offset),
    )
    inner_color = QColor(color)
    inner_color.setAlpha(max(20, color.alpha() // 2))
    pen2 = QPen(inner_color, thin)
    pen2.setCapStyle(Qt.PenCapStyle.RoundCap)
    painter.setPen(pen2)
    painter.drawLine(
        QPointF(x1 - nx * offset, y1 - ny * offset),
        QPointF(x2 - nx * offset, y2 - ny * offset),
    )
