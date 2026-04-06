"""Trace color configuration, gradient mapping, and velocity-sensitive drawing."""

from dataclasses import dataclass, field
from typing import List, Tuple, Optional
from PyQt6.QtGui import QColor


@dataclass
class ColorConfig:
    """Color settings for trace rendering."""
    line_color: QColor = None
    bg_color: QColor = None
    gradient_start: QColor = None
    gradient_end: QColor = None
    gradient_mid: QColor = None
    use_gradient: bool = False
    use_mid_color: bool = False
    interpolation: str = "rgb"       # "rgb" or "hsv"
    line_alpha: int = 180            # 0-255
    line_width: float = 1.0

    # Velocity-sensitive drawing
    velocity_width: bool = False
    velocity_width_min: float = 0.3
    velocity_width_max: float = 3.0
    velocity_opacity: bool = False
    velocity_opacity_min: int = 40
    velocity_opacity_max: int = 255

    # Rotational symmetry
    symmetry_order: int = 1          # 1 = none, 2-12 = N-fold

    # Palette (empty = custom)
    palette_name: str = ""

    def __post_init__(self):
        if self.line_color is None:
            self.line_color = QColor(200, 220, 255)
        if self.bg_color is None:
            self.bg_color = QColor(5, 5, 15)
        if self.gradient_start is None:
            self.gradient_start = QColor(100, 180, 255)
        if self.gradient_end is None:
            self.gradient_end = QColor(255, 100, 200)
        if self.gradient_mid is None:
            self.gradient_mid = QColor(100, 255, 180)

    def color_at(self, t: float) -> QColor:
        """Get the trace color at normalized position t (0.0 to 1.0)."""
        if not self.use_gradient:
            c = QColor(self.line_color)
            c.setAlpha(self.line_alpha)
            return c

        if self.use_mid_color:
            return self._multi_stop_color(t)

        return self._interpolate(self.gradient_start, self.gradient_end, t)

    def _multi_stop_color(self, t: float) -> QColor:
        """3-stop gradient: start -> mid -> end."""
        if t < 0.5:
            local_t = t * 2.0
            return self._interpolate(self.gradient_start, self.gradient_mid, local_t)
        else:
            local_t = (t - 0.5) * 2.0
            return self._interpolate(self.gradient_mid, self.gradient_end, local_t)

    def _interpolate(self, c1: QColor, c2: QColor, t: float) -> QColor:
        """Interpolate between two colors using current mode."""
        t = max(0.0, min(1.0, t))
        if self.interpolation == "hsv":
            return self._interpolate_hsv(c1, c2, t)
        return self._interpolate_rgb(c1, c2, t)

    def _interpolate_rgb(self, c1: QColor, c2: QColor, t: float) -> QColor:
        r = int(c1.red() + t * (c2.red() - c1.red()))
        g = int(c1.green() + t * (c2.green() - c1.green()))
        b = int(c1.blue() + t * (c2.blue() - c1.blue()))
        return QColor(r, g, b, self.line_alpha)

    def _interpolate_hsv(self, c1: QColor, c2: QColor, t: float) -> QColor:
        """HSV interpolation via shortest hue arc."""
        h1, s1, v1 = c1.hsvHueF(), c1.hsvSaturationF(), c1.valueF()
        h2, s2, v2 = c2.hsvHueF(), c2.hsvSaturationF(), c2.valueF()

        # Handle achromatic colors (hue = -1)
        if h1 < 0:
            h1 = h2
        if h2 < 0:
            h2 = h1
        if h1 < 0 and h2 < 0:
            h1 = h2 = 0.0

        # Shortest arc interpolation
        dh = h2 - h1
        if dh > 0.5:
            h1 += 1.0
        elif dh < -0.5:
            h2 += 1.0

        h = (h1 + t * (h2 - h1)) % 1.0
        s = s1 + t * (s2 - s1)
        v = v1 + t * (v2 - v1)

        c = QColor.fromHsvF(h, max(0, min(1, s)), max(0, min(1, v)))
        c.setAlpha(self.line_alpha)
        return c

    def width_at_speed(self, normalized_speed: float) -> float:
        """Map normalized speed (0=slow, 1=fast) to line width.

        Inverse mapping: slow -> thick, fast -> thin.
        """
        if not self.velocity_width:
            return self.line_width
        inv = 1.0 - normalized_speed
        return self.velocity_width_min + inv * (self.velocity_width_max - self.velocity_width_min)

    def alpha_at_speed(self, normalized_speed: float) -> int:
        """Map normalized speed to alpha. Slow -> brighter (more alpha)."""
        if not self.velocity_opacity:
            return self.line_alpha
        inv = 1.0 - normalized_speed
        return int(self.velocity_opacity_min + inv * (self.velocity_opacity_max - self.velocity_opacity_min))

    def to_dict(self) -> dict:
        return {
            "line_color": self.line_color.name(),
            "bg_color": self.bg_color.name(),
            "gradient_start": self.gradient_start.name(),
            "gradient_end": self.gradient_end.name(),
            "gradient_mid": self.gradient_mid.name(),
            "use_gradient": self.use_gradient,
            "use_mid_color": self.use_mid_color,
            "interpolation": self.interpolation,
            "line_alpha": self.line_alpha,
            "line_width": self.line_width,
            "velocity_width": self.velocity_width,
            "velocity_width_min": self.velocity_width_min,
            "velocity_width_max": self.velocity_width_max,
            "velocity_opacity": self.velocity_opacity,
            "velocity_opacity_min": self.velocity_opacity_min,
            "velocity_opacity_max": self.velocity_opacity_max,
            "symmetry_order": self.symmetry_order,
            "palette_name": self.palette_name,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ColorConfig":
        return cls(
            line_color=QColor(d.get("line_color", "#c8dcff")),
            bg_color=QColor(d.get("bg_color", "#05050f")),
            gradient_start=QColor(d.get("gradient_start", "#64b4ff")),
            gradient_end=QColor(d.get("gradient_end", "#ff64c8")),
            gradient_mid=QColor(d.get("gradient_mid", "#64ffb4")),
            use_gradient=d.get("use_gradient", False),
            use_mid_color=d.get("use_mid_color", False),
            interpolation=d.get("interpolation", "rgb"),
            line_alpha=d.get("line_alpha", 180),
            line_width=d.get("line_width", 1.0),
            velocity_width=d.get("velocity_width", False),
            velocity_width_min=d.get("velocity_width_min", 0.3),
            velocity_width_max=d.get("velocity_width_max", 3.0),
            velocity_opacity=d.get("velocity_opacity", False),
            velocity_opacity_min=d.get("velocity_opacity_min", 40),
            velocity_opacity_max=d.get("velocity_opacity_max", 255),
            symmetry_order=d.get("symmetry_order", 1),
            palette_name=d.get("palette_name", ""),
        )
