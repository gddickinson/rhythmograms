"""Regression tests for bugs fixed in the desktop app's code (see SESSION_LOG.md, 2026-11-11).

Run: python -m pytest -q tests/test_core_fixes.py   (the GUI tests need PyQt6 and run offscreen; skipped without it)
"""
import os
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.harmonograph import HarmonographEngine  # noqa: E402
from core.pendulum import HarmonographConfig, PendulumParams  # noqa: E402
from core.trace import TraceState  # noqa: E402


def _duffing_config():
    return HarmonographConfig(pendulums=[
        PendulumParams(frequency=2.0, amplitude=1.0, damping=0.01, nonlinearity=0.2),
        PendulumParams(frequency=3.01, phase=0.5, amplitude=0.5, damping=0.015),
        PendulumParams(frequency=3.0, phase=1.5, amplitude=1.0, damping=0.01, nonlinearity=0.1),
        PendulumParams(frequency=2.01, amplitude=0.5, damping=0.015)], duration=4.0, sample_rate=500.0)


def test_speed_range_is_in_pixels():
    """Velocity width/opacity normalise per-segment pixel speeds by TraceState.speed_range, so it must be in pixels.

    Before the fix it was in engine units (~0.03), every segment normalised to 1 and the velocity effects were flat.
    """
    cfg = HarmonographConfig()
    tr = TraceState(cfg, 800, 800, chunk_size=cfg.total_points)
    x, y = tr.compute_full_normalized()
    speed = np.hypot(np.diff(x), np.diff(y))
    smin, smax = tr.speed_range
    assert smax == pytest.approx(np.nanmax(speed), rel=1e-9)
    assert smin == pytest.approx(np.nanmin(speed), rel=1e-9, abs=1e-12)
    norm = np.clip((speed - smin) / (smax - smin), 0, 1)
    assert np.median(norm) < 0.9  # speeds now spread over 0..1


def test_duffing_chunks_match_full_trace():
    """Animated drawing (compute_chunk) must follow the same Duffing trajectory as compute_full (PNG export).

    Before the fix every 300-point chunk restarted the RK4 integration from rest and renormalised it.
    """
    eng = HarmonographEngine(_duffing_config())
    fx, fy = eng.compute_full()
    for start in (0, 300, 1700):
        x, y = eng.compute_chunk(start, 300)
        assert np.allclose(x, fx[start:start + 300], rtol=0, atol=1e-12)
        assert np.allclose(y, fy[start:start + 300], rtol=0, atol=1e-12)
    x, _ = eng.compute_chunk(1900, 300)  # clipped at the end of the trace
    assert len(x) == 100


_APP = []  # keep the QApplication alive for the whole session


def _qt():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PyQt6.QtWidgets")
    from PyQt6.QtWidgets import QApplication
    if not _APP:
        _APP.append(QApplication.instance() or QApplication([]))
    return _APP[0]


def test_control_panel_keeps_duration_and_sample_rate():
    """Moving a pendulum slider after loading a preset must not reset the preset's duration / sample rate to 60 s / 1 kHz."""
    _qt()
    from gui.controls import ControlPanel
    cfg = HarmonographConfig(duration=200.0, sample_rate=500.0)
    panel = ControlPanel()
    panel.set_config(cfg)
    out = panel.get_config()
    assert out.duration == 200.0 and out.sample_rate == 500.0


def test_3d_chunk_uses_global_time():
    """The animated 3D projection must take z(t) at the chunk's real time (as the full render does), not restart at t=0."""
    _qt()
    from core.projection import apply_perspective, compute_z
    from gui.canvas import RhythmogramCanvas
    canvas = RhythmogramCanvas()
    canvas.resize(500, 500)
    canvas._projection.enabled = True
    canvas.set_config(HarmonographConfig())
    canvas.pause()
    tr = canvas._trace
    x = np.linspace(100, 400, 300)
    y = np.linspace(400, 100, 300)
    tr._position = 900 + tr.chunk_size  # the chunk starting at sample 900 has just been taken
    xp, yp = canvas._apply_3d_chunk(x, y)
    sr = canvas._config.sample_rate
    t = (900 + np.arange(300)) / sr
    z = compute_z(t, canvas._projection.z_pendulums)
    cx, cy = canvas.width() / 2.0, canvas.height() / 2.0
    ex, ey = apply_perspective((x - cx) / cx, (y - cy) / cy, z, canvas._projection.focal_length)
    assert np.allclose(xp, ex * cx + cx) and np.allclose(yp, ey * cy + cy)
