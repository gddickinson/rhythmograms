# Rhythmogram Simulator

See @INTERFACE.md for the project navigation map and SESSION_LOG.md for history.

## Run
```bash
python main.py              # desktop app (PyQt6)
python run_web.py           # web app on http://127.0.0.1:8122
```

## Test
```bash
python -m pytest -q tests/  # web + desktop regression tests (node needed for the JS engine tests)
```

## Web
`web/static/harmonograph_engine.js`, `color.js`, `postfx.js` and `atmosphere.js` mirror `core/` and `effects/`:
change both together and rerun `python scripts/make_engine_fixture.py --write`.
