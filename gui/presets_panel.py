"""Preset gallery with thumbnail previews."""

import json
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QGridLayout, QLabel, QPushButton,
    QScrollArea, QGroupBox,
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QPixmap, QPainter, QPen, QColor

from core.pendulum import HarmonographConfig
from core.harmonograph import HarmonographEngine
from effects.color import ColorConfig


PRESETS_DIR = Path(__file__).parent.parent / "presets"
THUMB_SIZE = 100


class PresetThumbnail(QWidget):
    """A clickable preset thumbnail with label."""

    clicked = pyqtSignal(str)  # preset name

    def __init__(self, name: str, config: HarmonographConfig,
                 color_config: ColorConfig = None, parent=None):
        super().__init__(parent)
        self.name = name
        self.config = config
        self._color = color_config or ColorConfig()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)

        self._thumb_label = QLabel()
        self._thumb_label.setFixedSize(THUMB_SIZE, THUMB_SIZE)
        self._thumb_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._thumb_label.setStyleSheet(
            "border: 1px solid #3a3a5c; border-radius: 4px;"
        )
        layout.addWidget(self._thumb_label, alignment=Qt.AlignmentFlag.AlignCenter)

        name_label = QLabel(name)
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_label.setStyleSheet("font-size: 10px; color: #a0a0c0;")
        layout.addWidget(name_label)

        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._render_thumbnail()

    def _render_thumbnail(self):
        """Generate a small preview of this preset."""
        engine = HarmonographEngine(self.config)
        x, y = engine.compute_normalized(THUMB_SIZE, THUMB_SIZE, margin=0.08)

        pixmap = QPixmap(THUMB_SIZE, THUMB_SIZE)
        pixmap.fill(self._color.bg_color)

        if len(x) >= 2:
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setCompositionMode(
                QPainter.CompositionMode.CompositionMode_Plus
            )
            color = QColor(self._color.line_color)
            color.setAlpha(140)
            pen = QPen(color, 0.7)
            painter.setPen(pen)
            # Draw every 5th point for speed, skip NaN (strobe blanking)
            import math
            step = max(1, len(x) // 2000)
            for i in range(0, len(x) - step, step):
                if math.isnan(x[i]) or math.isnan(x[i + step]):
                    continue
                painter.drawLine(
                    int(x[i]), int(y[i]),
                    int(x[i + step]), int(y[i + step]),
                )
            painter.end()

        self._thumb_label.setPixmap(pixmap)

    def mousePressEvent(self, event):
        self.clicked.emit(self.name)


class PresetsPanel(QWidget):
    """Grid of preset thumbnails."""

    preset_selected = pyqtSignal(object, str)  # (HarmonographConfig, name)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._presets = {}
        self._load_presets()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        title = QLabel("Presets")
        title.setObjectName("title")
        layout.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        grid_widget = QWidget()
        self._grid = QGridLayout(grid_widget)
        self._grid.setSpacing(8)

        col = 0
        row = 0
        for name, config in self._presets.items():
            thumb = PresetThumbnail(name, config)
            thumb.clicked.connect(self._on_preset_click)
            self._grid.addWidget(thumb, row, col)
            col += 1
            if col >= 2:
                col = 0
                row += 1

        self._grid.setRowStretch(row + 1, 1)
        scroll.setWidget(grid_widget)
        layout.addWidget(scroll)

    def _load_presets(self):
        """Load all JSON presets from the presets directory."""
        if not PRESETS_DIR.exists():
            return
        for path in sorted(PRESETS_DIR.glob("*.json")):
            try:
                data = json.loads(path.read_text())
                name = data.get("name", path.stem.replace("_", " ").title())
                config = HarmonographConfig.from_dict(data)
                self._presets[name] = config
            except (json.JSONDecodeError, KeyError, ValueError):
                continue

    def _on_preset_click(self, name: str):
        if name in self._presets:
            self.preset_selected.emit(self._presets[name], name)
