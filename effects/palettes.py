"""Curated color palettes for rhythmogram rendering."""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Palette:
    """A named color palette with background, gradient colors, and interpolation."""
    name: str
    bg: str               # hex background color
    start: str            # hex gradient start
    mid: Optional[str]    # hex gradient mid (None = 2-stop)
    end: str              # hex gradient end
    interpolation: str    # "rgb" or "hsv"
    description: str


PALETTES: List[Palette] = [
    Palette(
        name="Classic Silver",
        bg="#05050f",
        start="#b0c4de",
        mid=None,
        end="#e8e8f0",
        interpolation="rgb",
        description="Authentic Heidersberger silver-on-black",
    ),
    Palette(
        name="Neon Plasma",
        bg="#050510",
        start="#00ffff",
        mid="#ff00ff",
        end="#ffff00",
        interpolation="hsv",
        description="Electric neon rainbow cycling through HSV",
    ),
    Palette(
        name="Gold on Navy",
        bg="#0a0a2e",
        start="#ffd700",
        mid=None,
        end="#ff8c00",
        interpolation="rgb",
        description="Warm gold traces on deep navy",
    ),
    Palette(
        name="Sunset Ember",
        bg="#1a0a0a",
        start="#ff4500",
        mid="#ff8c00",
        end="#ffd700",
        interpolation="rgb",
        description="Warm sunset gradients from red to gold",
    ),
    Palette(
        name="Cool Moonlight",
        bg="#050a14",
        start="#4169e1",
        mid="#87ceeb",
        end="#e0e8ff",
        interpolation="rgb",
        description="Cool blue moonlit traces",
    ),
    Palette(
        name="Aurora Borealis",
        bg="#050f0a",
        start="#00ff88",
        mid="#00aaff",
        end="#ff00aa",
        interpolation="hsv",
        description="Northern lights color sweep",
    ),
    Palette(
        name="Rose Gold",
        bg="#0f0808",
        start="#ff6b9d",
        mid="#ffa07a",
        end="#ffd700",
        interpolation="rgb",
        description="Elegant rose gold to warm gold",
    ),
    Palette(
        name="Deep Ocean",
        bg="#020a14",
        start="#001a66",
        mid="#0077b6",
        end="#00e5ff",
        interpolation="rgb",
        description="Deep sea blue emerging into cyan",
    ),
    Palette(
        name="Spectral",
        bg="#080808",
        start="#ff0000",
        mid=None,
        end="#0000ff",
        interpolation="hsv",
        description="Full visible spectrum via HSV sweep",
    ),
    Palette(
        name="Emerald Fire",
        bg="#0a0f05",
        start="#00ff00",
        mid="#ffff00",
        end="#ff4400",
        interpolation="rgb",
        description="Green to yellow to fiery orange",
    ),
]


def get_palette(name: str) -> Optional[Palette]:
    """Look up a palette by name."""
    for p in PALETTES:
        if p.name == name:
            return p
    return None


def palette_names() -> List[str]:
    """Return list of all palette names."""
    return [p.name for p in PALETTES]
