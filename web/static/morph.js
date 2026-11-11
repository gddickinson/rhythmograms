// Morph: parametric interpolation between two presets with core/morph.py morph_config (frequency, phase, amplitude,
// damping, duration and envelope are interpolated; sample rate is the larger one). Play sweeps t from 0 to 1, bounce
// goes back and forth, like the desktop Morph dialog (Tools > Morph).
import { route, app, esc, list, rng, animate } from './core.js';
import { configFromDict, morphConfig } from './harmonograph_engine.js';
import { prepareColor, applyPalette } from './color.js';
import { renderFull } from './render.js';
import { loadSetup, button } from './ui.js';
import { freshState, openInStudio } from './state.js';

const SIZE = 420;

route('morph', async (args, q) => {
  const setup = await loadSetup();
  const opts = sel => list(setup.presets, p => `<option value="${esc(p.slug)}"${p.slug === sel ? ' selected' : ''}>${esc(p.name)}</option>`);
  const pals = list(setup.palettes, p => `<option${p.name === 'Aurora Borealis' ? ' selected' : ''}>${esc(p.name)}</option>`);
  app().innerHTML = `<p class="kicker">Morph</p><h1 class="glow">Between two rhythmograms</h1>
  <p class="lead">Every pendulum's frequency, phase, amplitude and damping is interpolated linearly from preset A to
  preset B (core/morph.py). Modulation, strobe and chorus are not interpolated by morph_config, so the middle
  frames are plain four-pendulum traces.</p>
  <div class="row ctlrow" id="mctl">
    <div><label for="ma">Preset A</label><select id="ma">${opts(q.a || 'fugue')}</select></div>
    <div><label for="mb">Preset B</label><select id="mb">${opts(q.b || 'cathedral_rose')}</select></div>
    <div><label for="mp">Palette</label><select id="mp">${pals}</select></div>
  </div>
  <div class="ctl"><label for="mt">t <b id="tv">0.50</b></label><input type="range" id="mt" min="0" max="1" step="0.005" value="0.5"></div>
  <div id="mbtn"></div>
  <div class="morphview">
    <figure class="fig"><canvas id="ca" width="${SIZE}" height="${SIZE}" role="img" aria-label="Preset A"></canvas><figcaption class="small mute">A (t = 0)</figcaption></figure>
    <figure class="fig"><canvas id="cm" width="${SIZE}" height="${SIZE}" role="img" aria-label="Morphed configuration"></canvas><figcaption class="small mute" id="mcap"></figcaption></figure>
    <figure class="fig"><canvas id="cb" width="${SIZE}" height="${SIZE}" role="img" aria-label="Preset B"></canvas><figcaption class="small mute">B (t = 1)</figcaption></figure>
  </div>`;
  const $ = s => app().querySelector(s);
  const bySlug = Object.fromEntries(setup.presets.map(p => [p.slug, p]));
  let cc, A, B, t = 0.5, dir = 0, bounce = false, dirty = true;

  function setup2() {
    A = configFromDict(bySlug[$('#ma').value].config); B = configFromDict(bySlug[$('#mb').value].config);
    cc = prepareColor(applyPalette(freshState(setup).c, setup.palettes.find(p => p.name === $('#mp').value)));
    const opt = { maxSegments: 12000, rand: rng(2) };
    renderFull($('#ca').getContext('2d'), A, cc, SIZE, SIZE, opt);
    renderFull($('#cb').getContext('2d'), B, cc, SIZE, SIZE, opt);
    dirty = true;
  }
  ['#ma', '#mb', '#mp'].forEach(s => $(s).addEventListener('change', setup2));
  $('#mt').addEventListener('input', e => { t = +e.target.value; dir = 0; dirty = true; });
  const ctl = $('#mbtn');
  button(ctl, 'Play', () => { t = 0; dir = 1; bounce = false; });
  button(ctl, 'Bounce', () => { dir = dir || 1; bounce = true; }, true);
  button(ctl, 'Stop', () => { dir = 0; }, true);
  button(ctl, 'Open in Studio', () => openInStudio({ h: morphConfig(A, B, t), c: { ...cc } }), true);
  setup2();

  let last = performance.now();
  animate(now => {
    const dt = Math.min(0.1, (now - last) / 1000); last = now;
    if (dir) {
      t += dir * dt / 4; // a 4 s sweep
      if (t >= 1) { t = 1; dir = bounce ? -1 : 0; } else if (t <= 0) { t = 0; dir = bounce ? 1 : 0; }
      dirty = true; $('#mt').value = t;
    }
    if (!dirty) return;
    dirty = false;
    $('#tv').textContent = t.toFixed(2);
    const m = morphConfig(A, B, t);
    renderFull($('#cm').getContext('2d'), m, cc, SIZE, SIZE, { maxSegments: 6000, rand: rng(2) });
    $('#mcap').textContent = `t = ${t.toFixed(2)}: f = ${m.pendulums.map(p => p.frequency.toFixed(3)).join(', ')} Hz, ${m.duration.toFixed(0)} s`;
  });
});
