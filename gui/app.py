"""Main application window: layout, signal wiring, and coordination."""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QSplitter, QFileDialog, QStatusBar, QTabWidget, QApplication,
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QKeySequence, QShortcut

from core.pendulum import HarmonographConfig
from effects.color import ColorConfig
from effects.postprocess import EffectsConfig, apply_effects
from gui.canvas import RhythmogramCanvas
from gui.controls import ControlPanel
from gui.effects_panel import EffectsPanel
from gui.toolbar import Toolbar
from gui.presets_panel import PresetsPanel
from gui.style import DARK_THEME
from utils.config import save_config, load_config


class MainWindow(QMainWindow):
    """Main application window for the Rhythmogram Simulator."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Heidersberger Rhythmogram Simulator")
        self.setMinimumSize(QSize(1100, 700))
        self.setStyleSheet(DARK_THEME)

        self._config = HarmonographConfig()
        self._color_config = ColorConfig()
        self._effects_config = EffectsConfig()

        self._build_ui()
        self._connect_signals()

        # Start with default configuration
        self.canvas.set_color_config(self._color_config)
        self.canvas.set_config(self._config)

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Toolbar
        self.toolbar = Toolbar()
        main_layout.addWidget(self.toolbar)

        # Main splitter: canvas | controls
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Canvas (left, larger)
        self.canvas = RhythmogramCanvas()
        splitter.addWidget(self.canvas)

        # Right panel with tabs
        right_panel = QTabWidget()
        right_panel.setMaximumWidth(380)
        right_panel.setMinimumWidth(300)

        self.controls = ControlPanel(self._config)
        right_panel.addTab(self.controls, "Pendulums")

        self.effects_panel = EffectsPanel(self._color_config, self._effects_config)
        right_panel.addTab(self.effects_panel, "Visual")

        self.presets_panel = PresetsPanel()
        right_panel.addTab(self.presets_panel, "Presets")

        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)

        main_layout.addWidget(splitter)

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

        # Keyboard shortcuts
        QShortcut(QKeySequence("Space"), self, self.canvas.toggle_play_pause)
        QShortcut(QKeySequence("R"), self, self._on_reset)
        QShortcut(QKeySequence("Ctrl+S"), self, self._on_save)
        QShortcut(QKeySequence("Ctrl+O"), self, self._on_load)
        QShortcut(QKeySequence("Ctrl+E"), self, self._on_export_png)

    def _connect_signals(self):
        # Controls -> canvas
        self.controls.config_changed.connect(self._on_config_change)

        # Effects panel
        self.effects_panel.color_changed.connect(self._on_color_change)
        self.effects_panel.effects_changed.connect(self._on_effects_change)

        # Presets
        self.presets_panel.preset_selected.connect(self._on_preset_selected)

        # Toolbar
        self.toolbar.play_clicked.connect(self.canvas.play)
        self.toolbar.pause_clicked.connect(self.canvas.pause)
        self.toolbar.reset_clicked.connect(self._on_reset)
        self.toolbar.export_png_clicked.connect(self._on_export_png)
        self.toolbar.export_svg_clicked.connect(self._on_export_svg)
        self.toolbar.save_clicked.connect(self._on_save)
        self.toolbar.load_clicked.connect(self._on_load)

        # Canvas progress
        self.canvas.progress_changed.connect(self.toolbar.set_progress)
        self.canvas.drawing_complete.connect(
            lambda: self.status_bar.showMessage("Drawing complete")
        )

    def _on_config_change(self, config: HarmonographConfig):
        self._config = config
        self.canvas.set_config(config)
        self.status_bar.showMessage("Parameters updated")

    def _on_color_change(self, color_config: ColorConfig):
        self._color_config = color_config
        self.canvas.set_color_config(color_config)
        self.canvas.restart()

    def _on_effects_change(self, effects_config: EffectsConfig):
        self._effects_config = effects_config
        self.status_bar.showMessage("Effects updated (apply on export or reset)")

    def _on_preset_selected(self, config: HarmonographConfig, name: str):
        self._config = config
        self.controls.set_config(config)
        self.canvas.set_config(config)
        self.status_bar.showMessage(f'Preset loaded: "{name}"')

    def _on_reset(self):
        self.canvas.restart()
        self.toolbar.set_progress(0)
        self.status_bar.showMessage("Reset")

    def _on_export_png(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Export PNG", "rhythmogram.png",
            "PNG Images (*.png);;All Files (*)"
        )
        if path:
            self.status_bar.showMessage("Exporting PNG...")
            QApplication.processEvents()
            from utils.export import export_png
            export_png(path, self._config, self._color_config,
                       self._effects_config, 4096, 4096)
            self.status_bar.showMessage(f"Exported: {path}")

    def _on_export_svg(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Export SVG", "rhythmogram.svg",
            "SVG Files (*.svg);;All Files (*)"
        )
        if path:
            self.status_bar.showMessage("Exporting SVG...")
            QApplication.processEvents()
            from utils.export import export_svg
            export_svg(path, self._config, self._color_config, 4096, 4096)
            self.status_bar.showMessage(f"Exported: {path}")

    def _on_save(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Configuration", "rhythmogram_config.json",
            "JSON Files (*.json);;All Files (*)"
        )
        if path:
            save_config(path, self._config, self._color_config,
                        self._effects_config)
            self.status_bar.showMessage(f"Configuration saved: {path}")

    def _on_load(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Load Configuration", "",
            "JSON Files (*.json);;All Files (*)"
        )
        if path:
            try:
                config, color, effects = load_config(path)
                self._config = config
                self._color_config = color
                self._effects_config = effects
                self.controls.set_config(config)
                self.effects_panel.set_color_config(color)
                self.effects_panel.set_effects_config(effects)
                self.canvas.set_color_config(color)
                self.canvas.set_config(config)
                self.status_bar.showMessage(f"Configuration loaded: {path}")
            except Exception as e:
                self.status_bar.showMessage(f"Error loading config: {e}")
