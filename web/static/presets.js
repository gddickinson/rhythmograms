// Presets: every presets/*.json drawn in the browser (like the desktop Preset tab's thumbnails), and the Gallery:
// random smart configurations with random palettes (gui/gallery_panel.py). Thumbnails are drawn one per frame.
import { route, app, esc, list, rng, onLeave } from './core.js';
import { configFromDict, smartRandom } from './harmonograph_engine.js';
import { prepareColor, applyPalette } from './color.js';
import { renderFull } from './render.js';
import { loadSetup, thumbCanvas, button } from './ui.js';
import { freshState, openInStudio } from './state.js';

const THUMB = 240;

// Draw jobs one per animation frame so the page stays responsive; cancelled when the page is left.
let current = { alive: false };
function queue(jobs) {
  current.alive = false;
  const me = current = { alive: true };
  let i = 0;
  const next = () => { if (!me.alive || i >= jobs.length) return; jobs[i++](); requestAnimationFrame(next); };
  requestAnimationFrame(next);
  onLeave(() => { me.alive = false; });
}

const features = c => {
  const f = [];
  if (c.pendulums.some(p => p.nonlinearity)) f.push('Duffing');
  if (c.pendulums.some(p => p.fm_depth || p.pm_depth)) f.push('FM/PM');
  if (c.strobe_freq > 0) f.push('strobe');
  if (c.chorus_count > 1) f.push(`chorus ×${c.chorus_count}`);
  if (c.envelope.mode !== 'none') f.push(c.envelope.mode);
  return f;
};

route('presets', async (args, q) => {
  const setup = await loadSetup();
  const palName = q.pal || '';
  app().innerHTML = `<p class="kicker">Presets</p><h1 class="glow">${setup.presets.length} built-in presets</h1>
  <p class="lead">The presets of the desktop app (presets/*.json), each drawn from its full trace by the browser engine.
  Click one to open it in the Studio.</p>
  <div class="row ctlrow"><div><label for="pal">Colour the thumbnails with</label><select id="pal">
    <option value="">Default colours (as the desktop thumbnails)</option>${list(setup.palettes, p => `<option${p.name === palName ? ' selected' : ''}>${esc(p.name)}</option>`)}</select></div></div>
  <div class="thumbs" id="grid"></div>`;
  app().querySelector('#pal').addEventListener('change', e => { location.hash = `#/presets${e.target.value ? `?pal=${encodeURIComponent(e.target.value)}` : ''}`; });
  const pal = setup.palettes.find(p => p.name === palName);
  let cc = freshState(setup).c;
  if (pal) cc = applyPalette(cc, pal); else cc.line_alpha = 140; // PresetThumbnail: default line colour, alpha 140, width 0.7
  cc.line_width = 0.7;
  const grid = app().querySelector('#grid'), jobs = [];
  for (const p of setup.presets) {
    const a = document.createElement('a');
    a.className = 'card'; a.href = `#/studio?p=${encodeURIComponent(p.slug)}${pal ? `&pal=${encodeURIComponent(pal.name)}` : ''}`;
    const c = thumbCanvas(THUMB, `Preset ${p.name}`);
    const cfg = configFromDict(p.config);
    a.append(c);
    a.insertAdjacentHTML('beforeend', `<b>${esc(p.name)}</b><small>${cfg.duration} s · ${list(features(cfg), t => esc(t), ' · ') || 'classic'}</small>`);
    grid.append(a);
    jobs.push(() => renderFull(c.getContext('2d'), cfg, prepareColor(cc), THUMB, THUMB, { maxSegments: 2000, margin: 0.08, rand: rng(3) }));
  }
  queue(jobs);
});

route('gallery', async (args, q) => {
  const setup = await loadSetup();
  let seed = +q.seed || 1;
  app().innerHTML = `<p class="kicker">Gallery</p><h1 class="glow">Random rhythmograms</h1>
  <p class="lead">Auto-generated configurations: Smart Randomize with the advanced features (FM/PM, Duffing, strobe,
  chorus, envelopes) and a random palette for each, as in the desktop Gallery tab. Click one to open it in the Studio.</p>
  <div class="row ctlrow" id="gctl"><div><label for="count">Count</label><input id="count" type="number" min="4" max="24" value="12"></div></div>
  <p class="small mute" id="seed"></p><div class="thumbs" id="grid"></div>`;
  const ctl = app().querySelector('#gctl');
  button(ctl, 'Generate', () => { seed++; draw(); });
  draw();

  function draw() {
    const r = rng(seed), count = Math.max(4, Math.min(24, +app().querySelector('#count').value || 12));
    app().querySelector('#seed').textContent = `Seed ${seed} (reproducible: #/gallery?seed=${seed})`;
    const grid = app().querySelector('#grid'), jobs = [];
    grid.innerHTML = '';
    for (let i = 0; i < count; i++) {
      const cfg = smartRandom(r, true), pal = setup.palettes[Math.floor(r() * setup.palettes.length)];
      const cc = { ...applyPalette(freshState(setup).c, pal), line_alpha: 160, palette_name: pal.name };
      const a = document.createElement('a');
      a.className = 'card'; a.href = '#/studio';
      a.addEventListener('click', e => { e.preventDefault(); openInStudio({ h: cfg, c: cc }); });
      const c = thumbCanvas(THUMB, `Random configuration ${i + 1}, ${pal.name} palette`);
      a.append(c);
      a.insertAdjacentHTML('beforeend', `<b>${esc(pal.name)}</b><small>${list(features(cfg), t => esc(t), ' · ') || 'classic'}</small>`);
      grid.append(a);
      // GalleryThumbnail: every n//2000-th point, width 0.7, alpha at most 160
      jobs.push(() => renderFull(c.getContext('2d'), cfg, prepareColor({ ...cc, line_width: 0.7 }), THUMB, THUMB, { maxSegments: 2000, margin: 0.08, rand: rng(3) }));
    }
    queue(jobs);
  }
});
