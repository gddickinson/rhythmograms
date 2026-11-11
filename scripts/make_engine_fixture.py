"""Compute reference numbers with the repo's Python code for the node tests of the JS engine.

Writes tests/fixtures/engine_fixture.json, read by web/static/harmonograph_engine.test.mjs (engine, trails, projection)
and web/static/postfx.test.mjs (colours, post-processing, atmosphere). tests/test_web.py recomputes the fixture and
checks it is still current, so the JS is always compared with the current Python.

Sections "colors" and "morph" need PyQt6 (effects/color.py and core/morph.py use QColor); without PyQt6 they are
copied over unchanged from the existing fixture and the currency test skips them.

Run: python scripts/make_engine_fixture.py            (print a summary)
     python scripts/make_engine_fixture.py --write    (rewrite tests/fixtures/engine_fixture.json)
"""
import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.harmonograph import HarmonographEngine  # noqa: E402
from core.pendulum import EnvelopeConfig, HarmonographConfig  # noqa: E402
from core.projection import apply_perspective, compute_z, Projection3DConfig  # noqa: E402
from core.trails import TrailBuffer, TrailConfig  # noqa: E402
from effects import atmosphere as atm  # noqa: E402
from effects import postprocess as pp  # noqa: E402

FIXTURE = ROOT / "tests" / "fixtures" / "engine_fixture.json"
NONLINEAR_SECONDS = 6.0   # Duffing presets are cut to their first seconds (pure-Python RK4 is slow)
SAMPLES = 31


def _num(v):
    v = float(v)
    return None if math.isnan(v) else v


def _p(**kw):
    base = dict(frequency=2.0, phase=0.3, amplitude=1.0, damping=0.01)
    base.update(kw)
    return base


SYNTHETIC = {
    "fm_pm": {"pendulums": [_p(fm_freq=0.3, fm_depth=0.4), _p(frequency=3.01, pm_freq=0.2, pm_depth=1.2),
                            _p(frequency=3.0, fm_freq=0.1, fm_depth=0.2, pm_freq=0.35, pm_depth=0.6), _p(frequency=2.02)],
              "duration": 20.0, "sample_rate": 400.0},
    "breathe": {"pendulums": [_p(), _p(frequency=3.01), _p(frequency=3.0), _p(frequency=2.01)], "duration": 25.0,
                "sample_rate": 300.0, "envelope": {"mode": "breathe", "frequency": 0.13, "strength": 0.8}},
    "pulse": {"pendulums": [_p(), _p(frequency=5.0), _p(frequency=4.0), _p(frequency=1.01)], "duration": 25.0,
              "sample_rate": 300.0, "envelope": {"mode": "pulse", "frequency": 0.21, "strength": 0.6}},
    "bounce_strobe": {"pendulums": [_p(), _p(frequency=3.01), _p(frequency=3.0), _p(frequency=2.01)], "duration": 25.0,
                      "sample_rate": 300.0, "envelope": {"mode": "bounce", "frequency": 0.09, "strength": 0.7},
                      "strobe_freq": 2.7, "strobe_duty": 0.45},
    "chorus": {"pendulums": [_p(), _p(frequency=4.01), _p(frequency=3.0), _p(frequency=2.0)], "duration": 15.0,
               "sample_rate": 400.0, "chorus_count": 4, "chorus_spread": 0.035},
    "duffing_fm_chorus": {"pendulums": [_p(nonlinearity=0.3, fm_freq=0.2, fm_depth=0.3), _p(frequency=3.0),
                                        _p(frequency=1.5, nonlinearity=0.1), _p(frequency=2.5, damping=0.02)],
                          "duration": 8.0, "sample_rate": 250.0, "chorus_count": 3, "chorus_spread": 0.02,
                          "envelope": {"mode": "breathe", "frequency": 0.2, "strength": 0.5}},
    "duffing_phase_pm": {"pendulums": [_p(phase=1.1, nonlinearity=0.25, pm_freq=0.3, pm_depth=1.0),
                                       _p(frequency=3.01, phase=2.0, pm_freq=0.2, pm_depth=0.7), _p(frequency=0.0, amplitude=0.0),
                                       _p(frequency=1.5, phase=4.0, nonlinearity=0.05)],
                         "duration": 6.0, "sample_rate": 300.0, "strobe_freq": 1.3, "strobe_duty": 0.7},
}


