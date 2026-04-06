"""Pendulum parameter control panel with sliders and spinboxes."""

import math
import random
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QLabel, QSlider, QDoubleSpinBox, QPushButton, QScrollArea,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer

from core.pendulum import PendulumParams, HarmonographConfig


class ParamSlider(QWidget):
    """A labeled slider + spinbox pair for a single parameter."""

    value_changed = pyqtSignal(float)

    def __init__(self, label: str, min_val: float, max_val: float,
                 default: float, step: float = 0.01, decimals: int = 3,
                 parent=None):
        super().__init__(parent)
        self._min = min_val
        self._max = max_val
        self._steps = 1000  # slider resolution

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)

        lbl = QLabel(label)
        lbl.setFixedWidth(75)
        layout.addWidget(lbl)

        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._slider.setRange(0, self._steps)
        self._slider.setValue(self._val_to_slider(default))
        layout.addWidget(self._slider, stretch=1)

        self._spin = QDoubleSpinBox()
        self._spin.setRange(min_val, max_val)
        self._spin.setSingleStep(step)
        self._spin.setDecimals(decimals)
        self._spin.setValue(default)
        layout.addWidget(self._spin)

        self._updating = False
        self._slider.valueChanged.connect(self._slider_changed)
        self._spin.valueChanged.connect(self._spin_changed)

    @property
    def value(self) -> float:
        return self._spin.value()

    @value.setter
    def value(self, v: float):
        self._updating = True
        self._spin.setValue(v)
        self._slider.setValue(self._val_to_slider(v))
        self._updating = False

    def _val_to_slider(self, v: float) -> int:
        t = (v - self._min) / (self._max - self._min)
        return int(t * self._steps)

    def _slider_to_val(self, s: int) -> float:
        return self._min + (s / self._steps) * (self._max - self._min)

    def _slider_changed(self, pos):
        if self._updating:
            return
        self._updating = True
        val = self._slider_to_val(pos)
        self._spin.setValue(val)
        self._updating = False
        self.value_changed.emit(val)

    def _spin_changed(self, val):
        if self._updating:
            return
        self._updating = True
        self._slider.setValue(self._val_to_slider(val))
        self._updating = False
        self.value_changed.emit(val)


class PendulumControlGroup(QGroupBox):
    """Controls for a single pendulum (frequency, phase, amplitude, damping)."""

    params_changed = pyqtSignal()

    def __init__(self, title: str, params: PendulumParams = None, parent=None):
        super().__init__(title, parent)
        if params is None:
            params = PendulumParams()

        layout = QVBoxLayout(self)
        layout.setSpacing(4)

        self.freq = ParamSlider("Frequency", 0.1, 12.0, params.frequency, 0.01, 3)
        self.phase = ParamSlider("Phase", 0.0, 2 * math.pi, params.phase, 0.01, 3)
        self.amp = ParamSlider("Amplitude", 0.0, 1.0, params.amplitude, 0.01, 3)
        self.damping = ParamSlider("Damping", 0.0, 0.15, params.damping, 0.001, 4)

        for slider in [self.freq, self.phase, self.amp, self.damping]:
            layout.addWidget(slider)
            slider.value_changed.connect(self._on_change)

        btn_row = QHBoxLayout()
        rand_btn = QPushButton("Randomize")
        rand_btn.clicked.connect(self.randomize)
        btn_row.addStretch()
        btn_row.addWidget(rand_btn)
        layout.addLayout(btn_row)

    def get_params(self) -> PendulumParams:
        return PendulumParams(
            frequency=self.freq.value,
            phase=self.phase.value,
            amplitude=self.amp.value,
            damping=self.damping.value,
        )

    def set_params(self, p: PendulumParams):
        self.freq.value = p.frequency
        self.phase.value = p.phase
        self.amp.value = p.amplitude
        self.damping.value = p.damping

    def randomize(self):
        self.set_params(PendulumParams.random())
        self.params_changed.emit()

    def _on_change(self, _val):
        self.params_changed.emit()


class ControlPanel(QWidget):
    """Full control panel with 4 pendulum groups."""

    config_changed = pyqtSignal(object)  # emits HarmonographConfig

    DEBOUNCE_MS = 50

    def __init__(self, config: HarmonographConfig = None, parent=None):
        super().__init__(parent)
        if config is None:
            config = HarmonographConfig()

        self._debounce_timer = QTimer(self)
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.setInterval(self.DEBOUNCE_MS)
        self._debounce_timer.timeout.connect(self._emit_config)

        layout = QVBoxLayout()
        layout.setSpacing(6)

        title = QLabel("Pendulum Parameters")
        title.setObjectName("title")
        layout.addWidget(title)

        labels = ["X1 (Pendulum 1)", "X2 (Pendulum 2)",
                  "Y1 (Pendulum 3)", "Y2 (Pendulum 4)"]

        self.groups = []
        for i, label in enumerate(labels):
            group = PendulumControlGroup(label, config.pendulums[i])
            group.params_changed.connect(self._schedule_emit)
            self.groups.append(group)
            layout.addWidget(group)

        # Global buttons
        btn_row = QHBoxLayout()
        rand_all = QPushButton("Randomize All")
        rand_all.setObjectName("accent")
        rand_all.clicked.connect(self.randomize_all)
        btn_row.addStretch()
        btn_row.addWidget(rand_all)
        layout.addLayout(btn_row)

        layout.addStretch()

        # Wrap in scroll area
        inner = QWidget()
        inner.setLayout(layout)
        scroll = QScrollArea()
        scroll.setWidget(inner)
        scroll.setWidgetResizable(True)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    def get_config(self) -> HarmonographConfig:
        return HarmonographConfig(
            pendulums=[g.get_params() for g in self.groups]
        )

    def set_config(self, config: HarmonographConfig):
        for i, group in enumerate(self.groups):
            group.set_params(config.pendulums[i])

    def randomize_all(self):
        config = HarmonographConfig.random()
        self.set_config(config)
        self.config_changed.emit(config)

    def _schedule_emit(self):
        self._debounce_timer.start()

    def _emit_config(self):
        self.config_changed.emit(self.get_config())
