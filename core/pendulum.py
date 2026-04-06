"""Pendulum parameter dataclasses for the 4-pendulum damped harmonograph."""

from dataclasses import dataclass, field, asdict
from typing import List
import random
import math


@dataclass
class PendulumParams:
    """Parameters for a single pendulum."""
    frequency: float = 1.0    # Hz
    phase: float = 0.0        # radians (0 to 2*pi)
    amplitude: float = 1.0    # normalized (0 to 1)
    damping: float = 0.01     # decay rate (0 = no decay, higher = faster decay)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "PendulumParams":
        return cls(**d)

    @classmethod
    def random(cls) -> "PendulumParams":
        return cls(
            frequency=random.uniform(0.5, 8.0),
            phase=random.uniform(0, 2 * math.pi),
            amplitude=random.uniform(0.3, 1.0),
            damping=random.uniform(0.001, 0.05),
        )


@dataclass
class HarmonographConfig:
    """Full configuration for a 4-pendulum harmonograph.

    Pendulums 0-1 drive the X axis, pendulums 2-3 drive the Y axis.
    """
    pendulums: List[PendulumParams] = field(default_factory=lambda: [
        PendulumParams(frequency=2.0, phase=0.0, amplitude=1.0, damping=0.01),
        PendulumParams(frequency=3.01, phase=0.5, amplitude=0.5, damping=0.015),
        PendulumParams(frequency=3.0, phase=1.5, amplitude=1.0, damping=0.01),
        PendulumParams(frequency=2.01, phase=0.0, amplitude=0.5, damping=0.015),
    ])
    duration: float = 60.0       # seconds
    sample_rate: float = 1000.0  # points per second

    def __post_init__(self):
        if len(self.pendulums) != 4:
            raise ValueError("Exactly 4 pendulums required")

    @property
    def total_points(self) -> int:
        return int(self.duration * self.sample_rate)

    def to_dict(self) -> dict:
        return {
            "pendulums": [p.to_dict() for p in self.pendulums],
            "duration": self.duration,
            "sample_rate": self.sample_rate,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "HarmonographConfig":
        return cls(
            pendulums=[PendulumParams.from_dict(p) for p in d["pendulums"]],
            duration=d.get("duration", 60.0),
            sample_rate=d.get("sample_rate", 1000.0),
        )

    @classmethod
    def random(cls) -> "HarmonographConfig":
        return cls(pendulums=[PendulumParams.random() for _ in range(4)])
