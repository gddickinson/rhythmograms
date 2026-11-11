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

**Open questions for George**: answered the same day, see below.

## 2026-11-11 (later): fixes approved by George

Each in its own "Fix ..." commit, with regression tests in `tests/test_core_fixes.py` that failed first; the JS engine
(`web/static/harmonograph_engine.js`) and `tests/fixtures/engine_fixture.json` were updated to match:
5. Duffing pendulums now honour phase and PM: released at x0 = A·sin(phase), v0 = A·ω·cos(phase); PM rotates the state
   in the (x, v/ω) plane by pm(t) (exactly A·sin(ωt + phase + pm(t)) for a linear spring). Configurations with phase 0
   and no PM are unchanged; Atom, Deep Space and Duffing Chaos change (docs/img/presets.png regenerated).
6. Continuous mode with a Duffing pendulum continues the RK4 integration past the end of the trace (state and
   normalisation are kept from `compute_full`), instead of restarting every chunk. The web Studio does the same now
   (it used to replay the full trace).
7. `presets/george1.json` is named "Coiled Spring" (a fast ~9 Hz near-unison X pair against a slow ~1.5 Hz Y pair:
   horizontal loops stacked vertically like a spring seen side-on); README counts 35 presets.
Checks: pytest 58 passed (55 passed + 3 skipped without PyQt6), node 71 + 31 checks, screenshots static and on
port 8122 all ok, desktop continuous mode on Atom checked offscreen (runs past its 50 s duration).
