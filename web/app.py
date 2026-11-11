"""FastAPI web app for the Rhythmogram Simulator: serves the front end in static/ and the JSON API under /api.

Run with `python run_web.py` (http://127.0.0.1:8122, local only). `scripts/build_static.py` exports every path in
STATIC_ENDPOINTS to JSON for the GitHub Pages site, so keep that list in step with the GET routes below.

Everything comes from the desktop app's own Qt-free modules: presets/*.json read with core.pendulum.HarmonographConfig,
effects.palettes, effects.style_defaults, the EffectsConfig / AtmosphereConfig / TrailConfig / Projection3DConfig
defaults, and core.harmonograph.HarmonographEngine for the Python reference traces used by the Cross-check page.
"""
import json
import math
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.harmonograph import HarmonographEngine  # noqa: E402
from core.pendulum import ENVELOPE_MODES, HarmonographConfig  # noqa: E402
from core.projection import Projection3DConfig  # noqa: E402
from core.trails import TrailConfig  # noqa: E402
from effects.atmosphere import AtmosphereConfig  # noqa: E402
from effects.palettes import PALETTES  # noqa: E402
from effects.postprocess import EffectsConfig  # noqa: E402
from effects.style_defaults import BRUSH_TYPES, COLOR_DEFAULTS  # noqa: E402

STATIC = Path(__file__).resolve().parent / "static"
PRESETS_DIR = ROOT / "presets"
TITLE = "Rhythmogram Simulator"
TRACE_POINTS = 600  # points of each Python reference trace sent to the Cross-check page

app = FastAPI(title=TITLE)
app.mount("/static", StaticFiles(directory=STATIC), name="static")


def _readme_intro():
    text = (ROOT / "README.md").read_text(encoding="utf-8").split("\n\n")
    return " ".join(text[1].split()), " ".join(text[2].split())


def _load_presets():
    """Presets as the desktop Preset tab loads them (gui/presets_panel.py): sorted by file, name or title-cased stem."""
    out = {}
    for path in sorted(PRESETS_DIR.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        name = data.get("name", path.stem.replace("_", " ").title())
        cfg = HarmonographConfig.from_dict(data)
        extras = {k: data[k] for k in ("color", "effects") if k in data}
        out[path.stem] = {"slug": path.stem, "name": name, "file": f"presets/{path.name}", "config": cfg.to_dict(),
                          "nonlinear": any(p.nonlinearity for p in cfg.pendulums), **extras}
    return out


PRESETS = _load_presets()
_TRACE_CACHE = {}


def _clean(v):
    return None if v is None or (isinstance(v, float) and math.isnan(v)) else float(v)


def reference_trace(cfg: HarmonographConfig, points: int = TRACE_POINTS) -> dict:
    """compute_full() of the Python engine, sampled at `points` evenly spaced indices (NaN = strobe blanking)."""
    eng = HarmonographEngine(cfg)
    x, y = eng.compute_full()
    n = len(x)
    idx = sorted({round(i * (n - 1) / (points - 1)) for i in range(points)}) if n > 1 else list(range(n))
    xr, yr = eng.compute_ranges()
    return {"n": n, "idx": idx, "x": [_clean(x[i]) for i in idx], "y": [_clean(y[i]) for i in idx],
            "x_range": [float(v) for v in xr], "y_range": [float(v) for v in yr],
            "speed_range": list(eng.compute_speed_range()), "nan_count": int(sum(1 for v in x if v != v)),
            "source": "core.harmonograph.HarmonographEngine.compute_full (NumPy)"}


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/api/info")
def info():
    """Project summary and counts for the home page (text from the README)."""
    intro, desktop = _readme_intro()
    return {"title": TITLE, "version": "1", "intro": intro, "desktop": desktop, "presets": len(PRESETS),
            "palettes": len(PALETTES), "brushes": len(BRUSH_TYPES), "envelope_modes": len(ENVELOPE_MODES) - 1,
            "nonlinear_presets": sum(p["nonlinear"] for p in PRESETS.values()), "pendulums": 4}


@app.get("/api/presets")
def presets():
    """All built-in presets (presets/*.json) with their full HarmonographConfig."""
    return {"presets": list(PRESETS.values())}


@app.get("/api/palettes")
def palettes():
    """The curated palettes of effects/palettes.py."""
    return {"palettes": [{"name": p.name, "bg": p.bg, "start": p.start, "mid": p.mid, "end": p.end,
                          "interpolation": p.interpolation, "description": p.description} for p in PALETTES]}


@app.get("/api/defaults")
def defaults():
    """Default settings of every config dataclass, plus the envelope modes and brush types."""
    return {"harmonograph": HarmonographConfig().to_dict(), "color": COLOR_DEFAULTS,
            "effects": EffectsConfig().to_dict(), "atmosphere": AtmosphereConfig().to_dict(),
            "trail": TrailConfig().to_dict(), "projection": Projection3DConfig().to_dict(),
            "envelope_modes": ENVELOPE_MODES, "brush_types": BRUSH_TYPES}


@app.get("/api/trace/{slug}")
def trace(slug: str):
    """Python reference trace of a preset, for comparing with the browser engine."""
    if slug not in PRESETS:
        raise HTTPException(404, f"unknown preset {slug!r}")
    if slug not in _TRACE_CACHE:  # the Duffing presets take seconds (pure-Python RK4 loop)
        _TRACE_CACHE[slug] = {"slug": slug, **reference_trace(HarmonographConfig.from_dict(PRESETS[slug]["config"]))}
    return _TRACE_CACHE[slug]


@app.post("/api/trace")
def trace_custom(config: dict):
    """Python reference trace of any configuration (local app only: the Studio's current settings)."""
    try:
        cfg = HarmonographConfig.from_dict(config)
    except (KeyError, TypeError, ValueError) as e:
        raise HTTPException(422, f"bad config: {e}")
    if cfg.total_points > 400_000 or cfg.total_points < 2 or cfg.chorus_count > 8:
        raise HTTPException(422, "duration x sample rate must be 2..400000 and chorus_count <= 8")
    return reference_trace(cfg)


# GET paths (without the /api prefix) written to the static site as api/<path>.json.
STATIC_ENDPOINTS = ["/info", "/presets", "/palettes", "/defaults"] + [f"/trace/{s}" for s in PRESETS]
