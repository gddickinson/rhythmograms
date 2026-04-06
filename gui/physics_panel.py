"""Advanced physics controls — FM/PM, nonlinearity, strobe, and chorus."""

import math
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QDoubleSpinBox, QSpinBox, QScrollArea, QCheckBox, QSlider,
)
from PyQt6.QtCore import pyqtSignal, Qt

from gui.controls import ParamSlider


class FMPMGroup(QGroupBox):
    """FM/PM controls for a single pendulum."""
    params_changed = pyqtSignal()

    def __init__(self, title: str, parent=None):
        super().__init__(title, parent)
        layout = QVBoxLayout(self)
        layout.setSpacing(3)

        self.fm_freq = ParamSlider("FM Rate", 0.0, 5.0, 0.0, 0.01, 2)
        self.fm_depth = ParamSlider("FM Depth", 0.0, 3.0, 0.0, 0.01, 2)
        self.pm_freq = ParamSlider("PM Rate", 0.0, 5.0, 0.0, 0.01, 2)
        self.pm_depth = ParamSlider("PM Depth", 0.0, 3.14, 0.0, 0.01, 2)
        self.nonlin = ParamSlider("Nonlinear", 0.0, 2.0, 0.0, 0.01, 3)

        for s in [self.fm_freq, self.fm_depth, self.pm_freq, self.pm_depth, self.nonlin]:
            layout.addWidget(s)
            s.value_changed.connect(lambda *_: self.params_changed.emit())

    def get_values(self) -> dict:
        return {
            "fm_freq": self.fm_freq.value,
            "fm_depth": self.fm_depth.value,
            "pm_freq": self.pm_freq.value,
            "pm_depth": self.pm_depth.value,
            "nonlinearity": self.nonlin.value,
        }

    def set_values(self, fm_freq=0, fm_depth=0, pm_freq=0, pm_depth=0,
                   nonlinearity=0):
        self.fm_freq.value = fm_freq
        self.fm_depth.value = fm_depth
        self.pm_freq.value = pm_freq
        self.pm_depth.value = pm_depth
        self.nonlin.value = nonlinearity


class PhysicsPanel(QWidget):
    """Advanced physics panel — FM/PM per pendulum, strobe, and chorus."""

    params_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        layout = QVBoxLayout(inner)
        layout.setSpacing(6)

        title = QLabel("Advanced Physics")
        title.setObjectName("title")
        layout.addWidget(title)

        desc = QLabel(
            "Frequency/phase modulation, nonlinearity, strobe, and chorus.\n"
            "These extend the basic pendulum model for richer patterns."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #808098; font-size: 10px;")
        layout.addWidget(desc)

        # Per-pendulum FM/PM + nonlinearity
        labels = ["X1", "X2", "Y1", "Y2"]
        self.fm_groups = []
        for label in labels:
            g = FMPMGroup(f"{label} — Modulation")
            g.params_changed.connect(self._emit)
            self.fm_groups.append(g)
            layout.addWidget(g)

        # Strobe / light extinction
        strobe_group = QGroupBox("Light Extinction / Strobe")
        sg = QVBoxLayout(strobe_group)

        sg_desc = QLabel("Periodically blank the trace — recreates Heidersberger's strobe.")
        sg_desc.setWordWrap(True)
        sg_desc.setStyleSheet("color: #808098; font-size: 10px;")
        sg.addWidget(sg_desc)

        self.strobe_freq = ParamSlider("Strobe Hz", 0.0, 20.0, 0.0, 0.1, 1)
        self.strobe_freq.value_changed.connect(self._emit)
        sg.addWidget(self.strobe_freq)

        self.strobe_duty = ParamSlider("Duty Cycle", 0.1, 0.95, 0.5, 0.05, 2)
        self.strobe_duty.value_changed.connect(self._emit)
        sg.addWidget(self.strobe_duty)

        layout.addWidget(strobe_group)

        # Chorus
        chorus_group = QGroupBox("Multi-Trace Chorus")
        cg = QVBoxLayout(chorus_group)

        cg_desc = QLabel("Render N detuned copies for interference richness.")
        cg_desc.setWordWrap(True)
        cg_desc.setStyleSheet("color: #808098; font-size: 10px;")
        cg.addWidget(cg_desc)

        row = QHBoxLayout()
        row.addWidget(QLabel("Copies"))
        self.chorus_count = QSpinBox()
        self.chorus_count.setRange(1, 8)
        self.chorus_count.setValue(1)
        self.chorus_count.setSpecialValueText("Off")
        self.chorus_count.valueChanged.connect(self._emit)
        row.addWidget(self.chorus_count)
        row.addStretch()
        cg.addLayout(row)

        self.chorus_spread = ParamSlider("Spread", 0.005, 0.1, 0.02, 0.005, 3)
        self.chorus_spread.value_changed.connect(self._emit)
        cg.addWidget(self.chorus_spread)

        layout.addWidget(chorus_group)
        layout.addStretch()

        scroll.setWidget(inner)
        outer.addWidget(scroll)

    def get_physics_params(self) -> dict:
        """Return dict with all physics params to overlay on HarmonographConfig."""
        fm_params = [g.get_values() for g in self.fm_groups]
        return {
            "fm_params": fm_params,
            "strobe_freq": self.strobe_freq.value,
            "strobe_duty": self.strobe_duty.value,
            "chorus_count": self.chorus_count.value(),
            "chorus_spread": self.chorus_spread.value,
        }

    def set_from_config(self, config):
        """Set controls from a HarmonographConfig."""
        for i, g in enumerate(self.fm_groups):
            p = config.pendulums[i]
            g.set_values(p.fm_freq, p.fm_depth, p.pm_freq, p.pm_depth,
                         p.nonlinearity)
        self.strobe_freq.value = config.strobe_freq
        self.strobe_duty.value = config.strobe_duty
        self.chorus_count.setValue(config.chorus_count)
        self.chorus_spread.value = config.chorus_spread

    def _emit(self, *_):
        self.params_changed.emit()
