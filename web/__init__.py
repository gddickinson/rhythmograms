"""Web interface for the Rhythmogram Simulator (FastAPI app + static front end, also published to GitHub Pages).

Contents:
    app.py      FastAPI app: /api/info, /presets, /palettes, /defaults, /trace/<preset> (GET, exported to the static
                site) and POST /api/trace (local only); STATIC_ENDPOINTS lists what scripts/build_static.py exports.
    static/     ES-module front end; harmonograph_engine.js, color.js, postfx.js, atmosphere.js and render.js are the
                JS ports of core/ and effects/ that draw the rhythmograms in the browser (node-tested against Python).
See INTERFACE.md for the full map.
"""
