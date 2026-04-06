"""Atmosphere effects control panel — smoke, god rays, grain, distortion, grading."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QCheckBox, QSlider, QDoubleSpinBox, QSpinBox, QScrollArea,
)
from PyQt6.QtCore import Qt, pyqtSignal

from effects.atmosphere import AtmosphereConfig


class AtmospherePanel(QWidget):
    """Controls for atmospheric post-processing effects."""

    atmosphere_changed = pyqtSignal(object)  # AtmosphereConfig

    def __init__(self, parent=None):
        super().__init__(parent)
        self._building = True

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        layout = QVBoxLayout(inner)
        layout.setSpacing(6)

        title = QLabel("Atmosphere")
        title.setObjectName("title")
        layout.addWidget(title)

        desc = QLabel("Simulate light through smoke, haze, and atmosphere.")
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #808098; font-size: 10px;")
        layout.addWidget(desc)

        self._build_smoke(layout)
        self._build_god_rays(layout)
        self._build_chromatic(layout)
        self._build_grain(layout)
        self._build_heat(layout)
        self._build_grading(layout)

        layout.addStretch()
        scroll.setWidget(inner)
        outer.addWidget(scroll)
        self._building = False

    def _slider(self, layout, label, attr, lo, hi, default, scale=100):
        row = QHBoxLayout()
        row.addWidget(QLabel(f"  {label}"))
        s = QSlider(Qt.Orientation.Horizontal)
        s.setRange(int(lo * scale), int(hi * scale))
        s.setValue(int(default * scale))
        s.valueChanged.connect(self._emit)
        setattr(self, attr, s)
        setattr(self, f"_{attr}_scale", scale)
        row.addWidget(s)
        layout.addLayout(row)

    def _build_smoke(self, layout):
        g = QGroupBox("Smoke Glow")
        gl = QVBoxLayout(g)
        self.smoke_check = QCheckBox("Enable smoke glow")
        self.smoke_check.toggled.connect(self._emit)
        gl.addWidget(self.smoke_check)
        self._slider(gl, "Intensity", "smoke_intensity", 0.1, 1.0, 0.4)
        self._slider(gl, "Scale", "smoke_scale", 2, 20, 8, scale=1)
        layout.addWidget(g)

    def _build_god_rays(self, layout):
        g = QGroupBox("God Rays")
        gl = QVBoxLayout(g)
        self.rays_check = QCheckBox("Enable god rays")
        self.rays_check.toggled.connect(self._emit)
        gl.addWidget(self.rays_check)
        self._slider(gl, "Intensity", "rays_intensity", 0.1, 1.5, 0.5)
        self._slider(gl, "Decay", "rays_decay", 0.85, 0.99, 0.95)
        layout.addWidget(g)

    def _build_chromatic(self, layout):
        g = QGroupBox("Chromatic Aberration")
        gl = QVBoxLayout(g)
        self.chroma_check = QCheckBox("Enable")
        self.chroma_check.toggled.connect(self._emit)
        gl.addWidget(self.chroma_check)
        self._slider(gl, "Strength", "chroma_strength", 0.5, 15.0, 3.0, scale=10)
        layout.addWidget(g)

    def _build_grain(self, layout):
        g = QGroupBox("Film Grain")
        gl = QVBoxLayout(g)
        self.grain_check = QCheckBox("Enable film grain")
        self.grain_check.toggled.connect(self._emit)
        gl.addWidget(self.grain_check)
        self._slider(gl, "Intensity", "grain_intensity", 0.02, 0.2, 0.08)
        self._slider(gl, "Grain size", "grain_size", 1.0, 4.0, 1.5, scale=10)
        layout.addWidget(g)

    def _build_heat(self, layout):
        g = QGroupBox("Heat Distortion")
        gl = QVBoxLayout(g)
        self.heat_check = QCheckBox("Enable heat distortion")
        self.heat_check.toggled.connect(self._emit)
        gl.addWidget(self.heat_check)
        self._slider(gl, "Amplitude", "heat_amplitude", 1.0, 15.0, 3.0, scale=10)
        self._slider(gl, "Frequency", "heat_frequency", 0.005, 0.05, 0.02, scale=1000)
        layout.addWidget(g)

    def _build_grading(self, layout):
        g = QGroupBox("Color Grading")
        gl = QVBoxLayout(g)
        self.grade_check = QCheckBox("Enable color grading")
        self.grade_check.toggled.connect(self._emit)
        gl.addWidget(self.grade_check)
        self._slider(gl, "Contrast", "grade_contrast", 0.5, 2.0, 1.0, scale=100)
        self._slider(gl, "Saturation", "grade_saturation", 0.0, 2.0, 1.0, scale=100)

        row = QHBoxLayout()
        row.addWidget(QLabel("  Shadow tint B"))
        self.shadow_b = QSlider(Qt.Orientation.Horizontal)
        self.shadow_b.setRange(0, 30); self.shadow_b.setValue(10)
        self.shadow_b.valueChanged.connect(self._emit)
        row.addWidget(self.shadow_b)
        gl.addLayout(row)

        row = QHBoxLayout()
        row.addWidget(QLabel("  Highlight tint R"))
        self.highlight_r = QSlider(Qt.Orientation.Horizontal)
        self.highlight_r.setRange(0, 30); self.highlight_r.setValue(10)
        self.highlight_r.valueChanged.connect(self._emit)
        row.addWidget(self.highlight_r)
        gl.addLayout(row)

        layout.addWidget(g)

    def _val(self, attr):
        s = getattr(self, attr)
        scale = getattr(self, f"_{attr}_scale")
        return s.value() / scale

    def get_config(self) -> AtmosphereConfig:
        return AtmosphereConfig(
            smoke_glow=self.smoke_check.isChecked(),
            smoke_intensity=self._val("smoke_intensity"),
            smoke_scale=self._val("smoke_scale"),
            god_rays=self.rays_check.isChecked(),
            god_rays_intensity=self._val("rays_intensity"),
            god_rays_decay=self._val("rays_decay"),
            chromatic_aberration=self.chroma_check.isChecked(),
            chromatic_strength=self._val("chroma_strength"),
            film_grain=self.grain_check.isChecked(),
            grain_intensity=self._val("grain_intensity"),
            grain_size=self._val("grain_size"),
            heat_distortion=self.heat_check.isChecked(),
            heat_amplitude=self._val("heat_amplitude"),
            heat_frequency=self._val("heat_frequency"),
            color_grading=self.grade_check.isChecked(),
            shadow_tint_b=self.shadow_b.value(),
            highlight_tint_r=self.highlight_r.value(),
            grade_contrast=self._val("grade_contrast"),
            grade_saturation=self._val("grade_saturation"),
        )

    def set_config(self, c: AtmosphereConfig):
        self._building = True
        self.smoke_check.setChecked(c.smoke_glow)
        self.rays_check.setChecked(c.god_rays)
        self.chroma_check.setChecked(c.chromatic_aberration)
        self.grain_check.setChecked(c.film_grain)
        self.heat_check.setChecked(c.heat_distortion)
        self.grade_check.setChecked(c.color_grading)
        self._building = False

    def _emit(self, *_):
        if not self._building:
            self.atmosphere_changed.emit(self.get_config())
