"""Effects and color control panel with palettes, velocity, symmetry, mirrors,
brush selection, 3D projection, and post-processing."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QLabel, QCheckBox, QSlider, QPushButton, QColorDialog,
    QDoubleSpinBox, QComboBox, QSpinBox, QScrollArea,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor

from effects.color import ColorConfig
from effects.postprocess import EffectsConfig
from effects.palettes import palette_names, get_palette
from effects.brushes import BRUSH_TYPES
from core.projection import Projection3DConfig
from core.pendulum import PendulumParams


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
    def color(self): return self._color
    @color.setter
    def color(self, c):
        self._color = c
        self._update_style()

    def _update_style(self):
        self.setStyleSheet(f"background-color: {self._color.name()}; "
                           f"border: 1px solid #6a6a9c; border-radius: 3px;")

    def _pick_color(self):
        c = QColorDialog.getColor(self._color, self, "Choose Color")
        if c.isValid():
            self._color = c
            self._update_style()
            self.color_changed.emit(c)


class EffectsPanel(QWidget):
    """Panel for all visual settings — colors, drawing, and post-processing."""

    color_changed = pyqtSignal(object)
    effects_changed = pyqtSignal(object)
    projection_changed = pyqtSignal(object)  # Projection3DConfig

    def __init__(self, color_config=None, effects_config=None, parent=None):
        super().__init__(parent)
        if color_config is None: color_config = ColorConfig()
        if effects_config is None: effects_config = EffectsConfig()
        self._building = True

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
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
        self._build_drawing_group(layout, color_config)
        self._build_3d_group(layout)
        self._build_effects_group(layout, effects_config)

        layout.addStretch()
        scroll.setWidget(inner)
        outer.addWidget(scroll)
        self._building = False

    def _build_palette_group(self, layout, cc):
        g = QGroupBox("Color Palette")
        gl = QVBoxLayout(g)
        row = QHBoxLayout()
        row.addWidget(QLabel("Palette"))
        self.palette_combo = QComboBox()
        self.palette_combo.addItem("Custom")
        for name in palette_names():
            self.palette_combo.addItem(name)
        if cc.palette_name:
            idx = self.palette_combo.findText(cc.palette_name)
            if idx >= 0: self.palette_combo.setCurrentIndex(idx)
        self.palette_combo.currentTextChanged.connect(self._on_palette_change)
        row.addWidget(self.palette_combo, stretch=1)
        gl.addLayout(row)
        layout.addWidget(g)

    def _build_color_group(self, layout, cc):
        g = QGroupBox("Colors")
        gl = QVBoxLayout(g)

        for label_text, attr in [("Line Color", "line_color_btn"), ("Background", "bg_color_btn")]:
            row = QHBoxLayout()
            row.addWidget(QLabel(label_text))
            btn = ColorButton(getattr(cc, "line_color" if "Line" in label_text else "bg_color"))
            btn.color_changed.connect(self._on_color_change)
            setattr(self, attr, btn)
            row.addWidget(btn); row.addStretch()
            gl.addLayout(row)

        self.gradient_check = QCheckBox("Use gradient")
        self.gradient_check.setChecked(cc.use_gradient)
        self.gradient_check.toggled.connect(self._on_color_change)
        gl.addWidget(self.gradient_check)

        row = QHBoxLayout()
        row.addWidget(QLabel("Mode"))
        self.interp_combo = QComboBox()
        self.interp_combo.addItems(["rgb", "hsv"])
        self.interp_combo.setCurrentText(cc.interpolation)
        self.interp_combo.currentTextChanged.connect(self._on_color_change)
        row.addWidget(self.interp_combo); row.addStretch()
        gl.addLayout(row)

        row = QHBoxLayout()
        row.addWidget(QLabel("Start"))
        self.grad_start_btn = ColorButton(cc.gradient_start)
        self.grad_start_btn.color_changed.connect(self._on_color_change)
        row.addWidget(self.grad_start_btn)
        row.addWidget(QLabel("End"))
        self.grad_end_btn = ColorButton(cc.gradient_end)
        self.grad_end_btn.color_changed.connect(self._on_color_change)
        row.addWidget(self.grad_end_btn); row.addStretch()
        gl.addLayout(row)

        self.mid_color_check = QCheckBox("Mid color")
        self.mid_color_check.setChecked(cc.use_mid_color)
        self.mid_color_check.toggled.connect(self._on_color_change)
        row = QHBoxLayout()
        row.addWidget(self.mid_color_check)
        self.grad_mid_btn = ColorButton(cc.gradient_mid)
        self.grad_mid_btn.color_changed.connect(self._on_color_change)
        row.addWidget(self.grad_mid_btn); row.addStretch()
        gl.addLayout(row)

        for label_text, widget_name, range_args, val in [
            ("Opacity", "alpha_slider", (10, 255), cc.line_alpha),
        ]:
            row = QHBoxLayout()
            row.addWidget(QLabel(label_text))
            s = QSlider(Qt.Orientation.Horizontal)
            s.setRange(*range_args); s.setValue(val)
            s.valueChanged.connect(self._on_color_change)
            setattr(self, widget_name, s)
            row.addWidget(s)
            gl.addLayout(row)

        row = QHBoxLayout()
        row.addWidget(QLabel("Line Width"))
        self.line_width_spin = QDoubleSpinBox()
        self.line_width_spin.setRange(0.1, 10.0)
        self.line_width_spin.setSingleStep(0.5)
        self.line_width_spin.setDecimals(1)
        self.line_width_spin.setValue(cc.line_width)
        self.line_width_spin.valueChanged.connect(self._on_color_change)
        row.addWidget(self.line_width_spin); row.addStretch()
        gl.addLayout(row)

        layout.addWidget(g)

    def _build_drawing_group(self, layout, cc):
        g = QGroupBox("Drawing Style")
        gl = QVBoxLayout(g)

        # Brush type
        row = QHBoxLayout()
        row.addWidget(QLabel("Brush"))
        self.brush_combo = QComboBox()
        self.brush_combo.addItems(BRUSH_TYPES)
        self.brush_combo.setCurrentText(cc.brush_type)
        self.brush_combo.currentTextChanged.connect(self._on_color_change)
        row.addWidget(self.brush_combo); row.addStretch()
        gl.addLayout(row)

        # Velocity
        self.vel_width_check = QCheckBox("Velocity width")
        self.vel_width_check.setChecked(cc.velocity_width)
        self.vel_width_check.toggled.connect(self._on_color_change)
        gl.addWidget(self.vel_width_check)

        row = QHBoxLayout()
        row.addWidget(QLabel("  Min"))
        self.vel_width_min = QDoubleSpinBox()
        self.vel_width_min.setRange(0.1, 5.0); self.vel_width_min.setSingleStep(0.5)
        self.vel_width_min.setDecimals(1)
        self.vel_width_min.setValue(cc.velocity_width_min)
        self.vel_width_min.valueChanged.connect(self._on_color_change)
        row.addWidget(self.vel_width_min)
        row.addWidget(QLabel("Max"))
        self.vel_width_max = QDoubleSpinBox()
        self.vel_width_max.setRange(0.5, 15.0); self.vel_width_max.setSingleStep(0.5)
        self.vel_width_max.setDecimals(1)
        self.vel_width_max.setValue(cc.velocity_width_max)
        self.vel_width_max.valueChanged.connect(self._on_color_change)
        row.addWidget(self.vel_width_max); row.addStretch()
        gl.addLayout(row)

        self.vel_opacity_check = QCheckBox("Velocity opacity")
        self.vel_opacity_check.setChecked(cc.velocity_opacity)
        self.vel_opacity_check.toggled.connect(self._on_color_change)
        gl.addWidget(self.vel_opacity_check)

        # Symmetry
        row = QHBoxLayout()
        row.addWidget(QLabel("Symmetry"))
        self.symmetry_spin = QSpinBox()
        self.symmetry_spin.setRange(1, 12)
        self.symmetry_spin.setValue(cc.symmetry_order)
        self.symmetry_spin.setSpecialValueText("None")
        self.symmetry_spin.valueChanged.connect(self._on_color_change)
        row.addWidget(self.symmetry_spin); row.addStretch()
        gl.addLayout(row)

        # Mirrors
        row = QHBoxLayout()
        self.mirror_h_check = QCheckBox("Mirror H")
        self.mirror_h_check.setChecked(cc.mirror_horizontal)
        self.mirror_h_check.toggled.connect(self._on_color_change)
        row.addWidget(self.mirror_h_check)
        self.mirror_v_check = QCheckBox("Mirror V")
        self.mirror_v_check.setChecked(cc.mirror_vertical)
        self.mirror_v_check.toggled.connect(self._on_color_change)
        row.addWidget(self.mirror_v_check)
        row.addStretch()
        gl.addLayout(row)

        layout.addWidget(g)

    def _build_3d_group(self, layout):
        g = QGroupBox("3D Projection")
        gl = QVBoxLayout(g)

        self.enable_3d = QCheckBox("Enable 3D depth")
        self.enable_3d.toggled.connect(self._on_3d_change)
        gl.addWidget(self.enable_3d)

        row = QHBoxLayout()
        row.addWidget(QLabel("Focal length"))
        self.focal_spin = QDoubleSpinBox()
        self.focal_spin.setRange(0.5, 20.0); self.focal_spin.setValue(3.0)
        self.focal_spin.setSingleStep(0.5)
        self.focal_spin.valueChanged.connect(self._on_3d_change)
        row.addWidget(self.focal_spin); row.addStretch()
        gl.addLayout(row)

        row = QHBoxLayout()
        row.addWidget(QLabel("Rotate X"))
        self.rot_x_slider = QSlider(Qt.Orientation.Horizontal)
        self.rot_x_slider.setRange(-314, 314)
        self.rot_x_slider.setValue(0)
        self.rot_x_slider.valueChanged.connect(self._on_3d_change)
        row.addWidget(self.rot_x_slider)
        gl.addLayout(row)

        row = QHBoxLayout()
        row.addWidget(QLabel("Rotate Y"))
        self.rot_y_slider = QSlider(Qt.Orientation.Horizontal)
        self.rot_y_slider.setRange(-314, 314)
        self.rot_y_slider.setValue(0)
        self.rot_y_slider.valueChanged.connect(self._on_3d_change)
        row.addWidget(self.rot_y_slider)
        gl.addLayout(row)

        self.auto_rotate_check = QCheckBox("Auto-rotate")
        self.auto_rotate_check.toggled.connect(self._on_3d_change)
        gl.addWidget(self.auto_rotate_check)

        layout.addWidget(g)

    def _build_effects_group(self, layout, ec):
        g = QGroupBox("Post-Processing")
        gl = QVBoxLayout(g)

        self.invert_check = QCheckBox("Invert")
        self.invert_check.setChecked(ec.invert)
        self.invert_check.toggled.connect(self._on_effects_change)
        gl.addWidget(self.invert_check)

        self.solarize_check = QCheckBox("Solarize")
        self.solarize_check.setChecked(ec.solarize)
        self.solarize_check.toggled.connect(self._on_effects_change)
        gl.addWidget(self.solarize_check)

        row = QHBoxLayout()
        row.addWidget(QLabel("  Threshold"))
        self.solar_thresh = QSlider(Qt.Orientation.Horizontal)
        self.solar_thresh.setRange(0, 255); self.solar_thresh.setValue(ec.solarize_threshold)
        self.solar_thresh.valueChanged.connect(self._on_effects_change)
        row.addWidget(self.solar_thresh)
        gl.addLayout(row)

        self.bloom_check = QCheckBox("Bloom / Glow")
        self.bloom_check.setChecked(ec.bloom)
        self.bloom_check.toggled.connect(self._on_effects_change)
        gl.addWidget(self.bloom_check)

        for label, attr, rng, val in [
            ("  Radius", "bloom_radius", (1, 20), ec.bloom_radius),
            ("  Intensity", "bloom_intensity", (0, 100), int(ec.bloom_intensity * 100)),
        ]:
            row = QHBoxLayout()
            row.addWidget(QLabel(label))
            s = QSlider(Qt.Orientation.Horizontal); s.setRange(*rng); s.setValue(val)
            s.valueChanged.connect(self._on_effects_change)
            setattr(self, attr, s)
            row.addWidget(s)
            gl.addLayout(row)

        row = QHBoxLayout()
        row.addWidget(QLabel("  HDR Layers"))
        self.bloom_layers = QSpinBox(); self.bloom_layers.setRange(1, 3)
        self.bloom_layers.setValue(ec.bloom_layers)
        self.bloom_layers.valueChanged.connect(self._on_effects_change)
        row.addWidget(self.bloom_layers); row.addStretch()
        gl.addLayout(row)

        self.vignette_check = QCheckBox("Vignette")
        self.vignette_check.setChecked(ec.vignette)
        self.vignette_check.toggled.connect(self._on_effects_change)
        gl.addWidget(self.vignette_check)

        row = QHBoxLayout()
        row.addWidget(QLabel("  Strength"))
        self.vignette_strength = QSlider(Qt.Orientation.Horizontal)
        self.vignette_strength.setRange(0, 100)
        self.vignette_strength.setValue(int(ec.vignette_strength * 100))
        self.vignette_strength.valueChanged.connect(self._on_effects_change)
        row.addWidget(self.vignette_strength)
        gl.addLayout(row)

        layout.addWidget(g)

    # --- Getters ---
    def get_color_config(self):
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
            mirror_horizontal=self.mirror_h_check.isChecked(),
            mirror_vertical=self.mirror_v_check.isChecked(),
            brush_type=self.brush_combo.currentText(),
            palette_name=self.palette_combo.currentText()
            if self.palette_combo.currentText() != "Custom" else "",
        )

    def get_effects_config(self):
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

    def get_projection_config(self):
        return Projection3DConfig(
            enabled=self.enable_3d.isChecked(),
            focal_length=self.focal_spin.value(),
            rotation_x=self.rot_x_slider.value() / 100.0,
            rotation_y=self.rot_y_slider.value() / 100.0,
            auto_rotate=self.auto_rotate_check.isChecked(),
        )

    # --- Setters ---
    def set_color_config(self, cc):
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
        self.mirror_h_check.setChecked(cc.mirror_horizontal)
        self.mirror_v_check.setChecked(cc.mirror_vertical)
        self.brush_combo.setCurrentText(cc.brush_type)
        if cc.palette_name:
            idx = self.palette_combo.findText(cc.palette_name)
            if idx >= 0: self.palette_combo.setCurrentIndex(idx)
        else:
            self.palette_combo.setCurrentIndex(0)
        self._building = False

    def set_effects_config(self, ec):
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

    # --- Signals ---
    def _on_palette_change(self, name):
        if self._building or name == "Custom":
            if not self._building: self._on_color_change()
            return
        palette = get_palette(name)
        if not palette: return
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

    def _on_color_change(self, *_):
        if not self._building:
            self.color_changed.emit(self.get_color_config())

    def _on_effects_change(self, *_):
        if not self._building:
            self.effects_changed.emit(self.get_effects_config())

    def _on_3d_change(self, *_):
        if not self._building:
            self.projection_changed.emit(self.get_projection_config())
