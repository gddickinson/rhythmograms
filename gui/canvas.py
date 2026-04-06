"""QPainter canvas with offscreen buffer and animated trace drawing."""

from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import QTimer, pyqtSignal, Qt
from PyQt6.QtGui import QPainter, QPixmap, QPen, QColor

from core.pendulum import HarmonographConfig
from core.trace import TraceState
from effects.color import ColorConfig


class RhythmogramCanvas(QWidget):
    """Canvas widget that progressively draws a harmonograph trace.

    Uses offscreen QPixmap accumulation with additive compositing
    to simulate light on photographic paper.
    """

    progress_changed = pyqtSignal(float)
    drawing_complete = pyqtSignal()

    TIMER_INTERVAL_MS = 16  # ~60 fps
    CHUNK_SIZE = 300

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(400, 400)

        self._config = HarmonographConfig()
        self._color_config = ColorConfig()
        self._trace = None
        self._pixmap = None
        self._playing = False

        self._timer = QTimer(self)
        self._timer.setInterval(self.TIMER_INTERVAL_MS)
        self._timer.timeout.connect(self._draw_next_chunk)

        self.setStyleSheet("background-color: #05050f;")

    def set_config(self, config: HarmonographConfig):
        """Set a new harmonograph configuration and restart drawing."""
        self._config = config
        self.restart()

    def set_color_config(self, color_config: ColorConfig):
        """Update color settings."""
        self._color_config = color_config

    def restart(self):
        """Clear the canvas and start drawing from scratch."""
        self._timer.stop()
        w, h = self.width(), self.height()
        if w < 10 or h < 10:
            return

        self._pixmap = QPixmap(w, h)
        self._pixmap.fill(self._color_config.bg_color)
        self._trace = TraceState(
            self._config, w, h, chunk_size=self.CHUNK_SIZE
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

    def get_current_image(self) -> QPixmap:
        """Return the current canvas pixmap (for export/effects)."""
        if self._pixmap:
            return self._pixmap.copy()
        return QPixmap()

    def render_full(self, width: int, height: int) -> QPixmap:
        """Render the complete trace at given dimensions (for export)."""
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
        self._draw_points(painter, x, y, 0.0, 1.0)
        painter.end()
        return pixmap

    def _draw_next_chunk(self):
        """Timer callback: draw the next chunk of the trace."""
        if not self._trace or self._trace.is_complete:
            self._timer.stop()
            self._playing = False
            self.drawing_complete.emit()
            return

        result = self._trace.next_chunk()
        if result is None:
            return

        x, y = result
        if len(x) < 2:
            return

        progress = self._trace.progress
        prev_progress = max(0, progress - self.CHUNK_SIZE / self._config.total_points)

        painter = QPainter(self._pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setCompositionMode(
            QPainter.CompositionMode.CompositionMode_Plus
        )
        self._draw_points(painter, x, y, prev_progress, progress)
        painter.end()

        self.progress_changed.emit(progress)
        self.update()

    def _draw_points(self, painter: QPainter, x, y, t_start: float, t_end: float):
        """Draw a series of connected line segments."""
        n = len(x)
        for i in range(n - 1):
            t = t_start + (t_end - t_start) * (i / max(n - 1, 1))
            color = self._color_config.color_at(t)
            pen = QPen(color, self._color_config.line_width)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            painter.drawLine(
                int(x[i]), int(y[i]),
                int(x[i + 1]), int(y[i + 1]),
            )

    def paintEvent(self, event):
        if self._pixmap:
            painter = QPainter(self)
            painter.drawPixmap(0, 0, self._pixmap)
            painter.end()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._config:
            self.restart()
