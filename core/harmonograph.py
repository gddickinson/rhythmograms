"""Numpy-vectorized harmonograph point computation engine."""

import numpy as np
from .pendulum import HarmonographConfig


class HarmonographEngine:
    """Computes (x, y) trace points for a 4-pendulum damped harmonograph.

    x(t) = A1*sin(2*pi*f1*t + p1)*exp(-d1*t) + A2*sin(2*pi*f2*t + p2)*exp(-d2*t)
    y(t) = A3*sin(2*pi*f3*t + p3)*exp(-d3*t) + A4*sin(2*pi*f4*t + p4)*exp(-d4*t)
    """

    def __init__(self, config: HarmonographConfig):
        self.config = config
        self._precompute()

    def _precompute(self):
        """Pre-extract parameter arrays for vectorized computation."""
        p = self.config.pendulums
        self._freq = np.array([pp.frequency for pp in p]) * 2 * np.pi
        self._phase = np.array([pp.phase for pp in p])
        self._amp = np.array([pp.amplitude for pp in p])
        self._damp = np.array([pp.damping for pp in p])

    def compute_full(self) -> tuple:
        """Compute the complete trace. Returns (x, y) arrays."""
        n = self.config.total_points
        t = np.linspace(0, self.config.duration, n)
        return self._compute_at(t)

    def compute_chunk(self, start_idx: int, chunk_size: int) -> tuple:
        """Compute a chunk of the trace for animation.

        Returns (x, y) arrays for points [start_idx, start_idx + chunk_size).
        """
        n = self.config.total_points
        end_idx = min(start_idx + chunk_size, n)
        if start_idx >= n:
            return np.array([]), np.array([])
        t_start = start_idx / self.config.sample_rate
        t_end = end_idx / self.config.sample_rate
        t = np.linspace(t_start, t_end, end_idx - start_idx)
        return self._compute_at(t)

    def _compute_at(self, t: np.ndarray) -> tuple:
        """Compute x, y positions at given time values."""
        # Each pendulum: A * sin(freq*t + phase) * exp(-damping*t)
        # Pendulums 0,1 -> x; Pendulums 2,3 -> y
        signals = np.empty((4, len(t)))
        for i in range(4):
            signals[i] = (
                self._amp[i]
                * np.sin(self._freq[i] * t + self._phase[i])
                * np.exp(-self._damp[i] * t)
            )
        x = signals[0] + signals[1]
        y = signals[2] + signals[3]
        return x, y

    def compute_normalized(self, width: int, height: int, margin: float = 0.05):
        """Compute full trace normalized to pixel coordinates.

        Returns (x, y) arrays scaled to fit within [margin, 1-margin] * dimensions.
        """
        x, y = self.compute_full()
        return self._normalize(x, y, width, height, margin)

    def compute_chunk_normalized(
        self, start_idx: int, chunk_size: int,
        width: int, height: int,
        x_range: tuple = None, y_range: tuple = None,
        margin: float = 0.05,
    ):
        """Compute a normalized chunk. Requires pre-computed ranges for consistency."""
        x, y = self.compute_chunk(start_idx, chunk_size)
        if len(x) == 0:
            return np.array([]), np.array([])
        if x_range and y_range:
            x = self._scale(x, x_range, width, margin)
            y = self._scale(y, y_range, height, margin)
        else:
            x, y = self._normalize(x, y, width, height, margin)
        return x, y

    def compute_ranges(self) -> tuple:
        """Pre-compute the full x/y ranges for consistent chunk normalization."""
        x, y = self.compute_full()
        return (x.min(), x.max()), (y.min(), y.max())

    @staticmethod
    def _normalize(x, y, width, height, margin):
        x_min, x_max = x.min(), x.max()
        y_min, y_max = y.min(), y.max()
        x = HarmonographEngine._scale(x, (x_min, x_max), width, margin)
        y = HarmonographEngine._scale(y, (y_min, y_max), height, margin)
        return x, y

    @staticmethod
    def _scale(values, val_range, size, margin):
        v_min, v_max = val_range
        span = v_max - v_min
        if span < 1e-10:
            return np.full_like(values, size / 2.0)
        m = size * margin
        return m + (values - v_min) / span * (size - 2 * m)
