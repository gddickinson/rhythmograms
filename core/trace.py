"""Incremental trace state for animated drawing."""

from .pendulum import HarmonographConfig
from .harmonograph import HarmonographEngine


class TraceState:
    """Manages progressive drawing of a harmonograph trace.

    Yields chunks of normalized (x, y) points for incremental rendering.
    """

    def __init__(self, config: HarmonographConfig, width: int, height: int,
                 chunk_size: int = 200):
        self.config = config
        self.width = width
        self.height = height
        self.chunk_size = chunk_size

        self.engine = HarmonographEngine(config)
        self._x_range, self._y_range = self.engine.compute_ranges()
        self._position = 0
        self._total = config.total_points
        self._paused = False

    @property
    def progress(self) -> float:
        """Return drawing progress from 0.0 to 1.0."""
        if self._total == 0:
            return 1.0
        return min(self._position / self._total, 1.0)

    @property
    def is_complete(self) -> bool:
        return self._position >= self._total

    @property
    def is_paused(self) -> bool:
        return self._paused

    def pause(self):
        self._paused = True

    def resume(self):
        self._paused = False

    def next_chunk(self):
        """Return the next chunk of normalized (x, y) pixel coordinates.

        Returns None if paused or complete.
        """
        if self._paused or self.is_complete:
            return None

        x, y = self.engine.compute_chunk_normalized(
            self._position, self.chunk_size,
            self.width, self.height,
            self._x_range, self._y_range,
        )
        self._position += self.chunk_size
        if len(x) == 0:
            return None
        return x, y

    def resize(self, width: int, height: int):
        """Update canvas dimensions (for window resize)."""
        self.width = width
        self.height = height

    def reset(self):
        """Reset to the beginning."""
        self._position = 0
        self._paused = False

    def compute_full_normalized(self):
        """Compute the entire trace at once (for export/thumbnails)."""
        return self.engine.compute_normalized(self.width, self.height)