def trace_case(cfg: HarmonographConfig):
    eng = HarmonographEngine(cfg)
    x, y = eng.compute_full()
    n = len(x)
    idx = sorted({round(i * (n - 1) / (SAMPLES - 1)) for i in range(SAMPLES)} | {1, 2, n - 2})
    return {"config": cfg.to_dict(), "n": n, "idx": idx, "x": [_num(x[i]) for i in idx], "y": [_num(y[i]) for i in idx],
            "ranges": [list(map(float, r)) for r in eng.compute_ranges()], "speed_range": list(eng.compute_speed_range()),
            "nan_count": int(np.isnan(x).sum()), "sum_x": float(np.nansum(x)), "sum_y": float(np.nansum(y))}


def traces():
    out = {}
    for path in sorted((ROOT / "presets").glob("*.json")):
        cfg = HarmonographConfig.from_dict(json.loads(path.read_text(encoding="utf-8")))
        if any(p.nonlinearity for p in cfg.pendulums):
            cfg.duration = NONLINEAR_SECONDS
        out[path.stem] = trace_case(cfg)
    for name, d in SYNTHETIC.items():
        out[name] = trace_case(HarmonographConfig.from_dict(d))
    return out


def chunks():
    out = []
    for name, start, size, unbounded in [("fm_pm", 0, 300, False), ("fm_pm", 7900, 300, False), ("fm_pm", 9000, 300, True),
                                         ("bounce_strobe", 7200, 300, True), ("chorus", 5950, 100, False),
                                         ("duffing_fm_chorus", 300, 300, True), ("duffing_fm_chorus", 900, 300, False),
                                         ("duffing_fm_chorus", 1950, 400, True), ("duffing_phase_pm", 2100, 300, True)]:
        cfg = HarmonographConfig.from_dict(SYNTHETIC[name])
        x, y = HarmonographEngine(cfg).compute_chunk(start, size, unbounded=unbounded)
        out.append({"name": name, "start": start, "size": size, "unbounded": unbounded, "len": len(x),
                    "x": [_num(v) for v in x[::37]], "y": [_num(v) for v in y[::37]]})
    return out


def envelopes():
    t = np.array([0.0, 0.37, 2.5, 7.77, 19.9, 41.0])
    out = []
    for mode in ["none", "breathe", "pulse", "bounce"]:
        for f, s in [(0.1, 0.7), (0.0, 0.5), (0.33, 1.0)]:
            env = EnvelopeConfig(mode=mode, frequency=f, strength=s)
            out.append({"mode": mode, "frequency": f, "strength": s, "damping": 0.013, "t": t.tolist(),
                        "v": HarmonographEngine._compute_envelope(t, 0.013, env).tolist()})
    return out


def projection():
    proj = Projection3DConfig()
    t = np.linspace(0, 12, 9)
    z = compute_z(t, proj.z_pendulums)
    x, y = np.cos(t), np.sin(1.3 * t)
    cases = []
    for focal, rx, ry in [(3.0, 0.0, 0.0), (1.5, 0.4, -0.7), (0.5, 2.0, 1.0)]:
        xp, yp = apply_perspective(x, y, z, focal, rx, ry)
        cases.append({"focal": focal, "rx": rx, "ry": ry, "x": xp.tolist(), "y": yp.tolist()})
    return {"z_pendulums": [p.to_dict() for p in proj.z_pendulums], "t": t.tolist(), "z": z.tolist(), "cases": cases}


def trails():
    cfg = HarmonographConfig.from_dict(SYNTHETIC["fm_pm"])
    tc = TrailConfig(trail_length=50, pendulum_trail_lengths=[10, 20, 30, 40])
    tb = TrailBuffer(cfg, tc, 640, 480)
    for _ in range(6):
        tb.advance(steps=25)
    return {"name": "fm_pm", "width": 640, "height": 480, "trail": tc.to_dict(), "steps": 150,
            "combined": [list(map(float, p)) for p in tb.combined_trail],
            "pendulums": [[list(map(float, p)) for p in tr] for tr in tb.pendulum_trails]}


