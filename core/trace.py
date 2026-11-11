"""Incremental trace state for animated drawing."""

import numpy as np

from .pendulum import HarmonographConfig
from .harmonograph import HarmonographEngine


class TraceState:
    """Manages progressive drawing of a harmonograph trace.

    Yields chunks of normalized (x, y) points for incremental rendering.
    Supports both finite (standard) and continuous (infinite) modes.
    """

    def __init__(self, config: HarmonographConfig, width: int, height: int,
                 chunk_size: int = 200, continuous: bool = False):
        self.config = config
        self.width = width
        self.height = height
        self.chunk_size = chunk_size
        self.continuous = continuous

        self.engine = HarmonographEngine(config)

        if continuous:
            # Use amplitude-based ranges for continuous mode
            self._x_range, self._y_range = self.engine.compute_amplitude_ranges()
        else:
            self._x_range, self._y_range = self.engine.compute_ranges()

        # In pixels, like the chunk coordinates the renderer measures speeds on (engine units would pin every
        # normalised speed at 1 and flatten the velocity-sensitive width / opacity).
        self._speed_range = self._pixel_speed_range()
        self._position = 0
        self._total = config.total_points
        self._paused = False

    def _pixel_speed_range(self) -> tuple:
        """(min, max) segment length in pixels of the full trace, scaled with this trace's x/y ranges."""
        x, y = self.engine.compute_full()
        x = self.engine._scale(x, self._x_range, self.width, 0.05)
        y = self.engine._scale(y, self._y_range, self.height, 0.05)
        speed = np.hypot(np.diff(x), np.diff(y))
        valid = speed[~np.isnan(speed)]
        if len(valid) == 0:
            return (0.0, 1.0)
        return float(valid.min()), float(valid.max())

    @property
    def progress(self) -> float:
        """Return drawing progress from 0.0 to 1.0."""
        if self.continuous:
            # In continuous mode, cycle through 0-1 repeatedly
            cycle_len = self._total
            if cycle_len == 0:
                return 0.0
            return (self._position % cycle_len) / cycle_len
        if self._total == 0:
            return 1.0
        return min(self._position / self._total, 1.0)

    @property
    def is_complete(self) -> bool:
        if self.continuous:
            return False  # never completes
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
            unbounded=self.continuous,
        )
        self._position += self.chunk_size
        if len(x) == 0:
            return None
        return x, y

    @property
    def speed_range(self) -> tuple:
        """Return (speed_min, speed_max) for velocity normalization."""
        return self._speed_range

    @property
    def current_time(self) -> float:
        """Current time position in seconds."""
        return self._position / self.config.sample_rate

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
