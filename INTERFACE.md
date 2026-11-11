# INTERFACE.md: navigation map of the Rhythmogram Simulator

Desktop app: PyQt6 (`main.py` -> `gui/app.py`). Web app: FastAPI + ES modules (`run_web.py` -> `web/app.py`), also
published as a static GitHub Pages site. `core/` and most of `effects/` are Qt-free and shared by both.

## core/ (pure NumPy)
| File | Contents |
|------|----------|
| `pendulum.py` | `PendulumParams`, `EnvelopeConfig`, `HarmonographConfig` (to/from dict, `random`, `smart_random`), `ENVELOPE_MODES` |
| `harmonograph.py` | `HarmonographEngine`: `compute_full` (cached), `compute_chunk`, FM/PM, envelopes, Duffing RK4, strobe, chorus, ranges |
| `trace.py` | `TraceState`: progressive / continuous drawing, pixel `speed_range` for velocity effects |
| `trails.py` | `TrailConfig`, `TrailBuffer` (trail mode ring buffers) |
| `projection.py` | `Projection3DConfig`, `compute_z`, `apply_perspective` |
| `morph.py` | `morph_config`, `morph_color_config` (imports QColor) |

## effects/
| File | Contents |
|------|----------|
| `style_defaults.py` | Qt-free `COLOR_DEFAULTS`, `BRUSH_TYPES` (used by `color.py`, `brushes.py` and the web API) |
| `color.py` | `ColorConfig` (QColor): gradients RGB/HSV, velocity width/opacity |
| `palettes.py` | `Palette`, `PALETTES` (10), `get_palette` |
| `brushes.py` | `draw_segment` for line/dot/airbrush/chalk/ribbon (QPainter) |
| `postprocess.py` | `EffectsConfig`, invert/solarize/bloom/vignette on arrays; QImage helpers import PyQt6 lazily |
| `atmosphere.py` | `AtmosphereConfig`, smoke glow, god rays, chromatic aberration, grain, heat, grading |
| `composite.py` | `ExposureCompositor` (additive exposures) |

## gui/ (PyQt6)
`app.py` main window and signal wiring; `canvas.py` animated canvas (trace, trails, 3D, effects, zoom); `trace_renderer.py`
symmetry/mirrors/velocity drawing; panels: `controls.py` (pendulums, envelope), `effects_panel.py`, `physics_panel.py`,
`atmosphere_panel.py`, `layers_panel.py`, `presets_panel.py`, `gallery_panel.py`, `morph_dialog.py`, `toolbar.py`, `style.py`.

## utils/
`config.py` JSON save/load; `export.py` PNG/SVG; `animation_export.py` GIF/MP4/time-lapse; `audio.py` WAV analysis.

## web/ (web interface)
| File | Contents |
|------|----------|
| `app.py` | FastAPI: `/api/info`, `/presets`, `/palettes`, `/defaults`, `/trace/{slug}`, `POST /trace`; `STATIC_ENDPOINTS` |
| `static/index.html`, `style.css` (kit), `style_app.css`, `core.js` (kit router/helpers), `main.js`, `static_api.js` | shell, theme, router, static-site data layer |
| `static/harmonograph_engine.js` | JS port of `core/` (engine, smart_random, trails, projection, morph) |
| `static/color.js` | JS port of `ColorConfig` colours (QColor HSV emulated), palettes |
| `static/postfx.js`, `static/atmosphere.js` | JS ports of `postprocess.py` and `atmosphere.py` (+ scipy-compatible filters) |
| `static/render.js` | canvas drawing: brushes, symmetry, mirrors, velocity, full renders, trail frames |
| `static/player.js` | animated drawing (standard / continuous / trail, 3D, throttled effects) |
| `static/state.js`, `studio.js`, `studio_panels.js`, `studio_io.js`, `ui.js` | Studio page: state, layout, control tabs, save/load/export, form binder |
| `static/home.js`, `presets.js` (Presets + Gallery), `morph.js`, `check.js`, `about.js` | other pages |
| `static/*.test.mjs` | node tests against `tests/fixtures/engine_fixture.json` |

## scripts/, tests/, root
`scripts/build_static.py` (static site), `scripts/screenshots.py` (smoke test + README images),
`scripts/make_engine_fixture.py` (Python reference numbers for the JS); `tests/test_web.py` (API, build, node tests,
fixture currency, slider ranges), `tests/test_core_fixes.py` (desktop regression tests); `run_web.py` (port 8122),
`requirements-web.txt`, `.github/workflows/pages.yml`.

## How they connect
`gui/*` -> `core/*`, `effects/*`. `web/app.py` -> `core/*`, `effects/{palettes,style_defaults,postprocess,atmosphere}`.
Browser: `main.js` -> pages -> `player.js`/`render.js` -> `harmonograph_engine.js`, `color.js`, `postfx.js`, `atmosphere.js`.