def test_image(h=18, w=22):
    """Deterministic BGRA test image: a bright diagonal line, a blob and a gradient (alpha 255)."""
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    b = 40 + 200 * np.exp(-((xx - 6) ** 2 + (yy - 5) ** 2) / 8)
    g = 255 * (np.abs(xx - yy) < 1.5) + 30 * xx / w
    r = 120 + 100 * np.sin(xx / 3) * np.cos(yy / 4)
    arr = np.stack([b, g, r, np.full_like(b, 255)], axis=2)
    return np.clip(arr, 0, 255).astype(np.uint8)


def postfx():
    img = test_image()
    res = {"h": img.shape[0], "w": img.shape[1], "input": img.ravel().tolist()}
    ops = {
        "invert": lambda a: pp.apply_invert(a),
        "solarize": lambda a: pp.apply_solarize(a, 140),
        "bloom1": lambda a: pp.apply_bloom(a, 2, 0.5, 1),
        "bloom3": lambda a: pp.apply_bloom(a, 1, 0.7, 3),
        "vignette": lambda a: pp.apply_vignette(a, 0.8),
        "grading": lambda a: atm.apply_color_grading(a, (0, 3, 10), (10, 5, 0), 1.3, 0.6),
        "chromatic": lambda a: atm.apply_chromatic_aberration(a, 40.0),
        "heat": lambda a: atm.apply_heat_distortion(a, 2.5, 0.07),
        "rays": lambda a: atm.apply_god_rays(a, 0.9, 24, 0.95),
        "fastblur": lambda a: np.clip(atm._fast_blur_rgb(a[:, :, :3], 2), 0, 255),
    }
    for k, fn in ops.items():
        res[k] = np.asarray(fn(img.copy()), dtype=np.float64).ravel().tolist()
    return res


def colors():
    from PyQt6.QtGui import QColor
    from effects.color import ColorConfig
    from effects.palettes import PALETTES
    ts = [0.0, 0.1, 0.25, 0.49, 0.5, 0.77, 1.0]
    out = []
    for p in PALETTES:
        for interp in ["rgb", "hsv"]:
            cc = ColorConfig(gradient_start=QColor(p.start), gradient_end=QColor(p.end),
                             gradient_mid=QColor(p.mid or "#808080"), use_gradient=True,
                             use_mid_color=bool(p.mid), interpolation=interp, line_alpha=170)
            cols = [cc.color_at(t) for t in ts]
            out.append({"start": p.start, "mid": p.mid, "end": p.end, "interpolation": interp, "t": ts,
                        "rgba": [[c.red(), c.green(), c.blue(), c.alpha()] for c in cols]})
    cc = ColorConfig(velocity_width=True, velocity_opacity=True)
    speed = [0.0, 0.3, 0.9, 1.0]
    return {"gradients": out, "speed": speed, "width": [cc.width_at_speed(s) for s in speed],
            "alpha": [cc.alpha_at_speed(s) for s in speed]}


def morph():
    from core.morph import morph_config
    a = HarmonographConfig.from_dict(SYNTHETIC["breathe"])
    b = HarmonographConfig.from_dict(SYNTHETIC["pulse"])
    return [{"t": t, "a": a.to_dict(), "b": b.to_dict(), "out": morph_config(a, b, t).to_dict()} for t in (0.0, 0.3, 0.5, 1.0)]


def qt_available():
    try:
        import PyQt6.QtGui  # noqa: F401
        return True
    except ImportError:
        return False


def fixture(with_qt=None):
    out = {"traces": traces(), "chunks": chunks(), "envelopes": envelopes(), "projection": projection(),
           "trails": trails(), "postfx": postfx()}
    if with_qt is None:
        with_qt = qt_available()
    if with_qt:
        out["colors"], out["morph"] = colors(), morph()
    elif FIXTURE.exists():
        old = json.loads(FIXTURE.read_text())
        out["colors"], out["morph"] = old.get("colors"), old.get("morph")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    fx = fixture()
    if a.write:
        FIXTURE.parent.mkdir(parents=True, exist_ok=True)
        FIXTURE.write_text(json.dumps(fx, separators=(",", ":")))
        print(f"wrote {FIXTURE} ({FIXTURE.stat().st_size / 1e3:.0f} kB)")
    print({k: len(v) if hasattr(v, "__len__") else v for k, v in fx.items()})


if __name__ == "__main__":
    main()
