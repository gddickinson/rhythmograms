"""Trail state manager — ring buffer of recent points for trail visualization."""

from dataclasses import dataclass, field
from typing import List
import numpy as np
from collections import deque

from .pendulum import HarmonographConfig
from .harmonograph import HarmonographEngine


@dataclass
class TrailConfig:
    """Configuration for trail mode visualization."""
    enabled: bool = False
    trail_length: int = 800          # points in the combined trail
    point_size: float = 4.0          # size of the leading dot
    show_pendulums: bool = False     # show individual pendulum contribution trails
    pendulum_trail_lengths: List[int] = field(
        default_factory=lambda: [400, 400, 400, 400]
    )
    pendulum_colors: List[str] = field(
        default_factory=lambda: ["#ff4444", "#44ff44", "#4444ff", "#ffff44"]
    )
    fade_power: float = 1.5          # 1.0 = linear fade, >1 = sharper fade at tail

    def to_dict(self) -> dict:
        return {
            "enabled": self.enabled,
            "trail_length": self.trail_length,
            "point_size": self.point_size,
            "show_pendulums": self.show_pendulums,
            "pendulum_trail_lengths": self.pendulum_trail_lengths,
            "pendulum_colors": self.pendulum_colors,
            "fade_power": self.fade_power,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "TrailConfig":
        fields = {k for k in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in d.items() if k in fields})


class TrailBuffer:
    """Ring buffer that stores recent harmonograph points for trail rendering.

    Maintains separate buffers for the combined trace and each individual
    pendulum's contribution, with configurable lengths per pendulum.
    """

    def __init__(self, config: HarmonographConfig, trail_config: TrailConfig,
                 width: int, height: int):
        self.config = config
        self.trail_config = trail_config
        self.width = width
        self.height = height

        self.engine = HarmonographEngine(config)
        self._x_range, self._y_range = self.engine.compute_ranges()
        self._speed_range = self.engine.compute_speed_range()
        self._position = 0
        self._paused = False

        # Ring buffers: deque with maxlen for auto-eviction
        self.combined_trail = deque(maxlen=trail_config.trail_length)
        self.pendulum_trails = [
            deque(maxlen=trail_config.pendulum_trail_lengths[i])
            for i in range(4)
        ]

    @property
    def speed_range(self):
        return self._speed_range

    @property
    def current_time(self):
        return self._position / self.config.sample_rate

    @property
    def is_paused(self):
        return self._paused

    def pause(self):
        self._paused = True

    def resume(self):
        self._paused = False

    def advance(self, steps: int = 20):
        """Compute the next batch of points and add to trail buffers.

        Returns (combined_x, combined_y, pendulum_points) for the current state.
        """
        if self._paused:
            return None

        env = self.config.envelope
        margin = 0.05
        m_x = self.width * margin
        m_y = self.height * margin

        x_min, x_max = self._x_range
        y_min, y_max = self._y_range
        x_span = x_max - x_min if x_max - x_min > 1e-10 else 1.0
        y_span = y_max - y_min if y_max - y_min > 1e-10 else 1.0

        for step in range(steps):
            t = self._position / self.config.sample_rate
            self._position += 1

            # Compute each pendulum's contribution
            pend_signals = []
            for i in range(4):
                p = self.config.pendulums[i]
                freq = p.frequency * 2 * np.pi
                phase = p.phase

                # FM
                if p.fm_depth > 0:
                    freq += p.fm_depth * 2 * np.pi * np.sin(p.fm_freq * 2 * np.pi * t)
                # PM
                if p.pm_depth > 0:
                    phase += p.pm_depth * np.sin(p.pm_freq * 2 * np.pi * t)

                signal = p.amplitude * np.sin(freq * t + phase)

                # Envelope
                envelope = HarmonographEngine._compute_envelope(
                    np.array([t]), p.damping, env
                )[0]
                signal *= envelope
                pend_signals.append(signal)

            # Combined position
            raw_x = pend_signals[0] + pend_signals[1]
            raw_y = pend_signals[2] + pend_signals[3]

            # Normalize to screen coords
            px = m_x + (raw_x - x_min) / x_span * (self.width - 2 * m_x)
            py = m_y + (raw_y - y_min) / y_span * (self.height - 2 * m_y)
            self.combined_trail.append((px, py))

            # Individual pendulum screen positions (each shown relative to center)
            cx = self.width / 2.0
            cy = self.height / 2.0
            scale_x = (self.width - 2 * m_x) / x_span * 0.5
            scale_y = (self.height - 2 * m_y) / y_span * 0.5

            # X pendulums: show as horizontal displacement from center
            self.pendulum_trails[0].append((cx + pend_signals[0] * scale_x, cy))
            self.pendulum_trails[1].append((cx + pend_signals[1] * scale_x, cy))
            # Y pendulums: show as vertical displacement from center
            self.pendulum_trails[2].append((cx, cy + pend_signals[2] * scale_y))
            self.pendulum_trails[3].append((cx, cy + pend_signals[3] * scale_y))

        return True

    def get_combined_points(self):
        """Return combined trail as (x_array, y_array)."""
        if not self.combined_trail:
            return np.array([]), np.array([])
        points = list(self.combined_trail)
        x = np.array([p[0] for p in points])
        y = np.array([p[1] for p in points])
        return x, y

    def get_pendulum_points(self, index: int):
        """Return a single pendulum's trail as (x_array, y_array)."""
        trail = self.pendulum_trails[index]
        if not trail:
            return np.array([]), np.array([])
        points = list(trail)
        x = np.array([p[0] for p in points])
        y = np.array([p[1] for p in points])
        return x, y
