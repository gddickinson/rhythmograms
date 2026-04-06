"""Pendulum parameter control panel with sliders, spinboxes, and envelope controls."""

import math
import random
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QLabel, QSlider, QDoubleSpinBox, QPushButton, QScrollArea,
    QComboBox,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer

from core.pendulum import PendulumParams, HarmonographConfig, EnvelopeConfig, ENVELOPE_MODES


class ParamSlider(QWidget):
    """A labeled slider + spinbox pair for a single parameter."""

    value_changed = pyqtSignal(float)

    def __init__(self, label: str, min_val: float, max_val: float,
                 default: float, step: float = 0.01, decimals: int = 3,
                 parent=None):
        super().__init__(parent)
        self._min = min_val
        self._max = max_val
        self._steps = 1000

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


class EnvelopeControlGroup(QGroupBox):
    """Controls for envelope modulation (energy injection modes)."""

    params_changed = pyqtSignal()

    def __init__(self, envelope: EnvelopeConfig = None, parent=None):
        super().__init__("Energy Envelope", parent)
        if envelope is None:
            envelope = EnvelopeConfig()

        layout = QVBoxLayout(self)
        layout.setSpacing(4)

        # Mode selector
        row = QHBoxLayout()
        row.addWidget(QLabel("Mode"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(ENVELOPE_MODES)
        self.mode_combo.setCurrentText(envelope.mode)
        self.mode_combo.currentTextChanged.connect(self._on_change)
        row.addWidget(self.mode_combo, stretch=1)
        layout.addLayout(row)

        # Description label
        self._desc_label = QLabel()
        self._desc_label.setWordWrap(True)
        self._desc_label.setStyleSheet("color: #808098; font-size: 10px;")
        layout.addWidget(self._desc_label)

        # Frequency
        self.freq = ParamSlider("Cycle Hz", 0.01, 1.0, envelope.frequency, 0.01, 3)
        self.freq.value_changed.connect(self._on_change)
        layout.addWidget(self.freq)

        # Strength
        self.strength = ParamSlider("Strength", 0.0, 1.0, envelope.strength, 0.01, 2)
        self.strength.value_changed.connect(self._on_change)
        layout.addWidget(self.strength)

        self._update_description()

    def get_envelope(self) -> EnvelopeConfig:
        return EnvelopeConfig(
            mode=self.mode_combo.currentText(),
            frequency=self.freq.value,
            strength=self.strength.value,
        )

    def set_envelope(self, env: EnvelopeConfig):
        self.mode_combo.setCurrentText(env.mode)
        self.freq.value = env.frequency
        self.strength.value = env.strength
        self._update_description()

    def _on_change(self, *_args):
        self._update_description()
        self.params_changed.emit()

    def _update_description(self):
        descs = {
            "none": "Standard damping — trace decays to a point",
            "breathe": "Smooth pulsing — amplitude rises and falls sinusoidally",
            "pulse": "Energy kicks — damping resets periodically, trace snaps back",
            "bounce": "Triangle bounce — symmetric expansion and contraction cycles",
        }
        self._desc_label.setText(descs.get(self.mode_combo.currentText(), ""))


class ControlPanel(QWidget):
    """Full control panel with 4 pendulum groups and envelope controls."""

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

        # Envelope controls
        self.envelope_group = EnvelopeControlGroup(config.envelope)
        self.envelope_group.params_changed.connect(self._schedule_emit)
        layout.addWidget(self.envelope_group)

        # Global buttons
        btn_row = QHBoxLayout()
        rand_all = QPushButton("Randomize All")
        rand_all.clicked.connect(self.randomize_all)
        btn_row.addStretch()
        btn_row.addWidget(rand_all)

        smart_rand = QPushButton("Smart Randomize")
        smart_rand.setObjectName("accent")
        smart_rand.setToolTip("Generate aesthetic configs with near-integer frequency ratios")
        smart_rand.clicked.connect(self.smart_randomize_all)
        btn_row.addWidget(smart_rand)
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
            pendulums=[g.get_params() for g in self.groups],
            envelope=self.envelope_group.get_envelope(),
        )

    def set_config(self, config: HarmonographConfig):
        for i, group in enumerate(self.groups):
            group.set_params(config.pendulums[i])
        self.envelope_group.set_envelope(config.envelope)

    def randomize_all(self):
        config = HarmonographConfig.random()
        self.set_config(config)
        self.config_changed.emit(config)

    def smart_randomize_all(self):
        config = HarmonographConfig.smart_random(use_advanced=True)
        self.set_config(config)
        self.config_changed.emit(config)

    def _schedule_emit(self):
        self._debounce_timer.start()

    def _emit_config(self):
        self.config_changed.emit(self.get_config())
