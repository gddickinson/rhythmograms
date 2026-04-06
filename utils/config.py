"""JSON save/load for full application state."""

import json
from pathlib import Path

from core.pendulum import HarmonographConfig
from effects.color import ColorConfig
from effects.postprocess import EffectsConfig


def save_config(path: str, harmonograph: HarmonographConfig,
                color: ColorConfig, effects: EffectsConfig):
    """Save all configuration to a JSON file."""
    data = {
        "version": 1,
        **harmonograph.to_dict(),
        "color": color.to_dict(),
        "effects": effects.to_dict(),
    }
    Path(path).write_text(json.dumps(data, indent=2))


def load_config(path: str) -> tuple:
    """Load configuration from a JSON file.

    Returns (HarmonographConfig, ColorConfig, EffectsConfig).
    """
    data = json.loads(Path(path).read_text())
    harmonograph = HarmonographConfig.from_dict(data)
    color = ColorConfig.from_dict(data.get("color", {}))
    effects = EffectsConfig.from_dict(data.get("effects", {}))
    return harmonograph, color, effects
