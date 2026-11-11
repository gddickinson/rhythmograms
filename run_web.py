"""Start the Rhythmogram Simulator web app on http://127.0.0.1:8122 (local only).

Run: python run_web.py [--port 8122]
Needs: pip install -r requirements-web.txt (PyQt6 is not needed for the web app)
"""
import argparse

import uvicorn

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8122)
    port = ap.parse_args().port
    print(f"Rhythmogram Simulator web app: http://127.0.0.1:{port}")
    uvicorn.run("web.app:app", host="127.0.0.1", port=port)
