"""Numpy-vectorized harmonograph point computation engine with envelope modulation."""

import numpy as np
from .pendulum import HarmonographConfig


class HarmonographEngine:
    """Computes (x, y) trace points for a 4-pendulum damped harmonograph.

    x(t) = A1*sin(2*pi*f1*t + p1)*env1(t) + A2*sin(2*pi*f2*t + p2)*env2(t)
    y(t) = A3*sin(2*pi*f3*t + p3)*env3(t) + A4*sin(2*pi*f4*t + p4)*env4(t)

    Where env_i(t) is either pure damping exp(-d*t) or an envelope-modulated
    variant (breathe, pulse, bounce).
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

    def compute_chunk(self, start_idx: int, chunk_size: int,
                      unbounded: bool = False) -> tuple:
        """Compute a chunk of the trace for animation.

        Returns (x, y) arrays for points [start_idx, start_idx + chunk_size).
        If unbounded=True, allows computing beyond total_points (continuous mode).
        """
        n = self.config.total_points
        end_idx = start_idx + chunk_size
        if not unbounded:
            end_idx = min(end_idx, n)
            if start_idx >= n:
                return np.array([]), np.array([])
        t_start = start_idx / self.config.sample_rate
        t_end = end_idx / self.config.sample_rate
        t = np.linspace(t_start, t_end, end_idx - start_idx)
        return self._compute_at(t)

    def _compute_at(self, t: np.ndarray) -> tuple:
        """Compute x, y positions at given time values."""
        env = self.config.envelope
        signals = np.empty((4, len(t)))

        for i in range(4):
            oscillation = self._amp[i] * np.sin(self._freq[i] * t + self._phase[i])
            envelope = self._compute_envelope(t, self._damp[i], env)
            signals[i] = oscillation * envelope

        x = signals[0] + signals[1]
        y = signals[2] + signals[3]
        return x, y

    @staticmethod
    def _compute_envelope(t, damping, env_config):
        """Compute the amplitude envelope for a pendulum over time t.

        Blends between base exponential damping and the chosen envelope mode.
        """
        base_decay = np.exp(-damping * t)

        if env_config.mode == "none" or env_config.strength <= 0:
            return base_decay

        s = env_config.strength
        f = max(env_config.frequency, 0.001)

        if env_config.mode == "breathe":
            # Smooth sinusoidal amplitude modulation
            # Pattern breathes in and out while slowly decaying
            # At s=1: oscillates between 0 and 1 (full breathing)
            # At s=0: pure damping
            mod = 0.5 * (1.0 + np.cos(2.0 * np.pi * f * t))
            return base_decay * ((1.0 - s) + s * mod)

        if env_config.mode == "pulse":
            # Periodic energy kick — damping resets each cycle
            # Like someone pushing the pendulum every 1/f seconds
            period = 1.0 / f
            t_mod = np.fmod(t, period)
            pulse_env = np.exp(-damping * t_mod)
            return (1.0 - s) * base_decay + s * pulse_env

        if env_config.mode == "bounce":
            # Symmetric triangle wave — pattern grows and shrinks
            # No net decay: the envelope is purely periodic
            # Creates beautiful expanding/contracting patterns
            period = 1.0 / f
            phase = np.fmod(t, period) / period  # 0 to 1
            # Triangle: 0 -> 1 -> 0 over one period
            triangle = 1.0 - 2.0 * np.abs(phase - 0.5)
            # Smooth it with a power curve for organic feel
            smooth_tri = np.sin(triangle * np.pi * 0.5)  # sine ease
            # Blend: at s=1 pure bounce, at s=0 pure damping
            return (1.0 - s) * base_decay + s * smooth_tri

        return base_decay

    def compute_normalized(self, width: int, height: int, margin: float = 0.05):
        """Compute full trace normalized to pixel coordinates."""
        x, y = self.compute_full()
        return self._normalize(x, y, width, height, margin)

    def compute_chunk_normalized(
        self, start_idx: int, chunk_size: int,
        width: int, height: int,
        x_range: tuple = None, y_range: tuple = None,
        margin: float = 0.05,
        unbounded: bool = False,
    ):
        """Compute a normalized chunk. Requires pre-computed ranges for consistency."""
        x, y = self.compute_chunk(start_idx, chunk_size, unbounded=unbounded)
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

    def compute_speed_range(self) -> tuple:
        """Pre-compute the speed range for velocity-sensitive drawing."""
        x, y = self.compute_full()
        dx = np.diff(x)
        dy = np.diff(y)
        speed = np.sqrt(dx * dx + dy * dy)
        return float(speed.min()), float(speed.max())

    def compute_amplitude_ranges(self) -> tuple:
        """Compute theoretical max ranges from amplitudes (for continuous mode)."""
        a = self._amp
        x_max = a[0] + a[1]
        y_max = a[2] + a[3]
        return (-x_max, x_max), (-y_max, y_max)

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
