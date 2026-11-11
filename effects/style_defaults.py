"""Qt-free trace-style defaults shared by the desktop app and the web interface.

COLOR_DEFAULTS holds the default values of effects.color.ColorConfig (colours as hex strings) and BRUSH_TYPES the
brush names drawn by effects.brushes. Both modules import from here, so the PyQt6 GUI and the web API (which runs
without PyQt6) use the same numbers.
"""

BRUSH_TYPES = ["line", "dot", "airbrush", "chalk", "ribbon"]

COLOR_DEFAULTS = {
    "line_color": "#c8dcff",       # QColor(200, 220, 255)
    "bg_color": "#05050f",         # QColor(5, 5, 15)
    "gradient_start": "#64b4ff",   # QColor(100, 180, 255)
    "gradient_end": "#ff64c8",     # QColor(255, 100, 200)
    "gradient_mid": "#64ffb4",     # QColor(100, 255, 180)
    "use_gradient": False,
    "use_mid_color": False,
    "interpolation": "rgb",
    "line_alpha": 180,
    "line_width": 1.0,
    "velocity_width": False,
    "velocity_width_min": 0.3,
    "velocity_width_max": 3.0,
    "velocity_opacity": False,
    "velocity_opacity_min": 40,
    "velocity_opacity_max": 255,
    "symmetry_order": 1,
    "mirror_horizontal": False,
    "mirror_vertical": False,
    "brush_type": "line",
    "palette_name": "",
}
