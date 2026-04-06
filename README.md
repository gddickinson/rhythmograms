# Rhythmogram Simulator

A simulation of [Heinrich Heidersberger's](https://en.wikipedia.org/wiki/Heinrich_Heidersberger) rhythmograms — mesmerizing light-trace photographs created by 4-pendulum damped harmonographs. Heidersberger produced these abstract works from the 1950s onward by photographing the paths of light reflected from swinging pendulums, resulting in intricate, mathematically precise geometric patterns.

This desktop application lets you explore the same mathematical space interactively, with real-time animation, configurable pendulum parameters, and image export.

![Python](https://img.shields.io/badge/Python-3.10+-blue) ![PyQt6](https://img.shields.io/badge/GUI-PyQt6-green) ![License](https://img.shields.io/badge/license-MIT-lightgrey)

## Features

- **Real-time animation** — watch traces draw at 60fps with smooth incremental rendering
- **4-pendulum control** — adjust frequency, phase, amplitude, and damping for each of the X1, X2, Y1, Y2 pendulums
- **Color and gradients** — customizable line/background colors, gradient interpolation along the trace, adjustable alpha and line width
- **Post-processing effects** — invert, solarize, and bloom filters applied as pixel operations
- **Multiple exposures** — additive blending of multiple traces via the exposure compositor
- **8 built-in presets** — musically-named starting points: Classic Lissajous, Klangflache, Prelude, Fugue, Nocturne, Spirograph Decay, Orbital Bloom, Resonance
- **Save/Load** — persist and restore full configurations as JSON
- **Export** — high-resolution PNG and vector SVG output

## Installation

Requires Python 3.10+.

```bash
pip install PyQt6 numpy scipy
```

## Usage

```bash
python main.py
```

The application opens with a split view: the drawing canvas on the left and tabbed control panels on the right.

**Controls:**
- **Pendulums tab** — sliders for each pendulum's frequency, phase, amplitude, and damping
- **Effects tab** — color pickers, gradient settings, alpha/line width, and post-processing toggles
- **Presets tab** — click a thumbnail to load a preset configuration
- **Toolbar** — Play/Pause/Reset the animation, track progress, Save/Load configs, Export PNG/SVG

## Project Structure

```
rhythmograms/
    main.py                  # Application entry point
    core/
        pendulum.py          # Pendulum parameter dataclasses
        harmonograph.py      # Numpy-vectorized harmonograph engine
        trace.py             # Incremental animation state manager
    effects/
        color.py             # Color configuration and gradient interpolation
        postprocess.py       # Invert, solarize, bloom effects
        composite.py         # Additive exposure blending
    gui/
        app.py               # Main window layout and signal wiring
        canvas.py            # Offscreen QPixmap drawing surface
        controls.py          # Pendulum parameter sliders
        effects_panel.py     # Color and effects controls
        toolbar.py           # Playback and file action buttons
        presets_panel.py     # Preset thumbnail grid
        style.py             # Dark theme stylesheet
    utils/
        config.py            # JSON save/load
        export.py            # PNG and SVG export
    presets/                 # 8 built-in preset JSON files
```

## How It Works

A rhythmogram is the trace of a point whose x and y coordinates are each the sum of two damped sinusoids:

```
x(t) = A1 * sin(f1*t + p1) * exp(-d1*t)  +  A2 * sin(f2*t + p2) * exp(-d2*t)
y(t) = A3 * sin(f3*t + p3) * exp(-d3*t)  +  A4 * sin(f4*t + p4) * exp(-d4*t)
```

The interplay of frequencies, phases, and damping rates produces a rich variety of patterns — from simple Lissajous figures (no damping, integer frequency ratios) to complex spiraling forms that decay into stillness.

## Acknowledgments

Inspired by the work of Heinrich Heidersberger (1906-2006), whose rhythmograms bridged art and mathematics through the elegant physics of pendulum motion.
