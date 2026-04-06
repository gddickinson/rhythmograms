"""Pendulum parameter dataclasses for the 4-pendulum damped harmonograph.

Supports frequency/phase modulation, Duffing nonlinearity, light extinction,
and multi-trace chorus.
"""

from dataclasses import dataclass, field, asdict
from typing import List
import random
import math


@dataclass
class PendulumParams:
    """Parameters for a single pendulum with optional FM/PM and nonlinearity."""
    frequency: float = 1.0      # Hz
    phase: float = 0.0          # radians (0 to 2*pi)
    amplitude: float = 1.0      # normalized (0 to 1)
    damping: float = 0.01       # decay rate

    # Frequency modulation: freq(t) = f0 + fm_depth * sin(2*pi*fm_freq*t)
    fm_freq: float = 0.0        # FM modulator frequency (Hz), 0 = off
    fm_depth: float = 0.0       # FM modulation depth (Hz)

    # Phase modulation: phase(t) = p0 + pm_depth * sin(2*pi*pm_freq*t)
    pm_freq: float = 0.0        # PM modulator frequency (Hz), 0 = off
    pm_depth: float = 0.0       # PM modulation depth (radians)

    # Duffing nonlinearity: adds cubic term to restoring force
    nonlinearity: float = 0.0   # 0 = linear, >0 = hardening spring

    def to_dict(self) -> dict:
        return {
            "frequency": self.frequency, "phase": self.phase,
            "amplitude": self.amplitude, "damping": self.damping,
            "fm_freq": self.fm_freq, "fm_depth": self.fm_depth,
            "pm_freq": self.pm_freq, "pm_depth": self.pm_depth,
            "nonlinearity": self.nonlinearity,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "PendulumParams":
        fields = {k for k in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in d.items() if k in fields})

    @classmethod
    def random(cls) -> "PendulumParams":
        return cls(
            frequency=random.uniform(0.5, 8.0),
            phase=random.uniform(0, 2 * math.pi),
            amplitude=random.uniform(0.3, 1.0),
            damping=random.uniform(0.001, 0.05),
        )

    @classmethod
    def smart_random(cls, base_freq: float = None,
                     use_advanced: bool = False) -> "PendulumParams":
        """Random params with near-integer frequency ratio for aesthetic results.

        If use_advanced=True, may add FM/PM modulation and nonlinearity.
        """
        if base_freq is None:
            base_freq = random.choice([1.0, 1.5, 2.0])
        ratio = random.choice([1, 2, 3, 4, 5, 6])
        detune = random.uniform(-0.02, 0.02)
        freq = base_freq * ratio + detune

        kwargs = dict(
            frequency=max(0.5, min(12.0, freq)),
            phase=random.uniform(0, 2 * math.pi),
            amplitude=random.uniform(0.4, 1.0),
            damping=random.uniform(0.005, 0.03),
        )

        if use_advanced:
            # ~40% chance of FM
            if random.random() < 0.4:
                kwargs["fm_freq"] = random.uniform(0.05, 0.5)
                kwargs["fm_depth"] = random.uniform(0.1, 0.5)
            # ~30% chance of PM
            if random.random() < 0.3:
                kwargs["pm_freq"] = random.uniform(0.05, 0.4)
                kwargs["pm_depth"] = random.uniform(0.3, 1.5)
            # ~20% chance of nonlinearity
            if random.random() < 0.2:
                kwargs["nonlinearity"] = random.uniform(0.05, 0.3)

        return cls(**kwargs)


ENVELOPE_MODES = ["none", "breathe", "pulse", "bounce"]


@dataclass
class EnvelopeConfig:
    """Envelope modulation that modifies the damping behavior over time."""
    mode: str = "none"
    frequency: float = 0.1
    strength: float = 0.7

    def to_dict(self) -> dict:
        return {"mode": self.mode, "frequency": self.frequency,
                "strength": self.strength}

    @classmethod
    def from_dict(cls, d: dict) -> "EnvelopeConfig":
        return cls(mode=d.get("mode", "none"), frequency=d.get("frequency", 0.1),
                   strength=d.get("strength", 0.7))


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
    duration: float = 60.0
    sample_rate: float = 1000.0
    envelope: EnvelopeConfig = field(default_factory=EnvelopeConfig)

    # Light extinction / duty cycle
    strobe_freq: float = 0.0    # Hz, 0 = off (always on)
    strobe_duty: float = 0.5    # 0.0-1.0 fraction of cycle that trace is visible

    # Multi-trace chorus
    chorus_count: int = 1       # 1 = off, 2-8 = number of detuned copies
    chorus_spread: float = 0.02 # frequency spread between copies

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
            "envelope": self.envelope.to_dict(),
            "strobe_freq": self.strobe_freq,
            "strobe_duty": self.strobe_duty,
            "chorus_count": self.chorus_count,
            "chorus_spread": self.chorus_spread,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "HarmonographConfig":
        envelope = EnvelopeConfig.from_dict(d["envelope"]) if "envelope" in d else EnvelopeConfig()
        return cls(
            pendulums=[PendulumParams.from_dict(p) for p in d["pendulums"]],
            duration=d.get("duration", 60.0),
            sample_rate=d.get("sample_rate", 1000.0),
            envelope=envelope,
            strobe_freq=d.get("strobe_freq", 0.0),
            strobe_duty=d.get("strobe_duty", 0.5),
            chorus_count=d.get("chorus_count", 1),
            chorus_spread=d.get("chorus_spread", 0.02),
        )

    @classmethod
    def random(cls) -> "HarmonographConfig":
        return cls(pendulums=[PendulumParams.random() for _ in range(4)])

    @classmethod
    def smart_random(cls, use_advanced: bool = False) -> "HarmonographConfig":
        """Generate aesthetically pleasing random config.

        If use_advanced=True, may include FM/PM, nonlinearity, strobe, chorus.
        """
        base = random.choice([1.0, 1.5, 2.0])
        kwargs = dict(
            pendulums=[PendulumParams.smart_random(base, use_advanced) for _ in range(4)],
        )

        if use_advanced:
            # ~30% chance of strobe
            if random.random() < 0.3:
                kwargs["strobe_freq"] = random.choice([1.0, 2.0, 3.0, 5.0, 8.0])
                kwargs["strobe_duty"] = random.uniform(0.4, 0.8)
            # ~25% chance of chorus
            if random.random() < 0.25:
                kwargs["chorus_count"] = random.choice([2, 3, 4, 5])
                kwargs["chorus_spread"] = random.uniform(0.01, 0.05)
            # ~25% chance of envelope
            if random.random() < 0.25:
                kwargs["envelope"] = EnvelopeConfig(
                    mode=random.choice(["breathe", "pulse", "bounce"]),
                    frequency=random.uniform(0.05, 0.2),
                    strength=random.uniform(0.3, 0.8),
                )

        return cls(**kwargs)
