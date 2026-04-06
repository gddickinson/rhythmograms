"""Parametric morphing — interpolate between two harmonograph configurations."""

from dataclasses import dataclass
from PyQt6.QtGui import QColor

from .pendulum import PendulumParams, HarmonographConfig, EnvelopeConfig
from effects.color import ColorConfig


def lerp(a: float, b: float, t: float) -> float:
    """Linear interpolation."""
    return a + t * (b - a)


def lerp_color(c1: QColor, c2: QColor, t: float) -> QColor:
    """Interpolate two QColors in RGB space."""
    return QColor(
        int(lerp(c1.red(), c2.red(), t)),
        int(lerp(c1.green(), c2.green(), t)),
        int(lerp(c1.blue(), c2.blue(), t)),
        int(lerp(c1.alpha(), c2.alpha(), t)),
    )


def morph_pendulum(p1: PendulumParams, p2: PendulumParams, t: float) -> PendulumParams:
    """Interpolate between two pendulum parameter sets."""
    return PendulumParams(
        frequency=lerp(p1.frequency, p2.frequency, t),
        phase=lerp(p1.phase, p2.phase, t),
        amplitude=lerp(p1.amplitude, p2.amplitude, t),
        damping=lerp(p1.damping, p2.damping, t),
    )


def morph_envelope(e1: EnvelopeConfig, e2: EnvelopeConfig, t: float) -> EnvelopeConfig:
    """Interpolate envelope configs. Mode switches at t=0.5."""
    return EnvelopeConfig(
        mode=e1.mode if t < 0.5 else e2.mode,
        frequency=lerp(e1.frequency, e2.frequency, t),
        strength=lerp(e1.strength, e2.strength, t),
    )


def morph_config(c1: HarmonographConfig, c2: HarmonographConfig,
                 t: float) -> HarmonographConfig:
    """Interpolate between two harmonograph configurations.

    t: 0.0 = fully c1, 1.0 = fully c2.
    """
    pendulums = [morph_pendulum(c1.pendulums[i], c2.pendulums[i], t) for i in range(4)]
    return HarmonographConfig(
        pendulums=pendulums,
        duration=lerp(c1.duration, c2.duration, t),
        sample_rate=max(c1.sample_rate, c2.sample_rate),
        envelope=morph_envelope(c1.envelope, c2.envelope, t),
    )


def morph_color_config(cc1: ColorConfig, cc2: ColorConfig, t: float) -> ColorConfig:
    """Interpolate between two color configurations."""
    return ColorConfig(
        line_color=lerp_color(cc1.line_color, cc2.line_color, t),
        bg_color=lerp_color(cc1.bg_color, cc2.bg_color, t),
        gradient_start=lerp_color(cc1.gradient_start, cc2.gradient_start, t),
        gradient_end=lerp_color(cc1.gradient_end, cc2.gradient_end, t),
        gradient_mid=lerp_color(cc1.gradient_mid, cc2.gradient_mid, t),
        use_gradient=cc1.use_gradient or cc2.use_gradient,
        use_mid_color=cc1.use_mid_color or cc2.use_mid_color,
        interpolation=cc1.interpolation if t < 0.5 else cc2.interpolation,
        line_alpha=int(lerp(cc1.line_alpha, cc2.line_alpha, t)),
        line_width=lerp(cc1.line_width, cc2.line_width, t),
        velocity_width=cc1.velocity_width or cc2.velocity_width,
        velocity_width_min=lerp(cc1.velocity_width_min, cc2.velocity_width_min, t),
        velocity_width_max=lerp(cc1.velocity_width_max, cc2.velocity_width_max, t),
        velocity_opacity=cc1.velocity_opacity or cc2.velocity_opacity,
        symmetry_order=int(lerp(cc1.symmetry_order, cc2.symmetry_order, t)),
    )
