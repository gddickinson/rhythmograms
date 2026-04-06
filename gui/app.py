"""Main application window — menu bar, tabs, signal wiring, and coordination."""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QSplitter, QFileDialog,
    QStatusBar, QTabWidget, QApplication, QMenuBar, QMessageBox,
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QKeySequence, QShortcut, QAction

from core.pendulum import HarmonographConfig
from core.projection import Projection3DConfig
from effects.color import ColorConfig
from effects.postprocess import EffectsConfig, apply_effects
from gui.canvas import RhythmogramCanvas
from gui.controls import ControlPanel
from gui.effects_panel import EffectsPanel
from gui.toolbar import Toolbar
from gui.presets_panel import PresetsPanel
from gui.layers_panel import LayersPanel
from gui.gallery_panel import GalleryPanel
from gui.physics_panel import PhysicsPanel
from gui.style import DARK_THEME
from utils.config import save_config, load_config


class MainWindow(QMainWindow):
    """Main application window for the Rhythmogram Simulator."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Heidersberger Rhythmogram Simulator")
        self.setMinimumSize(QSize(1200, 800))
        self.setStyleSheet(DARK_THEME)

        self._config = HarmonographConfig()
        self._color_config = ColorConfig()
        self._effects_config = EffectsConfig()
        self._projection = Projection3DConfig()
        self._morph_dialog = None
        self._frame_capture = None

        self._build_ui()
        self._build_menu_bar()
        self._connect_signals()

        self.canvas.set_color_config(self._color_config)
        self.canvas.set_effects_config(self._effects_config)
        self.canvas.set_projection(self._projection)
        self.canvas.set_layer_compositor(self.layers_panel.composite_layers)
        self.canvas.set_config(self._config)

    def _build_menu_bar(self):
        mb = self.menuBar()

        # File menu
        file_menu = mb.addMenu("File")
        self._add_action(file_menu, "Save Config...", "Ctrl+S", self._on_save)
        self._add_action(file_menu, "Load Config...", "Ctrl+O", self._on_load)
        file_menu.addSeparator()
        self._add_action(file_menu, "Export PNG...", "Ctrl+E", self._on_export_png)
        self._add_action(file_menu, "Export SVG...", "Ctrl+Shift+E", self._on_export_svg)
        file_menu.addSeparator()
        self._add_action(file_menu, "Export GIF...", "Ctrl+G", self._on_export_gif)
        self._add_action(file_menu, "Export Video...", "", self._on_export_video)
        self._add_action(file_menu, "Export Time-Lapse...", "", self._on_export_timelapse)
        file_menu.addSeparator()
        self._add_action(file_menu, "Screenshot...", "Ctrl+Shift+S", self._on_screenshot)

        # View menu
        view_menu = mb.addMenu("View")
        self._add_action(view_menu, "Zoom In", "Ctrl+=", lambda: self._zoom_step(1.2))
        self._add_action(view_menu, "Zoom Out", "Ctrl+-", lambda: self._zoom_step(1/1.2))
        self._add_action(view_menu, "Reset Zoom", "Ctrl+0", self.canvas.reset_zoom)

        # Tools menu
        tools_menu = mb.addMenu("Tools")
        self._add_action(tools_menu, "Morph Configs...", "Ctrl+M", self._on_morph)
        tools_menu.addSeparator()
        self._add_action(tools_menu, "Load Audio File...", "", self._on_load_audio)
        self._add_action(tools_menu, "Clear Audio", "", self._on_clear_audio)

    def _add_action(self, menu, text, shortcut, callback):
        action = QAction(text, self)
        if shortcut:
            action.setShortcut(QKeySequence(shortcut))
        action.triggered.connect(callback)
        menu.addAction(action)

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.toolbar = Toolbar()
        main_layout.addWidget(self.toolbar)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        self.canvas = RhythmogramCanvas()
        self.canvas.setMinimumSize(600, 600)
        splitter.addWidget(self.canvas)

        right_panel = QTabWidget()
        right_panel.setMaximumWidth(360)
        right_panel.setMinimumWidth(280)

        self.controls = ControlPanel(self._config)
        right_panel.addTab(self.controls, "Pendulums")

        self.effects_panel = EffectsPanel(self._color_config, self._effects_config)
        right_panel.addTab(self.effects_panel, "Visual")

        self.physics_panel = PhysicsPanel()
        right_panel.addTab(self.physics_panel, "Physics")

        self.layers_panel = LayersPanel()
        right_panel.addTab(self.layers_panel, "Layers")

        self.presets_panel = PresetsPanel()
        right_panel.addTab(self.presets_panel, "Presets")

        self.gallery_panel = GalleryPanel()
        right_panel.addTab(self.gallery_panel, "Gallery")

        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 1)

        main_layout.addWidget(splitter)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

        QShortcut(QKeySequence("Space"), self, self.canvas.toggle_play_pause)
        QShortcut(QKeySequence("R"), self, self._on_reset)

    def _connect_signals(self):
        self.controls.config_changed.connect(self._on_config_change)
        self.physics_panel.params_changed.connect(self._on_physics_change)
        self.effects_panel.color_changed.connect(self._on_color_change)
        self.effects_panel.effects_changed.connect(self._on_effects_change)
        self.effects_panel.projection_changed.connect(self._on_projection_change)
        self.presets_panel.preset_selected.connect(self._on_preset_selected)
        self.gallery_panel.config_selected.connect(self._on_gallery_selected)
        self.layers_panel.flatten_requested.connect(self._on_flatten_layer)
        self.layers_panel.layers_changed.connect(lambda: self.canvas.update())
        self.layers_panel.load_layer_config.connect(self._on_load_layer_config)
        self.layers_panel.random_layer_requested.connect(self._on_random_layer)

        self.toolbar.play_clicked.connect(self.canvas.play)
        self.toolbar.pause_clicked.connect(self.canvas.pause)
        self.toolbar.reset_clicked.connect(self._on_reset)
        self.toolbar.export_png_clicked.connect(self._on_export_png)
        self.toolbar.export_svg_clicked.connect(self._on_export_svg)
        self.toolbar.save_clicked.connect(self._on_save)
        self.toolbar.load_clicked.connect(self._on_load)
        self.toolbar.continuous_toggled.connect(self._on_continuous_toggle)
        self.toolbar.fade_rate_changed.connect(self._on_fade_rate_change)

        self.canvas.progress_changed.connect(self.toolbar.set_progress)
        self.canvas.drawing_complete.connect(
            lambda: self.status_bar.showMessage("Drawing complete"))

    # --- Handlers ---
    def _on_config_change(self, config):
        self._config = config
        # Apply physics params on top
        self._apply_physics_to_config()
        self.canvas.set_config(self._config)
        self.status_bar.showMessage("Parameters updated")

    def _on_physics_change(self):
        self._apply_physics_to_config()
        self.canvas.set_config(self._config)
        self.status_bar.showMessage("Physics updated")

    def _apply_physics_to_config(self):
        """Overlay physics panel params onto the current config."""
        pp = self.physics_panel.get_physics_params()
        for i, fm in enumerate(pp["fm_params"]):
            p = self._config.pendulums[i]
            p.fm_freq = fm["fm_freq"]
            p.fm_depth = fm["fm_depth"]
            p.pm_freq = fm["pm_freq"]
            p.pm_depth = fm["pm_depth"]
            p.nonlinearity = fm["nonlinearity"]
        self._config.strobe_freq = pp["strobe_freq"]
        self._config.strobe_duty = pp["strobe_duty"]
        self._config.chorus_count = pp["chorus_count"]
        self._config.chorus_spread = pp["chorus_spread"]

    def _on_color_change(self, cc):
        self._color_config = cc
        self.canvas.set_color_config(cc)
        self.canvas.restart()

    def _on_effects_change(self, ec):
        self._effects_config = ec
        self.canvas.set_effects_config(ec)
        self.status_bar.showMessage("Effects updated")

    def _on_projection_change(self, proj):
        self._projection = proj
        self.canvas.set_projection(proj)
        self.status_bar.showMessage("3D projection updated")

    def _on_preset_selected(self, config, name):
        self._config = config
        self.controls.set_config(config)
        self.physics_panel.set_from_config(config)
        self.canvas.set_config(config)
        self.status_bar.showMessage(f'Preset: "{name}"')

    def _on_gallery_selected(self, config, cc):
        self._config = config
        self._color_config = cc
        self.controls.set_config(config)
        self.effects_panel.set_color_config(cc)
        self.canvas.set_color_config(cc)
        self.canvas.set_config(config)
        self.status_bar.showMessage("Gallery item loaded")

    def _on_flatten_layer(self):
        pixmap = self.canvas.get_current_image()
        if not pixmap.isNull():
            self.layers_panel.add_layer(pixmap, self._config, self._color_config)
            self.canvas.restart()
            self.canvas.pause()  # pause so user can change config before drawing
            self.status_bar.showMessage("Layer saved — change settings then press Play")

    def _on_load_layer_config(self, config, cc):
        """Load a layer's config into the editor (for creating variations)."""
        self._config = config
        self._color_config = cc
        self.controls.set_config(config)
        self.effects_panel.set_color_config(cc)
        self.canvas.set_color_config(cc)
        self.canvas.set_config(config)
        self.status_bar.showMessage("Layer config loaded into editor")

    def _on_random_layer(self):
        """Load smart random config after flattening current layer."""
        config = HarmonographConfig.smart_random()
        self._config = config
        self.controls.set_config(config)
        self.canvas.set_config(config)
        self.status_bar.showMessage("Random config loaded — press Play")

    def _on_continuous_toggle(self, enabled):
        self.canvas.continuous = enabled
        self.canvas.restart()
        self.status_bar.showMessage("Continuous" if enabled else "Standard")

    def _on_fade_rate_change(self, v):
        self.canvas.fade_rate = v

    def _on_reset(self):
        self.canvas.restart()
        self.toolbar.set_progress(0)
        self.status_bar.showMessage("Reset")

    def _zoom_step(self, factor):
        self.canvas._zoom = max(0.25, min(10.0, self.canvas._zoom * factor))
        self.canvas.update()

    # --- Morph ---
    def _on_morph(self):
        from gui.morph_dialog import MorphDialog
        self._morph_dialog = MorphDialog(
            self._config, self._color_config, parent=self)
        self._morph_dialog.config_updated.connect(self._on_morph_update)
        self._morph_dialog.show()

    def _on_morph_update(self, config, cc):
        self._config = config
        self._color_config = cc
        self.controls.set_config(config)
        self.effects_panel.set_color_config(cc)
        self.canvas.set_color_config(cc)
        self.canvas.set_config(config)

    # --- Audio ---
    def _on_load_audio(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Load Audio File", "", "WAV Files (*.wav);;All Files (*)")
        if not path:
            return
        from utils.audio import analyze_wav, check_audio_support
        if not check_audio_support():
            QMessageBox.warning(self, "Missing Dependency",
                                "scipy is required for audio analysis.")
            return
        analysis = analyze_wav(path)
        if analysis:
            self.canvas.set_audio_analysis(analysis)
            self.status_bar.showMessage(
                f"Audio loaded: {analysis.duration:.1f}s")
        else:
            self.status_bar.showMessage("Failed to load audio file")

    def _on_clear_audio(self):
        self.canvas.set_audio_analysis(None)
        self.status_bar.showMessage("Audio cleared")

    # --- Export ---
    def _on_export_png(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Export PNG", "rhythmogram.png", "PNG (*.png);;All (*)")
        if path:
            self.status_bar.showMessage("Exporting PNG...")
            QApplication.processEvents()
            from utils.export import export_png
            export_png(path, self._config, self._color_config,
                       self._effects_config, 4096, 4096)
            self.status_bar.showMessage(f"Exported: {path}")

    def _on_export_svg(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Export SVG", "rhythmogram.svg", "SVG (*.svg);;All (*)")
        if path:
            self.status_bar.showMessage("Exporting SVG...")
            QApplication.processEvents()
            from utils.export import export_svg
            export_svg(path, self._config, self._color_config, 4096, 4096)
            self.status_bar.showMessage(f"Exported: {path}")

    def _on_export_gif(self):
        from utils.animation_export import check_pillow_available
        if not check_pillow_available():
            QMessageBox.warning(self, "Missing Dependency",
                                "Pillow (pip install Pillow) is required for GIF export.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export GIF", "rhythmogram.gif", "GIF (*.gif);;All (*)")
        if not path:
            return
        self._capture_and_export("gif", path)

    def _on_export_video(self):
        from utils.animation_export import check_ffmpeg_available
        if not check_ffmpeg_available():
            QMessageBox.warning(self, "Missing Tool",
                                "ffmpeg must be installed for video export.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Video", "rhythmogram.mp4", "MP4 (*.mp4);;All (*)")
        if not path:
            return
        self._capture_and_export("video", path)

    def _on_export_timelapse(self):
        from utils.animation_export import check_pillow_available
        if not check_pillow_available():
            QMessageBox.warning(self, "Missing Dependency",
                                "Pillow is required for time-lapse export.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Time-Lapse", "timelapse.gif", "GIF (*.gif);;All (*)")
        if not path:
            return
        self._capture_and_export("timelapse", path)

    def _capture_and_export(self, mode, path):
        """Render full trace capturing frames, then export."""
        from utils.animation_export import (
            FrameCapture, export_gif, export_video, export_timelapse)

        self.status_bar.showMessage(f"Rendering frames for {mode} export...")
        QApplication.processEvents()

        capture = FrameCapture()
        # Render at smaller size for animation
        w, h = 800, 800
        from core.trace import TraceState
        trace = TraceState(self._config, w, h, chunk_size=500)
        from PyQt6.QtGui import QPixmap, QPainter

        pixmap = QPixmap(w, h)
        pixmap.fill(self._color_config.bg_color)

        frame_skip = 3  # capture every 3rd chunk
        chunk_count = 0
        while not trace.is_complete:
            result = trace.next_chunk()
            if result is None:
                break
            x, y = result
            if len(x) < 2:
                continue
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Plus)
            from gui.trace_renderer import draw_trace_chunk
            progress = trace.progress
            prev = max(0, progress - 500 / self._config.total_points)
            draw_trace_chunk(painter, x, y, prev, progress,
                             self._color_config, trace.speed_range, w, h)
            painter.end()
            chunk_count += 1
            if chunk_count % frame_skip == 0:
                img = pixmap.toImage()
                img = apply_effects(img, self._effects_config)
                capture.add_frame(img)

        if capture.frame_count == 0:
            self.status_bar.showMessage("No frames captured")
            return

        if mode == "gif":
            ok = export_gif(path, capture.frames, fps=24)
        elif mode == "video":
            ok = export_video(path, capture.frames, fps=30)
        else:
            ok = export_timelapse(path, capture.frames, skip=3, fps=20)

        if ok:
            self.status_bar.showMessage(
                f"Exported {capture.frame_count} frames: {path}")
        else:
            self.status_bar.showMessage("Export failed")

    # --- Screenshot ---
    def _on_screenshot(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Screenshot", "screenshot.png",
            "PNG (*.png);;JPEG (*.jpg);;All (*)")
        if path:
            pixmap = self.grab()
            pixmap.save(path)
            self.status_bar.showMessage(f"Screenshot saved: {path}")

    # --- Save/Load ---
    def _on_save(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Config", "rhythmogram_config.json", "JSON (*.json);;All (*)")
        if path:
            save_config(path, self._config, self._color_config, self._effects_config)
            self.status_bar.showMessage(f"Saved: {path}")

    def _on_load(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Load Config", "", "JSON (*.json);;All (*)")
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
                self.canvas.set_effects_config(effects)
                self.canvas.set_config(config)
                self.status_bar.showMessage(f"Loaded: {path}")
            except Exception as e:
                self.status_bar.showMessage(f"Error: {e}")
