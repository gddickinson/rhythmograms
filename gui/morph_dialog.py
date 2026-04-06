"""Morph dialog — smoothly interpolate between two configurations over time."""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSlider, QDoubleSpinBox, QGroupBox, QComboBox,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer

from core.pendulum import HarmonographConfig
from core.morph import morph_config, morph_color_config
from effects.color import ColorConfig


class MorphDialog(QDialog):
    """Dialog for morphing between two configurations.

    The start config is the current config. The end config is set by the user
    (from a preset or random). The dialog plays the morph animation.
    """

    config_updated = pyqtSignal(object, object)  # (HarmonographConfig, ColorConfig)

    def __init__(self, start_config: HarmonographConfig,
                 start_color: ColorConfig,
                 end_config: HarmonographConfig = None,
                 end_color: ColorConfig = None,
                 parent=None):
        super().__init__(parent)
        self.setWindowTitle("Morph Between Configurations")
        self.setMinimumWidth(400)

        self._start_config = start_config
        self._start_color = start_color
        self._end_config = end_config or HarmonographConfig.smart_random()
        self._end_color = end_color or ColorConfig()
        self._t = 0.0
        self._playing = False

        self._timer = QTimer(self)
        self._timer.setInterval(50)  # 20 fps
        self._timer.timeout.connect(self._tick)

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        desc = QLabel(
            "Smoothly morph from the current configuration to a target.\n"
            "Use the slider to manually scrub, or press Play for animation."
        )
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # Target selection
        target_group = QGroupBox("Target Configuration")
        tg = QVBoxLayout(target_group)

        row = QHBoxLayout()
        self.target_btn = QPushButton("New Random Target")
        self.target_btn.clicked.connect(self._new_random_target)
        row.addWidget(self.target_btn)

        self.smart_btn = QPushButton("Smart Random")
        self.smart_btn.setObjectName("accent")
        self.smart_btn.clicked.connect(self._new_smart_target)
        row.addWidget(self.smart_btn)
        row.addStretch()
        tg.addLayout(row)
        layout.addWidget(target_group)

        # Morph controls
        ctrl_group = QGroupBox("Morph Control")
        cg = QVBoxLayout(ctrl_group)

        row = QHBoxLayout()
        row.addWidget(QLabel("Position"))
        self.morph_slider = QSlider(Qt.Orientation.Horizontal)
        self.morph_slider.setRange(0, 1000)
        self.morph_slider.setValue(0)
        self.morph_slider.valueChanged.connect(self._on_slider_change)
        row.addWidget(self.morph_slider)
        self.pos_label = QLabel("0%")
        self.pos_label.setFixedWidth(40)
        row.addWidget(self.pos_label)
        cg.addLayout(row)

        row = QHBoxLayout()
        row.addWidget(QLabel("Speed"))
        self.speed_spin = QDoubleSpinBox()
        self.speed_spin.setRange(0.1, 5.0)
        self.speed_spin.setValue(1.0)
        self.speed_spin.setSingleStep(0.1)
        row.addWidget(self.speed_spin)
        row.addStretch()
        cg.addLayout(row)

        row = QHBoxLayout()
        self.play_btn = QPushButton("Play")
        self.play_btn.setObjectName("accent")
        self.play_btn.clicked.connect(self._toggle_play)
        row.addWidget(self.play_btn)

        self.reset_btn = QPushButton("Reset")
        self.reset_btn.clicked.connect(self._reset)
        row.addWidget(self.reset_btn)

        self.bounce_btn = QPushButton("Bounce")
        self.bounce_btn.setToolTip("Play forward then backward, repeating")
        self.bounce_btn.clicked.connect(self._toggle_bounce)
        row.addWidget(self.bounce_btn)
        row.addStretch()
        cg.addLayout(row)

        layout.addWidget(ctrl_group)

        # Close
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignRight)

        self._direction = 1  # 1 = forward, -1 = backward
        self._bounce = False

    def _new_random_target(self):
        self._end_config = HarmonographConfig.random()
        self._end_color = ColorConfig()

    def _new_smart_target(self):
        self._end_config = HarmonographConfig.smart_random()
        self._end_color = ColorConfig()

    def _on_slider_change(self, value):
        self._t = value / 1000.0
        self.pos_label.setText(f"{int(self._t * 100)}%")
        self._emit_morph()

    def _emit_morph(self):
        config = morph_config(self._start_config, self._end_config, self._t)
        color = morph_color_config(self._start_color, self._end_color, self._t)
        self.config_updated.emit(config, color)

    def _toggle_play(self):
        if self._playing:
            self._playing = False
            self._timer.stop()
            self.play_btn.setText("Play")
        else:
            self._playing = True
            self._direction = 1
            self._timer.start()
            self.play_btn.setText("Pause")

    def _toggle_bounce(self):
        self._bounce = not self._bounce
        self.bounce_btn.setStyleSheet(
            "background-color: #5050a0;" if self._bounce else ""
        )
        if self._bounce and not self._playing:
            self._toggle_play()

    def _reset(self):
        self._t = 0.0
        self.morph_slider.setValue(0)
        self._emit_morph()

    def _tick(self):
        step = 0.005 * self.speed_spin.value()
        self._t += step * self._direction

        if self._t >= 1.0:
            if self._bounce:
                self._t = 1.0
                self._direction = -1
            else:
                self._t = 1.0
                self._playing = False
                self._timer.stop()
                self.play_btn.setText("Play")

        if self._t <= 0.0:
            if self._bounce:
                self._t = 0.0
                self._direction = 1
            else:
                self._t = 0.0
                self._playing = False
                self._timer.stop()
                self.play_btn.setText("Play")

        self.morph_slider.setValue(int(self._t * 1000))

    def closeEvent(self, event):
        self._timer.stop()
        super().closeEvent(event)
