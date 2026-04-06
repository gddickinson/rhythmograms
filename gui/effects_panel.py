"""Effects and color control panel."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QLabel, QCheckBox, QSlider, QPushButton, QColorDialog,
    QDoubleSpinBox,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor

from effects.color import ColorConfig
from effects.postprocess import EffectsConfig


class ColorButton(QPushButton):
    """A button that shows a color and opens a picker on click."""

    color_changed = pyqtSignal(QColor)

    def __init__(self, color: QColor, parent=None):
        super().__init__(parent)
        self._color = color
        self.setFixedSize(30, 24)
        self._update_style()
        self.clicked.connect(self._pick_color)

    @property
    def color(self) -> QColor:
        return self._color

    @color.setter
    def color(self, c: QColor):
        self._color = c
        self._update_style()

    def _update_style(self):
        self.setStyleSheet(
            f"background-color: {self._color.name()}; "
            f"border: 1px solid #6a6a9c; border-radius: 3px;"
        )

    def _pick_color(self):
        c = QColorDialog.getColor(self._color, self, "Choose Color")
        if c.isValid():
            self._color = c
            self._update_style()
            self.color_changed.emit(c)


class EffectsPanel(QWidget):
    """Panel for color settings and post-processing effects."""

    color_changed = pyqtSignal(object)    # emits ColorConfig
    effects_changed = pyqtSignal(object)  # emits EffectsConfig

    def __init__(self, color_config: ColorConfig = None,
                 effects_config: EffectsConfig = None, parent=None):
        super().__init__(parent)
        if color_config is None:
            color_config = ColorConfig()
        if effects_config is None:
            effects_config = EffectsConfig()

        layout = QVBoxLayout(self)
        layout.setSpacing(6)

        title = QLabel("Visual Settings")
        title.setObjectName("title")
        layout.addWidget(title)

        # --- Color group ---
        color_group = QGroupBox("Colors")
        cg_layout = QVBoxLayout(color_group)

        # Line color
        row = QHBoxLayout()
        row.addWidget(QLabel("Line Color"))
        self.line_color_btn = ColorButton(color_config.line_color)
        self.line_color_btn.color_changed.connect(self._on_color_change)
        row.addWidget(self.line_color_btn)
        row.addStretch()
        cg_layout.addLayout(row)

        # Background color
        row = QHBoxLayout()
        row.addWidget(QLabel("Background"))
        self.bg_color_btn = ColorButton(color_config.bg_color)
        self.bg_color_btn.color_changed.connect(self._on_color_change)
        row.addWidget(self.bg_color_btn)
        row.addStretch()
        cg_layout.addLayout(row)

        # Gradient
        self.gradient_check = QCheckBox("Use gradient")
        self.gradient_check.setChecked(color_config.use_gradient)
        self.gradient_check.toggled.connect(self._on_color_change)
        cg_layout.addWidget(self.gradient_check)

        row = QHBoxLayout()
        row.addWidget(QLabel("Start"))
        self.grad_start_btn = ColorButton(color_config.gradient_start)
        self.grad_start_btn.color_changed.connect(self._on_color_change)
        row.addWidget(self.grad_start_btn)
        row.addWidget(QLabel("End"))
        self.grad_end_btn = ColorButton(color_config.gradient_end)
        self.grad_end_btn.color_changed.connect(self._on_color_change)
        row.addWidget(self.grad_end_btn)
        row.addStretch()
        cg_layout.addLayout(row)

        # Alpha
        row = QHBoxLayout()
        row.addWidget(QLabel("Opacity"))
        self.alpha_slider = QSlider(Qt.Orientation.Horizontal)
        self.alpha_slider.setRange(10, 255)
        self.alpha_slider.setValue(color_config.line_alpha)
        self.alpha_slider.valueChanged.connect(self._on_color_change)
        row.addWidget(self.alpha_slider)
        cg_layout.addLayout(row)

        # Line width
        row = QHBoxLayout()
        row.addWidget(QLabel("Line Width"))
        self.line_width_spin = QDoubleSpinBox()
        self.line_width_spin.setRange(0.3, 5.0)
        self.line_width_spin.setSingleStep(0.1)
        self.line_width_spin.setValue(color_config.line_width)
        self.line_width_spin.valueChanged.connect(self._on_color_change)
        row.addWidget(self.line_width_spin)
        row.addStretch()
        cg_layout.addLayout(row)

        layout.addWidget(color_group)

        # --- Effects group ---
        fx_group = QGroupBox("Post-Processing")
        fg_layout = QVBoxLayout(fx_group)

        self.invert_check = QCheckBox("Invert")
        self.invert_check.setChecked(effects_config.invert)
        self.invert_check.toggled.connect(self._on_effects_change)
        fg_layout.addWidget(self.invert_check)

        self.solarize_check = QCheckBox("Solarize")
        self.solarize_check.setChecked(effects_config.solarize)
        self.solarize_check.toggled.connect(self._on_effects_change)
        fg_layout.addWidget(self.solarize_check)

        row = QHBoxLayout()
        row.addWidget(QLabel("  Threshold"))
        self.solar_thresh = QSlider(Qt.Orientation.Horizontal)
        self.solar_thresh.setRange(0, 255)
        self.solar_thresh.setValue(effects_config.solarize_threshold)
        self.solar_thresh.valueChanged.connect(self._on_effects_change)
        row.addWidget(self.solar_thresh)
        fg_layout.addLayout(row)

        self.bloom_check = QCheckBox("Bloom / Glow")
        self.bloom_check.setChecked(effects_config.bloom)
        self.bloom_check.toggled.connect(self._on_effects_change)
        fg_layout.addWidget(self.bloom_check)

        row = QHBoxLayout()
        row.addWidget(QLabel("  Radius"))
        self.bloom_radius = QSlider(Qt.Orientation.Horizontal)
        self.bloom_radius.setRange(1, 20)
        self.bloom_radius.setValue(effects_config.bloom_radius)
        self.bloom_radius.valueChanged.connect(self._on_effects_change)
        row.addWidget(self.bloom_radius)
        fg_layout.addLayout(row)

        row = QHBoxLayout()
        row.addWidget(QLabel("  Intensity"))
        self.bloom_intensity = QSlider(Qt.Orientation.Horizontal)
        self.bloom_intensity.setRange(0, 100)
        self.bloom_intensity.setValue(int(effects_config.bloom_intensity * 100))
        self.bloom_intensity.valueChanged.connect(self._on_effects_change)
        row.addWidget(self.bloom_intensity)
        fg_layout.addLayout(row)

        layout.addWidget(fx_group)
        layout.addStretch()

    def get_color_config(self) -> ColorConfig:
        return ColorConfig(
            line_color=self.line_color_btn.color,
            bg_color=self.bg_color_btn.color,
            gradient_start=self.grad_start_btn.color,
            gradient_end=self.grad_end_btn.color,
            use_gradient=self.gradient_check.isChecked(),
            line_alpha=self.alpha_slider.value(),
            line_width=self.line_width_spin.value(),
        )

    def get_effects_config(self) -> EffectsConfig:
        return EffectsConfig(
            invert=self.invert_check.isChecked(),
            solarize=self.solarize_check.isChecked(),
            solarize_threshold=self.solar_thresh.value(),
            bloom=self.bloom_check.isChecked(),
            bloom_radius=self.bloom_radius.value(),
            bloom_intensity=self.bloom_intensity.value() / 100.0,
        )

    def set_color_config(self, cc: ColorConfig):
        self.line_color_btn.color = cc.line_color
        self.bg_color_btn.color = cc.bg_color
        self.grad_start_btn.color = cc.gradient_start
        self.grad_end_btn.color = cc.gradient_end
        self.gradient_check.setChecked(cc.use_gradient)
        self.alpha_slider.setValue(cc.line_alpha)
        self.line_width_spin.setValue(cc.line_width)

    def set_effects_config(self, ec: EffectsConfig):
        self.invert_check.setChecked(ec.invert)
        self.solarize_check.setChecked(ec.solarize)
        self.solar_thresh.setValue(ec.solarize_threshold)
        self.bloom_check.setChecked(ec.bloom)
        self.bloom_radius.setValue(ec.bloom_radius)
        self.bloom_intensity.setValue(int(ec.bloom_intensity * 100))

    def _on_color_change(self, *_args):
        self.color_changed.emit(self.get_color_config())

    def _on_effects_change(self, *_args):
        self.effects_changed.emit(self.get_effects_config())
