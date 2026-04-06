"""Trace color configuration and gradient mapping."""

from dataclasses import dataclass
from PyQt6.QtGui import QColor


@dataclass
class ColorConfig:
    """Color settings for trace rendering."""
    line_color: QColor = None
    bg_color: QColor = None
    gradient_start: QColor = None
    gradient_end: QColor = None
    use_gradient: bool = False
    line_alpha: int = 180       # 0-255
    line_width: float = 1.0

    def __post_init__(self):
        if self.line_color is None:
            self.line_color = QColor(200, 220, 255)
        if self.bg_color is None:
            self.bg_color = QColor(5, 5, 15)
        if self.gradient_start is None:
            self.gradient_start = QColor(100, 180, 255)
        if self.gradient_end is None:
            self.gradient_end = QColor(255, 100, 200)

    def color_at(self, t: float) -> QColor:
        """Get the trace color at normalized position t (0.0 to 1.0)."""
        if not self.use_gradient:
            c = QColor(self.line_color)
            c.setAlpha(self.line_alpha)
            return c
        r = int(self.gradient_start.red() + t * (self.gradient_end.red() - self.gradient_start.red()))
        g = int(self.gradient_start.green() + t * (self.gradient_end.green() - self.gradient_start.green()))
        b = int(self.gradient_start.blue() + t * (self.gradient_end.blue() - self.gradient_start.blue()))
        return QColor(r, g, b, self.line_alpha)

    def to_dict(self) -> dict:
        return {
            "line_color": self.line_color.name(),
            "bg_color": self.bg_color.name(),
            "gradient_start": self.gradient_start.name(),
            "gradient_end": self.gradient_end.name(),
            "use_gradient": self.use_gradient,
            "line_alpha": self.line_alpha,
            "line_width": self.line_width,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ColorConfig":
        return cls(
            line_color=QColor(d.get("line_color", "#c8dcff")),
            bg_color=QColor(d.get("bg_color", "#05050f")),
            gradient_start=QColor(d.get("gradient_start", "#64b4ff")),
            gradient_end=QColor(d.get("gradient_end", "#ff64c8")),
            use_gradient=d.get("use_gradient", False),
            line_alpha=d.get("line_alpha", 180),
            line_width=d.get("line_width", 1.0),
        )
