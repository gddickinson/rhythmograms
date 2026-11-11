// Home page: hero with a live rhythmogram drawing itself, counts from the API, entry cards.
import { route, api, app, esc, list, animate } from './core.js';
import { configFromDict } from './harmonograph_engine.js';
import { applyPalette } from './color.js';
import { loadSetup } from './ui.js';
import { freshState } from './state.js';
import { Player } from './player.js';

const DOORS = [
  ['#/studio', 'Studio', 'The full simulator: four pendulums, envelopes, FM/PM, Duffing, strobe, chorus, palettes, brushes, symmetry, 3D, trails, post-processing and atmosphere, with PNG / SVG / config export.'],
  ['#/presets', 'Presets', 'All the built-in presets of the desktop app, drawn in your browser. Click one to open it in the Studio.'],
  ['#/gallery', 'Gallery', 'Auto-generated random configurations with random palettes, like the desktop Gallery tab.'],
  ['#/morph', 'Morph', 'Interpolate smoothly between two presets (parametric morphing).'],
  ['#/check', 'Cross-check', 'The browser engine against the Python engine: every preset computed by NumPy on the server, compared point by point.'],
  ['#/about', 'About', 'Heidersberger\'s rhythmograms, the equations, what runs in the browser, how to run the desktop and web apps.'],
];

route('home', async () => {
  const [info, setup] = await Promise.all([api('/info'), loadSetup()]);
  const intro = info.intro.replace(/\[([^\]]+)\]\([^)]+\)/g, '$1');
  app().innerHTML = `
  <section class="hero two heroart">
    <div>
      <p class="kicker">Light traces · four damped pendulums</p>
      <h1 class="glow">Rhythmogram Simulator</h1>
      <p class="lead">${esc(intro)}</p>
      <p class="mute">The desktop app's engine, ported to JavaScript: everything on this site is drawn live in your browser.</p>
      <a class="btn" href="#/studio">Open the Studio</a><a class="btn alt" href="#/presets">Browse the presets</a>
    </div>
    <figure class="fig"><canvas id="hero" width="620" height="620" role="img" aria-label="A rhythmogram drawing itself: the Cathedral Rose preset in the Neon Plasma palette"></canvas>
      <figcaption class="small mute" id="herocap"></figcaption></figure>
  </section>
  <div class="tiles">
    <div class="tile"><b>${info.pendulums}</b><span>damped pendulums</span></div>
    <div class="tile"><b>${info.presets}</b><span>built-in presets</span></div>
    <div class="tile"><b>${info.palettes}</b><span>curated palettes</span></div>
    <div class="tile"><b>${info.brushes}</b><span>brush types</span></div>
    <div class="tile"><b>${info.envelope_modes}</b><span>energy envelopes</span></div>
  </div>
  <div class="grid wide">${list(DOORS, ([href, t, d]) => `<a class="card door" href="${href}"><b>${t}</b><span>${d}</span></a>`)}</div>
  <h2>Presets</h2>
  <p>${list(setup.presets, p => `<a class="tag a" href="#/studio?p=${encodeURIComponent(p.slug)}">${esc(p.name)}</a>`)}</p>`;
  hero(setup);
});

function hero(setup) {
  const cv = document.getElementById('hero');
  const st = freshState(setup);
  const preset = setup.presets.find(p => p.slug === 'cathedral_rose') || setup.presets[0];
  st.h = configFromDict(preset.config);
  st.c = applyPalette(st.c, setup.palettes.find(p => p.name === 'Neon Plasma') || setup.palettes[0]);
  st.c.line_alpha = 150; st.speed = 3;
  document.getElementById('herocap').textContent = `${preset.name}, ${st.c.palette_name} palette, drawn at 3x the desktop speed`;
  const pl = new Player(cv);
  pl.setState(st);
  pl.restart();
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) { while (!pl.done) pl.step(0.1); return; }
  let last = performance.now();
  animate(now => { pl.step((now - last) / 1000); last = now; });
}
