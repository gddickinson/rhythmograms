"""3D projection for harmonograph traces — adds depth via Z-axis pendulums."""

from dataclasses import dataclass, field
from typing import List
import numpy as np
import math

from .pendulum import PendulumParams


@dataclass
class Projection3DConfig:
    """Configuration for optional 3D depth projection.

    Adds two Z-axis pendulums. The resulting z(t) is used for perspective
    projection: x' = f*x/(z+f), y' = f*y/(z+f).
    """
    enabled: bool = False
    z_pendulums: List[PendulumParams] = field(default_factory=lambda: [
        PendulumParams(frequency=1.5, phase=0.0, amplitude=0.5, damping=0.01),
        PendulumParams(frequency=2.51, phase=1.0, amplitude=0.3, damping=0.015),
    ])
    focal_length: float = 3.0       # perspective strength (higher = less distortion)
    rotation_x: float = 0.0         # viewing angle around X axis (radians)
    rotation_y: float = 0.0         # viewing angle around Y axis (radians)
    auto_rotate: bool = False       # slowly rotate viewing angle over time
    auto_rotate_speed: float = 0.02 # radians per second

    def to_dict(self) -> dict:
        return {
            "enabled": self.enabled,
            "z_pendulums": [p.to_dict() for p in self.z_pendulums],
            "focal_length": self.focal_length,
            "rotation_x": self.rotation_x,
            "rotation_y": self.rotation_y,
            "auto_rotate": self.auto_rotate,
            "auto_rotate_speed": self.auto_rotate_speed,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Projection3DConfig":
        z_pend = [PendulumParams.from_dict(p) for p in d.get("z_pendulums", [])]
        return cls(
            enabled=d.get("enabled", False),
            z_pendulums=z_pend if len(z_pend) == 2 else cls().z_pendulums,
            focal_length=d.get("focal_length", 3.0),
            rotation_x=d.get("rotation_x", 0.0),
            rotation_y=d.get("rotation_y", 0.0),
            auto_rotate=d.get("auto_rotate", False),
            auto_rotate_speed=d.get("auto_rotate_speed", 0.02),
        )


def compute_z(t: np.ndarray, z_pendulums: List[PendulumParams],
              envelope_func=None) -> np.ndarray:
    """Compute z(t) from two Z-axis pendulums."""
    z = np.zeros_like(t)
    for p in z_pendulums:
        freq = p.frequency * 2 * math.pi
        signal = p.amplitude * np.sin(freq * t + p.phase) * np.exp(-p.damping * t)
        if envelope_func is not None:
            signal = signal * envelope_func(t, p.damping)
        z += signal
    return z


def apply_perspective(x: np.ndarray, y: np.ndarray, z: np.ndarray,
                      focal: float, rot_x: float = 0.0,
                      rot_y: float = 0.0) -> tuple:
    """Apply 3D rotation and perspective projection.

    Returns projected (x', y') arrays.
    """
    # Rotation around Y axis
    if abs(rot_y) > 1e-6:
        cos_y, sin_y = math.cos(rot_y), math.sin(rot_y)
        x2 = x * cos_y + z * sin_y
        z2 = -x * sin_y + z * cos_y
        x, z = x2, z2

    # Rotation around X axis
    if abs(rot_x) > 1e-6:
        cos_x, sin_x = math.cos(rot_x), math.sin(rot_x)
        y2 = y * cos_x - z * sin_x
        z2 = y * sin_x + z * cos_x
        y, z = y2, z2

    # Perspective projection
    denom = z + focal
    denom = np.where(np.abs(denom) < 0.01, 0.01, denom)
    x_proj = focal * x / denom
    y_proj = focal * y / denom

    return x_proj, y_proj
