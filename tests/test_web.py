"""Web interface tests: every exported endpoint answers, the static build is complete, and the JS engine tests pass.

Run: python -m pytest -q tests/test_web.py
"""
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from web.app import STATIC, STATIC_ENDPOINTS, app  # noqa: E402

client = TestClient(app)


def test_index_served():
    r = client.get("/")
    assert r.status_code == 200 and "static/main.js" in r.text


@pytest.mark.parametrize("path", STATIC_ENDPOINTS)
def test_endpoint(path):
    r = client.get("/api" + path)
    assert r.status_code == 200, r.text
    assert r.json() is not None


def test_static_build(tmp_path):
    sys.path.insert(0, str(ROOT / "scripts"))
    import build_static
    build_static.build(tmp_path / "site")
    assert (tmp_path / "site" / "index.html").read_text().count("APP_STATIC") == 1
    for path in STATIC_ENDPOINTS:
        assert (tmp_path / "site" / "api" / (path.strip("/") + ".json")).exists()


def test_static_assets_referenced_exist():
    html = (STATIC / "index.html").read_text()
    for name in ("style.css", "main.js"):
        assert f"static/{name}" in html and (STATIC / name).exists()


@pytest.mark.skipif(not shutil.which("node"), reason="node not installed")
def test_js_engine():
    tests = sorted(STATIC.glob("*.test.mjs"))
    for t in tests:
        r = subprocess.run(["node", str(t)], capture_output=True, text=True)
        assert r.returncode == 0, r.stdout + r.stderr


# --- Rhythmogram-specific tests -------------------------------------------------------------------------------------
import json  # noqa: E402
import re  # noqa: E402

import numpy as np  # noqa: E402

from core.harmonograph import HarmonographEngine  # noqa: E402
from core.pendulum import HarmonographConfig  # noqa: E402
from effects.palettes import PALETTES  # noqa: E402


def test_presets_come_from_files():
    d = client.get("/api/presets").json()["presets"]
    files = sorted((ROOT / "presets").glob("*.json"))
    assert [p["slug"] for p in d] == [f.stem for f in files]
    for p, f in zip(d, files):
        assert p["config"] == HarmonographConfig.from_dict(json.loads(f.read_text())).to_dict()
    assert client.get("/api/info").json()["presets"] == len(files)


def test_palettes_and_defaults():
    assert [p["name"] for p in client.get("/api/palettes").json()["palettes"]] == [p.name for p in PALETTES]
    d = client.get("/api/defaults").json()
    assert d["harmonograph"] == HarmonographConfig().to_dict() and d["envelope_modes"][0] == "none"
    assert d["brush_types"] == ["line", "dot", "airbrush", "chalk", "ribbon"]


def test_color_defaults_match_colorconfig():
    """effects/style_defaults.py is what ColorConfig uses (checked where PyQt6 is installed)."""
    pytest.importorskip("PyQt6.QtGui")
    from effects.color import ColorConfig
    assert ColorConfig().to_dict() == client.get("/api/defaults").json()["color"]


def test_trace_matches_engine():
    r = client.get("/api/trace/supernova").json()
    x, _ = HarmonographEngine(HarmonographConfig.from_dict(json.loads((ROOT / "presets/supernova.json").read_text()))).compute_full()
    assert r["n"] == len(x) and np.allclose([x[i] for i in r["idx"]], r["x"])
    assert client.get("/api/trace/nope").status_code == 404


def test_trace_post():
    cfg = HarmonographConfig(duration=5.0, strobe_freq=2.0).to_dict()
    r = client.post("/api/trace", json=cfg).json()
    assert r["n"] == 5000 and r["nan_count"] > 0
    assert client.post("/api/trace", json={"pendulums": []}).status_code == 422
    assert client.post("/api/trace", json={**cfg, "duration": 1e6}).status_code == 422


def _close(a, b, path=""):
    if isinstance(a, dict):
        assert a.keys() == b.keys(), path
        for k in a:
            _close(a[k], b[k], f"{path}.{k}")
    elif isinstance(a, list):
        assert len(a) == len(b), path
        for i, (u, v) in enumerate(zip(a, b)):
            _close(u, v, f"{path}[{i}]")
    elif isinstance(a, float) or isinstance(b, float):
        assert (a is None and b is None) or abs(a - b) <= 1e-9 * max(1.0, abs(b)) + (1.0 if "postfx" in path else 0), path
    else:
        assert a == b, path


def test_js_fixture_is_current():
    """tests/fixtures/engine_fixture.json (read by the node tests) still matches the Python code."""
    sys.path.insert(0, str(ROOT / "scripts"))
    import make_engine_fixture as mf
    emb = json.loads(mf.FIXTURE.read_text())
    now = mf.fixture(with_qt=mf.qt_available())
    for key in ["traces", "chunks", "envelopes", "projection", "trails", "postfx"] + (["colors", "morph"] if mf.qt_available() else []):
        _close(emb[key], now[key], key)


def test_studio_ranges_match_desktop_sliders():
    """Slider ranges in studio_panels.js are the ParamSlider ranges of the PyQt panels."""
    js = (STATIC / "studio_panels.js").read_text()
    gui = (ROOT / "gui/controls.py").read_text() + (ROOT / "gui/physics_panel.py").read_text()
    pairs = {"Frequency": "frequency`", "Damping": "damping`", "FM Rate": "fm_freq`", "FM Depth": "fm_depth`",
             "PM Rate": "pm_freq`", "PM Depth": "pm_depth`", "Nonlinear": "nonlinearity`", "Strobe Hz": "'h.strobe_freq'",
             "Duty Cycle": "'h.strobe_duty'", "Spread": "'h.chorus_spread'", "Trail length": "'tr.trail_length'",
             "Point size": "'tr.point_size'", "Fade curve": "'tr.fade_power'", "Cycle Hz": "'h.envelope.frequency'"}
    for label, key in pairs.items():
        lo, hi = re.search(rf'ParamSlider\("{label}", ([\d.]+), ([\d.]+)', gui).groups()
        m = re.search(re.escape(key) + r", '[^']+', ([\d.]+), ([\d.]+)", js)
        assert m, key
        assert (float(m.group(1)), float(m.group(2))) == (float(lo), float(hi)), label
