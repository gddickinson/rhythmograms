"""Effects and color control panel with enhanced visual options."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QLabel, QCheckBox, QSlider, QPushButton, QColorDialog,
    QDoubleSpinBox, QComboBox, QSpinBox, QScrollArea,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor

from effects.color import ColorConfig
from effects.postprocess import EffectsConfig
from effects.palettes import PALETTES, palette_names, get_palette


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
    """Panel for color settings, palettes, velocity, symmetry, and effects."""

    color_changed = pyqtSignal(object)    # emits ColorConfig
    effects_changed = pyqtSignal(object)  # emits EffectsConfig

    def __init__(self, color_config: ColorConfig = None,
                 effects_config: EffectsConfig = None, parent=None):
        super().__init__(parent)
        if color_config is None:
            color_config = ColorConfig()
        if effects_config is None:
            effects_config = EffectsConfig()

        self._building = True  # suppress signals during init

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        layout = QVBoxLayout(inner)
        layout.setSpacing(6)

        title = QLabel("Visual Settings")
        title.setObjectName("title")
        layout.addWidget(title)

        self._build_palette_group(layout, color_config)
        self._build_color_group(layout, color_config)
        self._build_velocity_group(layout, color_config)
        self._build_symmetry_group(layout, color_config)
        self._build_effects_group(layout, effects_config)

        layout.addStretch()
        scroll.setWidget(inner)
        outer_layout.addWidget(scroll)

        self._building = False

    def _build_palette_group(self, layout, cc):
        group = QGroupBox("Color Palette")
        g_layout = QVBoxLayout(group)

        row = QHBoxLayout()
        row.addWidget(QLabel("Palette"))
        self.palette_combo = QComboBox()
        self.palette_combo.addItem("Custom")
        for name in palette_names():
            self.palette_combo.addItem(name)
        if cc.palette_name:
            idx = self.palette_combo.findText(cc.palette_name)
            if idx >= 0:
                self.palette_combo.setCurrentIndex(idx)
        self.palette_combo.currentTextChanged.connect(self._on_palette_change)
        row.addWidget(self.palette_combo, stretch=1)
        g_layout.addLayout(row)

        layout.addWidget(group)

    def _build_color_group(self, layout, cc):
        group = QGroupBox("Colors")
        cg = QVBoxLayout(group)

        # Line color
        row = QHBoxLayout()
        row.addWidget(QLabel("Line Color"))
        self.line_color_btn = ColorButton(cc.line_color)
        self.line_color_btn.color_changed.connect(self._on_color_change)
        row.addWidget(self.line_color_btn)
        row.addStretch()
        cg.addLayout(row)

        # Background color
        row = QHBoxLayout()
        row.addWidget(QLabel("Background"))
        self.bg_color_btn = ColorButton(cc.bg_color)
        self.bg_color_btn.color_changed.connect(self._on_color_change)
        row.addWidget(self.bg_color_btn)
        row.addStretch()
        cg.addLayout(row)

        # Gradient
        self.gradient_check = QCheckBox("Use gradient")
        self.gradient_check.setChecked(cc.use_gradient)
        self.gradient_check.toggled.connect(self._on_color_change)
        cg.addWidget(self.gradient_check)

        # Interpolation mode
        row = QHBoxLayout()
        row.addWidget(QLabel("Interpolation"))
        self.interp_combo = QComboBox()
        self.interp_combo.addItems(["rgb", "hsv"])
        self.interp_combo.setCurrentText(cc.interpolation)
        self.interp_combo.currentTextChanged.connect(self._on_color_change)
        row.addWidget(self.interp_combo)
        row.addStretch()
        cg.addLayout(row)

        row = QHBoxLayout()
        row.addWidget(QLabel("Start"))
        self.grad_start_btn = ColorButton(cc.gradient_start)
        self.grad_start_btn.color_changed.connect(self._on_color_change)
        row.addWidget(self.grad_start_btn)
        row.addWidget(QLabel("End"))
        self.grad_end_btn = ColorButton(cc.gradient_end)
        self.grad_end_btn.color_changed.connect(self._on_color_change)
        row.addWidget(self.grad_end_btn)
        row.addStretch()
        cg.addLayout(row)

        # Mid color (3-stop gradient)
        self.mid_color_check = QCheckBox("Mid color")
        self.mid_color_check.setChecked(cc.use_mid_color)
        self.mid_color_check.toggled.connect(self._on_color_change)
        row = QHBoxLayout()
        row.addWidget(self.mid_color_check)
        self.grad_mid_btn = ColorButton(cc.gradient_mid)
        self.grad_mid_btn.color_changed.connect(self._on_color_change)
        row.addWidget(self.grad_mid_btn)
        row.addStretch()
        cg.addLayout(row)

        # Alpha
        row = QHBoxLayout()
        row.addWidget(QLabel("Opacity"))
        self.alpha_slider = QSlider(Qt.Orientation.Horizontal)
        self.alpha_slider.setRange(10, 255)
        self.alpha_slider.setValue(cc.line_alpha)
        self.alpha_slider.valueChanged.connect(self._on_color_change)
        row.addWidget(self.alpha_slider)
        cg.addLayout(row)

        # Line width
        row = QHBoxLayout()
        row.addWidget(QLabel("Line Width"))
        self.line_width_spin = QDoubleSpinBox()
        self.line_width_spin.setRange(0.3, 5.0)
        self.line_width_spin.setSingleStep(0.1)
        self.line_width_spin.setValue(cc.line_width)
        self.line_width_spin.valueChanged.connect(self._on_color_change)
        row.addWidget(self.line_width_spin)
        row.addStretch()
        cg.addLayout(row)

        layout.addWidget(group)

    def _build_velocity_group(self, layout, cc):
        group = QGroupBox("Velocity Sensitivity")
        vg = QVBoxLayout(group)

        self.vel_width_check = QCheckBox("Velocity-sensitive line width")
        self.vel_width_check.setChecked(cc.velocity_width)
        self.vel_width_check.toggled.connect(self._on_color_change)
        vg.addWidget(self.vel_width_check)

        row = QHBoxLayout()
        row.addWidget(QLabel("  Min width"))
        self.vel_width_min = QDoubleSpinBox()
        self.vel_width_min.setRange(0.1, 5.0)
        self.vel_width_min.setSingleStep(0.1)
        self.vel_width_min.setValue(cc.velocity_width_min)
        self.vel_width_min.valueChanged.connect(self._on_color_change)
        row.addWidget(self.vel_width_min)
        row.addWidget(QLabel("Max"))
        self.vel_width_max = QDoubleSpinBox()
        self.vel_width_max.setRange(0.5, 10.0)
        self.vel_width_max.setSingleStep(0.1)
        self.vel_width_max.setValue(cc.velocity_width_max)
        self.vel_width_max.valueChanged.connect(self._on_color_change)
        row.addWidget(self.vel_width_max)
        row.addStretch()
        vg.addLayout(row)

        self.vel_opacity_check = QCheckBox("Velocity-sensitive opacity")
        self.vel_opacity_check.setChecked(cc.velocity_opacity)
        self.vel_opacity_check.toggled.connect(self._on_color_change)
        vg.addWidget(self.vel_opacity_check)

        layout.addWidget(group)

    def _build_symmetry_group(self, layout, cc):
        group = QGroupBox("Rotational Symmetry")
        sg = QVBoxLayout(group)

        row = QHBoxLayout()
        row.addWidget(QLabel("Fold order"))
        self.symmetry_spin = QSpinBox()
        self.symmetry_spin.setRange(1, 12)
        self.symmetry_spin.setValue(cc.symmetry_order)
        self.symmetry_spin.setSpecialValueText("None")
        self.symmetry_spin.valueChanged.connect(self._on_color_change)
        row.addWidget(self.symmetry_spin)
        row.addStretch()
        sg.addLayout(row)

        layout.addWidget(group)

    def _build_effects_group(self, layout, ec):
        group = QGroupBox("Post-Processing")
        fg = QVBoxLayout(group)

        self.invert_check = QCheckBox("Invert")
        self.invert_check.setChecked(ec.invert)
        self.invert_check.toggled.connect(self._on_effects_change)
        fg.addWidget(self.invert_check)

        self.solarize_check = QCheckBox("Solarize")
        self.solarize_check.setChecked(ec.solarize)
        self.solarize_check.toggled.connect(self._on_effects_change)
        fg.addWidget(self.solarize_check)

        row = QHBoxLayout()
        row.addWidget(QLabel("  Threshold"))
        self.solar_thresh = QSlider(Qt.Orientation.Horizontal)
        self.solar_thresh.setRange(0, 255)
        self.solar_thresh.setValue(ec.solarize_threshold)
        self.solar_thresh.valueChanged.connect(self._on_effects_change)
        row.addWidget(self.solar_thresh)
        fg.addLayout(row)

        self.bloom_check = QCheckBox("Bloom / Glow")
        self.bloom_check.setChecked(ec.bloom)
        self.bloom_check.toggled.connect(self._on_effects_change)
        fg.addWidget(self.bloom_check)

        row = QHBoxLayout()
        row.addWidget(QLabel("  Radius"))
        self.bloom_radius = QSlider(Qt.Orientation.Horizontal)
        self.bloom_radius.setRange(1, 20)
        self.bloom_radius.setValue(ec.bloom_radius)
        self.bloom_radius.valueChanged.connect(self._on_effects_change)
        row.addWidget(self.bloom_radius)
        fg.addLayout(row)

        row = QHBoxLayout()
        row.addWidget(QLabel("  Intensity"))
        self.bloom_intensity = QSlider(Qt.Orientation.Horizontal)
        self.bloom_intensity.setRange(0, 100)
        self.bloom_intensity.setValue(int(ec.bloom_intensity * 100))
        self.bloom_intensity.valueChanged.connect(self._on_effects_change)
        row.addWidget(self.bloom_intensity)
        fg.addLayout(row)

        row = QHBoxLayout()
        row.addWidget(QLabel("  HDR Layers"))
        self.bloom_layers = QSpinBox()
        self.bloom_layers.setRange(1, 3)
        self.bloom_layers.setValue(ec.bloom_layers)
        self.bloom_layers.valueChanged.connect(self._on_effects_change)
        row.addWidget(self.bloom_layers)
        row.addStretch()
        fg.addLayout(row)

        # Vignette
        self.vignette_check = QCheckBox("Vignette")
        self.vignette_check.setChecked(ec.vignette)
        self.vignette_check.toggled.connect(self._on_effects_change)
        fg.addWidget(self.vignette_check)

        row = QHBoxLayout()
        row.addWidget(QLabel("  Strength"))
        self.vignette_strength = QSlider(Qt.Orientation.Horizontal)
        self.vignette_strength.setRange(0, 100)
        self.vignette_strength.setValue(int(ec.vignette_strength * 100))
        self.vignette_strength.valueChanged.connect(self._on_effects_change)
        row.addWidget(self.vignette_strength)
        fg.addLayout(row)

        layout.addWidget(group)

    # --- Public getters/setters ---

    def get_color_config(self) -> ColorConfig:
        return ColorConfig(
            line_color=self.line_color_btn.color,
            bg_color=self.bg_color_btn.color,
            gradient_start=self.grad_start_btn.color,
            gradient_end=self.grad_end_btn.color,
            gradient_mid=self.grad_mid_btn.color,
            use_gradient=self.gradient_check.isChecked(),
            use_mid_color=self.mid_color_check.isChecked(),
            interpolation=self.interp_combo.currentText(),
            line_alpha=self.alpha_slider.value(),
            line_width=self.line_width_spin.value(),
            velocity_width=self.vel_width_check.isChecked(),
            velocity_width_min=self.vel_width_min.value(),
            velocity_width_max=self.vel_width_max.value(),
            velocity_opacity=self.vel_opacity_check.isChecked(),
            symmetry_order=self.symmetry_spin.value(),
            palette_name=self.palette_combo.currentText()
            if self.palette_combo.currentText() != "Custom" else "",
        )

    def get_effects_config(self) -> EffectsConfig:
        return EffectsConfig(
            invert=self.invert_check.isChecked(),
            solarize=self.solarize_check.isChecked(),
            solarize_threshold=self.solar_thresh.value(),
            bloom=self.bloom_check.isChecked(),
            bloom_radius=self.bloom_radius.value(),
            bloom_intensity=self.bloom_intensity.value() / 100.0,
            bloom_layers=self.bloom_layers.value(),
            vignette=self.vignette_check.isChecked(),
            vignette_strength=self.vignette_strength.value() / 100.0,
        )

    def set_color_config(self, cc: ColorConfig):
        self._building = True
        self.line_color_btn.color = cc.line_color
        self.bg_color_btn.color = cc.bg_color
        self.grad_start_btn.color = cc.gradient_start
        self.grad_end_btn.color = cc.gradient_end
        self.grad_mid_btn.color = cc.gradient_mid
        self.gradient_check.setChecked(cc.use_gradient)
        self.mid_color_check.setChecked(cc.use_mid_color)
        self.interp_combo.setCurrentText(cc.interpolation)
        self.alpha_slider.setValue(cc.line_alpha)
        self.line_width_spin.setValue(cc.line_width)
        self.vel_width_check.setChecked(cc.velocity_width)
        self.vel_width_min.setValue(cc.velocity_width_min)
        self.vel_width_max.setValue(cc.velocity_width_max)
        self.vel_opacity_check.setChecked(cc.velocity_opacity)
        self.symmetry_spin.setValue(cc.symmetry_order)
        if cc.palette_name:
            idx = self.palette_combo.findText(cc.palette_name)
            if idx >= 0:
                self.palette_combo.setCurrentIndex(idx)
        else:
            self.palette_combo.setCurrentIndex(0)
        self._building = False

    def set_effects_config(self, ec: EffectsConfig):
        self._building = True
        self.invert_check.setChecked(ec.invert)
        self.solarize_check.setChecked(ec.solarize)
        self.solar_thresh.setValue(ec.solarize_threshold)
        self.bloom_check.setChecked(ec.bloom)
        self.bloom_radius.setValue(ec.bloom_radius)
        self.bloom_intensity.setValue(int(ec.bloom_intensity * 100))
        self.bloom_layers.setValue(ec.bloom_layers)
        self.vignette_check.setChecked(ec.vignette)
        self.vignette_strength.setValue(int(ec.vignette_strength * 100))
        self._building = False

    # --- Palette handling ---

    def _on_palette_change(self, name: str):
        if self._building or name == "Custom":
            if not self._building:
                self._on_color_change()
            return
        palette = get_palette(name)
        if not palette:
            return
        self._building = True
        self.bg_color_btn.color = QColor(palette.bg)
        self.grad_start_btn.color = QColor(palette.start)
        self.grad_end_btn.color = QColor(palette.end)
        self.gradient_check.setChecked(True)
        self.interp_combo.setCurrentText(palette.interpolation)
        if palette.mid:
            self.grad_mid_btn.color = QColor(palette.mid)
            self.mid_color_check.setChecked(True)
        else:
            self.mid_color_check.setChecked(False)
        self._building = False
        self._on_color_change()

    def _on_color_change(self, *_args):
        if not self._building:
            self.color_changed.emit(self.get_color_config())

    def _on_effects_change(self, *_args):
        if not self._building:
            self.effects_changed.emit(self.get_effects_config())
