"""Gallery panel — auto-generate random rhythmograms for exploration."""

import random
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QGridLayout, QSpinBox,
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QPixmap, QPainter, QPen, QColor

from core.pendulum import HarmonographConfig
from core.harmonograph import HarmonographEngine
from effects.color import ColorConfig
from effects.palettes import PALETTES


GALLERY_THUMB_SIZE = 120


class GalleryThumbnail(QWidget):
    """A clickable auto-generated rhythmogram thumbnail."""

    clicked = pyqtSignal(object, object)  # (HarmonographConfig, ColorConfig)

    def __init__(self, config: HarmonographConfig, color_config: ColorConfig,
                 parent=None):
        super().__init__(parent)
        self.config = config
        self.color_config = color_config

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)

        self._thumb_label = QLabel()
        self._thumb_label.setFixedSize(GALLERY_THUMB_SIZE, GALLERY_THUMB_SIZE)
        self._thumb_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._thumb_label.setStyleSheet(
            "border: 1px solid #3a3a5c; border-radius: 4px;"
        )
        layout.addWidget(self._thumb_label, alignment=Qt.AlignmentFlag.AlignCenter)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._render()

    def _render(self):
        """Render a thumbnail preview."""
        engine = HarmonographEngine(self.config)
        x, y = engine.compute_normalized(GALLERY_THUMB_SIZE, GALLERY_THUMB_SIZE,
                                          margin=0.08)
        cc = self.color_config
        pixmap = QPixmap(GALLERY_THUMB_SIZE, GALLERY_THUMB_SIZE)
        pixmap.fill(cc.bg_color)

        if len(x) >= 2:
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setCompositionMode(
                QPainter.CompositionMode.CompositionMode_Plus
            )
            n = len(x)
            step = max(1, n // 2000)
            for i in range(0, n - step, step):
                t = i / max(n - 1, 1)
                color = cc.color_at(t)
                color.setAlpha(min(160, color.alpha()))
                pen = QPen(color, 0.7)
                painter.setPen(pen)
                painter.drawLine(int(x[i]), int(y[i]),
                                 int(x[i + step]), int(y[i + step]))
            painter.end()

        self._thumb_label.setPixmap(pixmap)

    def mousePressEvent(self, event):
        self.clicked.emit(self.config, self.color_config)


class GalleryPanel(QWidget):
    """Auto-generated gallery of random rhythmograms."""

    config_selected = pyqtSignal(object, object)  # (HarmonographConfig, ColorConfig)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._thumbnails = []
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(6)

        title = QLabel("Gallery")
        title.setObjectName("title")
        layout.addWidget(title)

        desc = QLabel("Auto-generate random configurations. Click to load.")
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #808098; font-size: 10px;")
        layout.addWidget(desc)

        # Controls
        row = QHBoxLayout()
        row.addWidget(QLabel("Count"))
        self.count_spin = QSpinBox()
        self.count_spin.setRange(4, 24)
        self.count_spin.setValue(12)
        row.addWidget(self.count_spin)

        self.gen_btn = QPushButton("Generate")
        self.gen_btn.setObjectName("accent")
        self.gen_btn.clicked.connect(self._generate)
        row.addWidget(self.gen_btn)
        row.addStretch()
        layout.addLayout(row)

        # Scrollable grid
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self._grid_widget = QWidget()
        self._grid = QGridLayout(self._grid_widget)
        self._grid.setSpacing(8)
        scroll.setWidget(self._grid_widget)
        layout.addWidget(scroll)

    def _generate(self):
        """Generate random configs and render thumbnails."""
        # Clear existing
        for thumb in self._thumbnails:
            thumb.setParent(None)
            thumb.deleteLater()
        self._thumbnails.clear()

        count = self.count_spin.value()
        cols = 2

        for idx in range(count):
            config = HarmonographConfig.smart_random()
            palette = random.choice(PALETTES)

            cc = ColorConfig(
                bg_color=QColor(palette.bg),
                gradient_start=QColor(palette.start),
                gradient_end=QColor(palette.end),
                use_gradient=True,
                interpolation=palette.interpolation,
                line_alpha=160,
            )
            if palette.mid:
                cc.gradient_mid = QColor(palette.mid)
                cc.use_mid_color = True

            thumb = GalleryThumbnail(config, cc)
            thumb.clicked.connect(self._on_thumb_click)
            self._thumbnails.append(thumb)
            self._grid.addWidget(thumb, idx // cols, idx % cols)

        # Add stretch at bottom
        self._grid.setRowStretch(count // cols + 1, 1)

    def _on_thumb_click(self, config, color_config):
        self.config_selected.emit(config, color_config)
