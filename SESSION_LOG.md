# SESSION_LOG

## 2026-11-11: web interface, static GitHub Pages site, desktop bug fixes (branch `web-interface`)

**Web interface** (`web/`, `run_web.py` on port 8122, `scripts/`, `.github/workflows/pages.yml`): the static site is
the working app. JS ports of `core/` (engine, trails, projection, morph, randomizers), `effects/color.py` (QColor HSV
emulated), `effects/postprocess.py` and `effects/atmosphere.py`, plus canvas versions of the brushes and the trace
renderer. Pages: Home, Studio (desktop tabs, transport, continuous and trail modes, 3D, effects, PNG/SVG/JSON export,
desktop-compatible config load), Presets, Gallery, Morph, Cross-check, About.
Agreement: node tests vs `tests/fixtures/engine_fixture.json` (`scripts/make_engine_fixture.py`): 41 traces incl. all
35 presets (Duffing ones cut to 6 s) match to 1e-9 relative (in practice ~1e-16); colours within 1/255; bloom, vignette,
god rays, chromatic aberration, heat, grading within 1 grey level. Smoke glow and film grain use the same algorithm with
a different random field (no NumPy RandomState in JS). Not in the browser: layers, audio-reactive mode, GIF/MP4/
time-lapse export, zoom/pan.

Small Qt-free refactors so the web API can run without PyQt6 (desktop behaviour unchanged, GUI checked offscreen):
`effects/style_defaults.py` (ColorConfig defaults and BRUSH_TYPES, imported by `color.py` / `brushes.py`), and
`effects/postprocess.py` imports PyQt6 only inside its QImage helpers.

**Bugs fixed in the desktop code** (each its own "Fix ..." commit; regression tests in `tests/test_core_fixes.py`,
all four failed before the fixes):
1. Velocity-sensitive width/opacity were flat: `TraceState.speed_range` was in engine units but segment speeds are in
   pixels, so every normalised speed clipped to 1. Now a pixel speed range (`TraceState._pixel_speed_range`).
2. Duffing presets restarted their RK4 integration (and renormalised) every 300-point animation chunk, so the animated
   drawing differed from the full trace / PNG export. Bounded chunks are now cut from the (cached) full trace.
3. `ControlPanel.get_config()` dropped duration and sample rate: touching any slider after loading a preset redrew it
   as 60 s at 1000 Hz (e.g. Silk Vortex is 200 s, the Duffing presets 500 Hz). Now kept.
4. Animated 3D projection evaluated the Z pendulums on chunk-local time (0..0.3 s at an assumed 1000 Hz). Now the
   chunk's real sample times.

**Open questions for George** (not changed):
- `_compute_nonlinear` ignores each pendulum's phase and PM (starts every pendulum at x=0, v=A·ω); with any Duffing
  pendulum all four go through RK4. Using the phase would change the Atom / Deep Space / Duffing Chaos presets.
- Continuous mode with a Duffing pendulum still restarts the integration every chunk (unbounded chunks); the web
  replays the full trace instead.
- README says "34 Built-in Presets"; there are 35 files: `presets/george1.json` has no name (shown as "George1") and
  carries colour/effects settings that the Preset tab ignores. Keep it as a preset, name it, or move it?
