"""QPainter canvas — animated trace with layers, 3D, audio, zoom/pan,
continuous mode, and live post-processing preview."""

import math
import numpy as np
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import QTimer, pyqtSignal, Qt, QPointF
from PyQt6.QtGui import QPainter, QPixmap, QColor

from core.pendulum import HarmonographConfig
from core.trace import TraceState
from core.projection import Projection3DConfig, compute_z, apply_perspective
from effects.color import ColorConfig
from effects.postprocess import EffectsConfig, apply_effects
from effects.atmosphere import AtmosphereConfig, apply_atmosphere
from gui.trace_renderer import draw_trace_chunk


class RhythmogramCanvas(QWidget):
    """Canvas widget with progressive trace drawing and compositing."""

    progress_changed = pyqtSignal(float)
    drawing_complete = pyqtSignal()
    frame_rendered = pyqtSignal(object)  # QImage for animation capture

    TIMER_INTERVAL_MS = 16
    CHUNK_SIZE = 300
    ZOOM_MIN, ZOOM_MAX, ZOOM_STEP = 0.25, 10.0, 1.15

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(500, 500)
        self.setMouseTracking(True)

        self._config = HarmonographConfig()
        self._color_config = ColorConfig()
        self._effects_config = EffectsConfig()
        self._atmosphere_config = AtmosphereConfig()
        self._projection = Projection3DConfig()
        self._trace = None
        self._pixmap = None
        self._display_pixmap = None
        self._effects_dirty = True
        self._playing = False

        # Continuous mode
        self._continuous = False
        self._fade_rate = 3

        # Zoom and pan
        self._zoom = 1.0
        self._pan = QPointF(0, 0)
        self._panning = False
        self._pan_start = QPointF()

        # Layer compositing callback
        self._layer_compositor = None

        # Audio-reactive
        self._audio_analysis = None
        self._audio_mod_strength = 0.5

        # Frame capture for animation export
        self._capturing = False

        self._timer = QTimer(self)
        self._timer.setInterval(self.TIMER_INTERVAL_MS)
        self._timer.timeout.connect(self._draw_next_chunk)
        self.setStyleSheet("background-color: #05050f;")

    # --- Properties ---
    @property
    def continuous(self): return self._continuous
    @continuous.setter
    def continuous(self, v): self._continuous = v

    @property
    def fade_rate(self): return self._fade_rate
    @fade_rate.setter
    def fade_rate(self, v): self._fade_rate = max(1, min(20, v))

    @property
    def zoom_level(self): return self._zoom

    @property
    def capturing(self): return self._capturing
    @capturing.setter
    def capturing(self, v): self._capturing = v

    # --- Config setters ---
    def set_config(self, config):
        self._config = config
        self.restart()

    def set_color_config(self, cc):
        self._color_config = cc

    def set_effects_config(self, ec):
        self._effects_config = ec
        self._effects_dirty = True
        self.update()

    def set_atmosphere_config(self, ac):
        self._atmosphere_config = ac
        self._effects_dirty = True
        self.update()

    def set_projection(self, proj):
        self._projection = proj
        self.restart()

    def set_layer_compositor(self, fn):
        """Set a callable(QPixmap) -> QPixmap for layer compositing."""
        self._layer_compositor = fn

    def set_audio_analysis(self, analysis, strength=0.5):
        self._audio_analysis = analysis
        self._audio_mod_strength = strength

    # --- Playback ---
    def restart(self):
        self._timer.stop()
        w, h = self.width(), self.height()
        if w < 10 or h < 10:
            return
        self._pixmap = QPixmap(w, h)
        self._pixmap.fill(self._color_config.bg_color)
        self._display_pixmap = None
        self._effects_dirty = True
        self._trace = TraceState(
            self._config, w, h, chunk_size=self.CHUNK_SIZE,
            continuous=self._continuous,
        )
        self._playing = True
        self._timer.start()
        self.update()

    def play(self):
        if self._trace and not self._trace.is_complete:
            self._playing = True
            self._trace.resume()
            self._timer.start()

    def pause(self):
        self._playing = False
        if self._trace:
            self._trace.pause()
        self._timer.stop()

    def toggle_play_pause(self):
        if self._playing: self.pause()
        else: self.play()

    @property
    def is_playing(self): return self._playing

    def reset_zoom(self):
        self._zoom = 1.0
        self._pan = QPointF(0, 0)
        self.update()

    def get_current_image(self):
        return self._pixmap.copy() if self._pixmap else QPixmap()

    def render_full(self, width, height):
        trace = TraceState(self._config, width, height,
                           chunk_size=self._config.total_points)
        pixmap = QPixmap(width, height)
        pixmap.fill(self._color_config.bg_color)
        x, y = trace.compute_full_normalized()
        if len(x) < 2:
            return pixmap
        # Apply 3D if enabled
        if self._projection.enabled:
            x, y = self._apply_3d(x, y, trace, width, height)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Plus)
        draw_trace_chunk(painter, x, y, 0.0, 1.0, self._color_config,
                         trace.speed_range, width, height)
        painter.end()
        return pixmap

    # --- Animation ---
    def _draw_next_chunk(self):
        if not self._trace or self._trace.is_complete:
            self._timer.stop()
            self._playing = False
            self.drawing_complete.emit()
            return

        if self._continuous and self._pixmap:
            self._apply_fade()

        # Audio-reactive modulation
        if self._audio_analysis and self._trace:
            self._apply_audio_modulation()

        result = self._trace.next_chunk()
        if result is None:
            return
        x, y = result
        if len(x) < 2:
            return

        # 3D projection
        if self._projection.enabled:
            x, y = self._apply_3d_chunk(x, y)

        progress = self._trace.progress
        prev_progress = max(0, progress - self.CHUNK_SIZE / self._config.total_points)

        painter = QPainter(self._pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Plus)
        draw_trace_chunk(painter, x, y, prev_progress, progress,
                         self._color_config, self._trace.speed_range,
                         self.width(), self.height())
        painter.end()

        self._effects_dirty = True
        self.progress_changed.emit(progress)

        if self._capturing:
            self.frame_rendered.emit(self._pixmap.toImage())

        self.update()

    def _apply_fade(self):
        painter = QPainter(self._pixmap)
        bg = QColor(self._color_config.bg_color)
        bg.setAlpha(self._fade_rate)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        painter.fillRect(self._pixmap.rect(), bg)
        painter.end()

    def _apply_audio_modulation(self):
        """Modulate config based on audio analysis at current time."""
        if not self._audio_analysis or not self._trace:
            return
        t = self._trace.current_time
        mod = self._audio_analysis.modulation_at(t)
        s = self._audio_mod_strength
        # Modulate amplitudes based on spectral bands
        for i, key in enumerate(["bass", "low_mid", "mid", "high_mid"]):
            if i < 4:
                base_amp = self._config.pendulums[i].amplitude
                self._config.pendulums[i].amplitude = base_amp * (1 - s + s * mod[key])

    def _apply_3d_chunk(self, x, y):
        """Apply 3D projection to normalized chunk coordinates."""
        proj = self._projection
        w, h = self.width(), self.height()
        cx, cy = w / 2.0, h / 2.0
        # Convert pixel coords back to normalized [-1, 1]
        xn = (x - cx) / cx
        yn = (y - cy) / cy
        # Simple Z from time-based oscillation
        t_approx = np.linspace(0, len(x) / 1000.0, len(x))
        z = np.zeros_like(xn)
        for p in proj.z_pendulums:
            freq = p.frequency * 2 * math.pi
            z += p.amplitude * np.sin(freq * t_approx + p.phase) * np.exp(-p.damping * t_approx)
        # Auto-rotate
        rot_x = proj.rotation_x
        rot_y = proj.rotation_y
        if proj.auto_rotate and self._trace:
            t_global = self._trace.current_time
            rot_y += t_global * proj.auto_rotate_speed
        xp, yp = apply_perspective(xn, yn, z, proj.focal_length, rot_x, rot_y)
        return xp * cx + cx, yp * cy + cy

    def _apply_3d(self, x, y, trace, width, height):
        """Apply 3D for full render."""
        proj = self._projection
        cx, cy = width / 2.0, height / 2.0
        xn = (x - cx) / cx
        yn = (y - cy) / cy
        t = np.linspace(0, self._config.duration, len(x))
        z = compute_z(t, proj.z_pendulums)
        xp, yp = apply_perspective(xn, yn, z, proj.focal_length,
                                    proj.rotation_x, proj.rotation_y)
        return xp * cx + cx, yp * cy + cy

    # --- Display ---
    def _get_display_pixmap(self):
        if not self._pixmap:
            return QPixmap()

        # Layer compositing
        base = self._pixmap
        if self._layer_compositor:
            base = self._layer_compositor(base)

        has_fx = (self._effects_config.invert or self._effects_config.solarize
                  or self._effects_config.bloom or self._effects_config.vignette
                  or self._atmosphere_config.has_any)
        if not has_fx:
            return base
        if self._effects_dirty or self._display_pixmap is None:
            image = base.toImage()
            image = apply_effects(image, self._effects_config)
            if self._atmosphere_config.has_any:
                from effects.postprocess import qimage_to_array, array_to_qimage
                arr = qimage_to_array(image)
                arr = apply_atmosphere(arr, self._atmosphere_config)
                image = array_to_qimage(arr)
            self._display_pixmap = QPixmap.fromImage(image)
            self._effects_dirty = False
        return self._display_pixmap

    def paintEvent(self, event):
        pixmap = self._get_display_pixmap()
        if pixmap.isNull():
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        if self._zoom == 1.0 and self._pan == QPointF(0, 0):
            painter.drawPixmap(0, 0, pixmap)
        else:
            cx, cy = self.width() / 2.0, self.height() / 2.0
            painter.translate(cx + self._pan.x(), cy + self._pan.y())
            painter.scale(self._zoom, self._zoom)
            painter.translate(-cx, -cy)
            painter.drawPixmap(0, 0, pixmap)
        painter.end()

    # --- Input events ---
    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        if delta == 0: return
        old = self._zoom
        new = min(old * self.ZOOM_STEP, self.ZOOM_MAX) if delta > 0 else max(old / self.ZOOM_STEP, self.ZOOM_MIN)
        if new == old: return
        pos = event.position()
        cx, cy = self.width() / 2.0, self.height() / 2.0
        ix = (pos.x() - cx - self._pan.x()) / old + cx
        iy = (pos.y() - cy - self._pan.y()) / old + cy
        sx = (ix - cx) * new + cx
        sy = (iy - cy) * new + cy
        self._pan = QPointF(pos.x() - sx, pos.y() - sy)
        self._zoom = new
        self.update()
        event.accept()

    def mousePressEvent(self, event):
        if (event.button() == Qt.MouseButton.MiddleButton or
                (event.button() == Qt.MouseButton.LeftButton and
                 event.modifiers() & Qt.KeyboardModifier.ControlModifier)):
            self._panning = True
            self._pan_start = event.position() - self._pan
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._panning:
            self._pan = event.position() - self._pan_start
            self.update()
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._panning:
            self._panning = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        self.reset_zoom()
        event.accept()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._config:
            self.restart()
