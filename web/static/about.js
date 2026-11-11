// About: what rhythmograms are, the equations (from the README), what the browser version does and does not do,
// how to run the desktop and web apps, credits.
import { route, app, api, esc } from './core.js';

route('about', async () => {
  const info = await api('/info');
  const intro = info.intro.replace(/\[([^\]]+)\]\([^)]+\)/g, '$1');
  app().innerHTML = `<p class="kicker">About</p><h1 class="glow">Rhythmogram Simulator</h1>
  <p class="lead">${esc(intro)}</p>
  <p>${esc(info.desktop)} This site is its web edition: the engine and the drawing code are ported to JavaScript and run
  in your browser, so nothing is sent to a server.</p>

  <h2>How it works</h2>
  <p>A rhythmogram is the trace of a point whose x and y coordinates are each the sum of two damped sinusoids:</p>
  <p class="eq">x(t) = A1·sin(f1(t)·t + p1(t))·env(t,d1) + A2·sin(f2(t)·t + p2(t))·env(t,d2)</p><br>
  <p class="eq">y(t) = A3·sin(f3(t)·t + p3(t))·env(t,d3) + A4·sin(f4(t)·t + p4(t))·env(t,d4)</p>
  <ul>
    <li><b>Frequency modulation</b>: f(t) = f0 + depth·sin(2π·fm_freq·t); <b>phase modulation</b>: p(t) = p0 + depth·sin(2π·pm_freq·t).</li>
    <li><b>Envelope</b> env(t, d): exponential damping exp(−d·t), or <i>breathe</i> (smooth pulsing), <i>pulse</i>
      (periodic energy kicks, exp(−d·(t mod T))) or <i>bounce</i> (sine-eased triangle wave).</li>
    <li><b>Duffing nonlinearity</b> adds a cubic restoring force, integrated with RK4.</li>
    <li><b>Strobe</b> blanks the trace periodically (Heidersberger's light extinction); <b>chorus</b> draws N detuned copies.</li>
  </ul>

  <h2>In the browser</h2>
  <p>The Studio has the desktop app's pendulum, visual, physics and atmosphere controls: the four pendulums and the
  energy envelope, smart and plain randomize, ${info.palettes} palettes, gradients with RGB or HSV interpolation,
  ${info.brushes} brushes, velocity-sensitive width and opacity, 2-12-fold symmetry and mirrors, 3D projection with
  auto-rotate, continuous mode with fading, trail mode with per-pendulum trails, invert / solarize / HDR bloom /
  vignette, and smoke glow, god rays, chromatic aberration, film grain, heat distortion and colour grading. It exports
  the view or a full render (up to 4096 px) as PNG, the line trace as SVG, and the settings as JSON in the desktop's
  format (the desktop app can load them with File > Load Config, and the Studio loads the desktop's files).</p>
  <p>Desktop only: the layer stack, audio-reactive mode (WAV files), GIF / MP4 / time-lapse export, zoom and pan,
  full-screen mode.</p>
  <h3>Agreement with the Python code</h3>
  <p>The trace engine matches NumPy to about 1e-12 (see <a href="#/check">Cross-check</a>);
  colours, bloom, vignette, god rays, chromatic aberration, heat distortion and colour grading match the Python
  effects to within one grey level in node tests. Smoke glow and film grain use the same algorithms with a different
  random noise field. One deliberate difference: in continuous mode, presets with a Duffing pendulum replay their
  full trace, while the desktop app restarts the integration every 300 points (an open question in the repository's
  SESSION_LOG.md).</p>

  <h2>Run it yourself</h2>
  <h3>Desktop app (PyQt6)</h3>
  <pre>pip install PyQt6 numpy scipy
python main.py</pre>
  <h3>Web app (local server)</h3>
  <pre>pip install -r requirements-web.txt
python run_web.py          # http://127.0.0.1:8122</pre>
  <p>The local app is the same front end; it also lets the Cross-check page send new configurations to the Python engine.</p>

  <h2>Credits</h2>
  <p>Inspired by the work of Heinrich Heidersberger (1906-2006), whose rhythmograms bridged art and mathematics
  through the elegant physics of pendulum motion. Code: <a href="https://github.com/gddickinson/rhythmograms">gddickinson/rhythmograms</a>,
  MIT licence.</p>`;
});
