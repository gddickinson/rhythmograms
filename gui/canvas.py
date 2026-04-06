"""QPainter canvas with offscreen buffer, animated trace, velocity drawing, symmetry,
live post-processing preview, continuous simulation, and zoom/pan."""

import math
import numpy as np
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import QTimer, pyqtSignal, Qt, QPointF, QRectF
from PyQt6.QtGui import QPainter, QPixmap, QPen, QColor, QImage, QTransform

from core.pendulum import HarmonographConfig
from core.trace import TraceState
from effects.color import ColorConfig
from effects.postprocess import EffectsConfig, apply_effects


class RhythmogramCanvas(QWidget):
    """Canvas widget that progressively draws a harmonograph trace.

    Supports standard (finite) and continuous (infinite) modes,
    velocity-sensitive drawing, rotational symmetry, live effects,
    and scroll-wheel zoom with pan.
    """

    progress_changed = pyqtSignal(float)
    drawing_complete = pyqtSignal()

    TIMER_INTERVAL_MS = 16  # ~60 fps
    CHUNK_SIZE = 300
    ZOOM_MIN = 0.25
    ZOOM_MAX = 10.0
    ZOOM_STEP = 1.15  # 15% per scroll notch

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(500, 500)
        self.setMouseTracking(True)

        self._config = HarmonographConfig()
        self._color_config = ColorConfig()
        self._effects_config = EffectsConfig()
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
        self._pan = QPointF(0, 0)  # offset in widget coords
        self._panning = False
        self._pan_start = QPointF()

        self._timer = QTimer(self)
        self._timer.setInterval(self.TIMER_INTERVAL_MS)
        self._timer.timeout.connect(self._draw_next_chunk)

        self.setStyleSheet("background-color: #05050f;")

    # --- Properties ---

    @property
    def continuous(self) -> bool:
        return self._continuous

    @continuous.setter
    def continuous(self, value: bool):
        self._continuous = value

    @property
    def fade_rate(self) -> int:
        return self._fade_rate

    @fade_rate.setter
    def fade_rate(self, value: int):
        self._fade_rate = max(1, min(20, value))

    @property
    def zoom_level(self) -> float:
        return self._zoom

    # --- Config setters ---

    def set_config(self, config: HarmonographConfig):
        self._config = config
        self.restart()

    def set_color_config(self, color_config: ColorConfig):
        self._color_config = color_config

    def set_effects_config(self, effects_config: EffectsConfig):
        self._effects_config = effects_config
        self._effects_dirty = True
        self.update()

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
        if self._playing:
            self.pause()
        else:
            self.play()

    @property
    def is_playing(self) -> bool:
        return self._playing

    def reset_zoom(self):
        """Reset zoom to 1x and center the view."""
        self._zoom = 1.0
        self._pan = QPointF(0, 0)
        self.update()

    # --- Image access ---

    def get_current_image(self) -> QPixmap:
        if self._pixmap:
            return self._pixmap.copy()
        return QPixmap()

    def render_full(self, width: int, height: int) -> QPixmap:
        trace = TraceState(
            self._config, width, height, chunk_size=self._config.total_points
        )
        pixmap = QPixmap(width, height)
        pixmap.fill(self._color_config.bg_color)

        x, y = trace.compute_full_normalized()
        if len(x) < 2:
            return pixmap

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setCompositionMode(
            QPainter.CompositionMode.CompositionMode_Plus
        )
        self._draw_points(painter, x, y, 0.0, 1.0, trace.speed_range,
                          width, height)
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

        result = self._trace.next_chunk()
        if result is None:
            return

        x, y = result
        if len(x) < 2:
            return

        progress = self._trace.progress
        prev_progress = max(
            0, progress - self.CHUNK_SIZE / self._config.total_points
        )

        painter = QPainter(self._pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setCompositionMode(
            QPainter.CompositionMode.CompositionMode_Plus
        )
        self._draw_points(painter, x, y, prev_progress, progress,
                          self._trace.speed_range,
                          self.width(), self.height())
        painter.end()

        self._effects_dirty = True
        self.progress_changed.emit(progress)
        self.update()

    def _apply_fade(self):
        painter = QPainter(self._pixmap)
        bg = QColor(self._color_config.bg_color)
        bg.setAlpha(self._fade_rate)
        painter.setCompositionMode(
            QPainter.CompositionMode.CompositionMode_SourceOver
        )
        painter.fillRect(self._pixmap.rect(), bg)
        painter.end()

    # --- Drawing helpers ---

    def _draw_points(self, painter: QPainter, x, y, t_start: float,
                     t_end: float, speed_range: tuple,
                     canvas_w: int, canvas_h: int):
        n = len(x)
        cc = self._color_config
        sym = cc.symmetry_order
        needs_velocity = cc.velocity_width or cc.velocity_opacity

        speeds = None
        if needs_velocity:
            speeds = self._compute_normalized_speeds(x, y, speed_range)

        cx = canvas_w / 2.0
        cy = canvas_h / 2.0

        for rot in range(max(1, sym)):
            angle = (2.0 * math.pi * rot / sym) if sym > 1 else 0.0
            cos_a = math.cos(angle)
            sin_a = math.sin(angle)

            for i in range(n - 1):
                t = t_start + (t_end - t_start) * (i / max(n - 1, 1))
                color = cc.color_at(t)

                if speeds is not None:
                    spd = speeds[i]
                    if cc.velocity_width:
                        width = cc.width_at_speed(spd)
                    else:
                        width = cc.line_width
                    if cc.velocity_opacity:
                        alpha = cc.alpha_at_speed(spd)
                        color.setAlpha(alpha)
                else:
                    width = cc.line_width

                pen = QPen(color, width)
                pen.setCapStyle(Qt.PenCapStyle.RoundCap)
                painter.setPen(pen)

                if sym > 1:
                    x1, y1 = self._rotate(x[i], y[i], cx, cy, cos_a, sin_a)
                    x2, y2 = self._rotate(x[i + 1], y[i + 1], cx, cy,
                                          cos_a, sin_a)
                else:
                    x1, y1 = x[i], y[i]
                    x2, y2 = x[i + 1], y[i + 1]

                painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))

    @staticmethod
    def _compute_normalized_speeds(x, y, speed_range):
        dx = np.diff(x)
        dy = np.diff(y)
        speed = np.sqrt(dx * dx + dy * dy)
        s_min, s_max = speed_range
        span = s_max - s_min
        if span < 1e-10:
            return np.zeros(len(speed))
        return np.clip((speed - s_min) / span, 0.0, 1.0)

    @staticmethod
    def _rotate(px, py, cx, cy, cos_a, sin_a):
        dx = px - cx
        dy = py - cy
        return cx + dx * cos_a - dy * sin_a, cy + dx * sin_a + dy * cos_a

    # --- Display with effects and zoom ---

    def _get_display_pixmap(self) -> QPixmap:
        if not self._pixmap:
            return QPixmap()

        has_effects = (self._effects_config.invert
                       or self._effects_config.solarize
                       or self._effects_config.bloom
                       or self._effects_config.vignette)

        if not has_effects:
            return self._pixmap

        if self._effects_dirty or self._display_pixmap is None:
            image = self._pixmap.toImage()
            image = apply_effects(image, self._effects_config)
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
            # Fast path: no transform needed
            painter.drawPixmap(0, 0, pixmap)
        else:
            # Apply zoom centered on widget center, plus pan offset
            cx = self.width() / 2.0
            cy = self.height() / 2.0
            painter.translate(cx + self._pan.x(), cy + self._pan.y())
            painter.scale(self._zoom, self._zoom)
            painter.translate(-cx, -cy)
            painter.drawPixmap(0, 0, pixmap)

        painter.end()

    # --- Zoom and pan events ---

    def wheelEvent(self, event):
        """Zoom in/out centered on the cursor position."""
        delta = event.angleDelta().y()
        if delta == 0:
            return

        old_zoom = self._zoom
        if delta > 0:
            new_zoom = min(old_zoom * self.ZOOM_STEP, self.ZOOM_MAX)
        else:
            new_zoom = max(old_zoom / self.ZOOM_STEP, self.ZOOM_MIN)

        if new_zoom == old_zoom:
            return

        # Zoom toward cursor: adjust pan so the point under the cursor
        # stays at the same screen position
        cursor_pos = event.position()
        cx = self.width() / 2.0
        cy = self.height() / 2.0

        # Point in image coords under cursor (before zoom)
        img_x = (cursor_pos.x() - cx - self._pan.x()) / old_zoom + cx
        img_y = (cursor_pos.y() - cy - self._pan.y()) / old_zoom + cy

        # Where that image point ends up after zoom change (without pan adjust)
        new_screen_x = (img_x - cx) * new_zoom + cx
        new_screen_y = (img_y - cy) * new_zoom + cy

        # Adjust pan so it stays under cursor
        self._pan = QPointF(
            cursor_pos.x() - new_screen_x,
            cursor_pos.y() - new_screen_y,
        )
        self._zoom = new_zoom
        self.update()
        event.accept()

    def mousePressEvent(self, event):
        """Start panning with middle button or Ctrl+left button."""
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
        """Pan the view while dragging."""
        if self._panning:
            self._pan = event.position() - self._pan_start
            self.update()
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """Stop panning."""
        if self._panning:
            self._panning = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        """Double-click to reset zoom and pan."""
        self.reset_zoom()
        event.accept()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._config:
            self.restart()
