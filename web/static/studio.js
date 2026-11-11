// Studio: the desktop app in the browser. Pendulum, visual, physics and atmosphere tabs on the left; the animated
// canvas, transport (play / pause / reset, continuous mode with fade), randomizers, presets and exports on the right.
// URL: #/studio?p=<preset slug>&pal=<palette name>. Keys as on the desktop: Space play/pause, R reset.
import { route, app, esc, animate, download, onLeave } from './core.js';
import { configFromDict, smartRandom, randomConfig, cloneConfig } from './harmonograph_engine.js';
import { freshState, takeHandoff } from './state.js';
import { applyPalette } from './color.js';
import { Binder, button, loadSetup, group } from './ui.js';
import { buildPanels } from './studio_panels.js';
import { Player } from './player.js';
import { configJson, applyConfigJson, pickFile, saveView, renderPng, svgText } from './studio_io.js';

const VIEW = 900; // canvas pixels (square)

route('studio', async (args, q) => {
  const setup = await loadSetup();
  const st = freshState(setup), handoff = takeHandoff();
  const bySlug = Object.fromEntries(setup.presets.map(p => [p.slug, p]));
  const startSlug = q.p && bySlug[q.p] ? q.p : (handoff ? '' : 'cathedral_rose');
  if (startSlug) loadPreset(startSlug, false);
  const pal = setup.palettes.find(p => p.name === (q.pal || (handoff ? '' : 'Neon Plasma')));
  if (pal) st.c = applyPalette(st.c, pal);
  if (handoff) { Object.assign(st, handoff); st.h = cloneConfig(st.h); st.en = st.h.pendulums.map(x => x.amplitude > 0); }

  const binder = new Binder(() => st, onChange);
  const host = app();
  host.innerHTML = `<p class="kicker">Studio</p><h1 class="glow">Draw a rhythmogram</h1>
  <p class="lead small">Four damped pendulums drive a point of light: two add up to x, two to y. Set them on the left,
  watch the trace build up on the right, then save the picture or the settings.</p>
  <div class="studio"><div class="controls" id="ctl"></div><div class="view" id="view"></div></div>`;
  const ctl = host.querySelector('#ctl'), view = host.querySelector('#view');

  // --- canvas, transport, readout -----------------------------------------------------------------------------
  view.innerHTML = `<div class="stage"><canvas id="cv" width="${VIEW}" height="${VIEW}" role="img" tabindex="0"></canvas></div>
    <div class="progress" aria-hidden="true"><i id="bar"></i></div>
    <div class="transport" id="tp"></div>
    <div class="readout" id="ro" aria-live="off"></div>
    <p class="small mute keys">Keys: <kbd>Space</kbd> play / pause · <kbd>R</kbd> reset (as in the desktop app)</p>`;
  const cv = view.querySelector('#cv'), bar = view.querySelector('#bar'), ro = view.querySelector('#ro'), tp = view.querySelector('#tp');
  const player = new Player(cv, (p, t) => { bar.style.width = `${(p * 100).toFixed(1)}%`; readout(p, t); });
  player.setState(st);

  const playBtn = button(tp, 'Pause', () => toggle());
  button(tp, 'Reset', () => restart(), true);
  button(tp, 'Smart randomize', () => { st.h = smartRandom(Math.random, true); afterLoad('smart random'); }, false,
    'Near-integer frequency ratios, sometimes with FM/PM, strobe, chorus and an envelope (HarmonographConfig.smart_random)');
  button(tp, 'Randomize all', () => { st.h = randomConfig(); afterLoad('random'); }, true, 'Uniformly random pendulums (HarmonographConfig.random)');
  const opts = group(tp, 'Drawing');
  b().check(opts, 'cont', 'Continuous (pendulums never stop; old trace fades)', 't');
  b().slider(opts, 'fade', 'Fade', 1, 20, 1, 'x');
  b().slider(opts, 'speed', 'Drawing speed (1 = desktop)', 0.25, 20, 0.25, 'x', 2);
  const pre = group(tp, 'Preset');
  b().select(pre, 'preset', 'Load a preset', [['', '(choose)'], ...setup.presets.map(p => [p.slug, p.name])], 'x', v => v && loadPreset(v, true));
  const ex = group(tp, 'Save and export');
  const size = b().select(ex, null, 'PNG size', [['1024', '1024 px'], ['2048', '2048 px'], ['4096', '4096 px (desktop export size)']], 'x', () => {});
  button(ex, 'Save view', () => saveView(cv, fileName('png')), true, 'The canvas as shown, as PNG');
  const renderBtn = button(ex, 'Render PNG', async () => {
    renderBtn.disabled = true; renderBtn.textContent = 'Rendering...';
    await new Promise(r => setTimeout(r, 30));
    try { await renderPng(st, +size.value, fileName('png')); } finally { renderBtn.disabled = false; renderBtn.textContent = 'Render PNG'; }
  }, false, 'Full trace at the chosen size with all effects');
  button(ex, 'SVG', () => download(fileName('svg'), svgText(st), 'image/svg+xml'), true, 'Vector trace (line brush, no raster effects)');
  button(ex, 'Save config', () => download(fileName('json'), configJson(st), 'application/json'), true);
  button(ex, 'Load config', async () => {
    const text = await pickFile();
    if (!text) return;
    try { applyConfigJson(st, JSON.parse(text), setup.defaults); afterLoad('file'); } catch (e) { alert(`Could not load: ${e.message}`); }
  }, true, 'A JSON file saved here or by the desktop app (File > Save Config)');

  // --- tabs ---------------------------------------------------------------------------------------------------
  let envCb = () => {};
  buildPanels(ctl, b(), setup, { onPalette, onEnvelope: f => { envCb = f; } });
  const paldesc = ctl.querySelector('.paldesc');

  function b() { return binder; }
  function onChange(kind, path) {
    if (path === 'h.envelope.mode') envCb(st.h.envelope.mode);
    if (path && path.startsWith('c.') && path !== 'c.palette_name' && !['c.line_alpha', 'c.line_width', 'c.brush_type'].includes(path) &&
        /color|gradient|interpolation|mid/.test(path)) { st.c.palette_name = ''; binder.refresh(); paldesc.textContent = ''; }
    if (kind === 't') restartSoon();
    else if (kind === 'f') { player.fxDirty = true; player.present(true); }
  }
  function onPalette(name) {
    const p = setup.palettes.find(x => x.name === name);
    if (p) { st.c = applyPalette(st.c, p); paldesc.textContent = p.description; } else { st.c.palette_name = ''; paldesc.textContent = ''; }
    binder.refresh(); restart();
  }

  function loadPreset(slug, live) {
    const p = bySlug[slug];
    st.h = configFromDict(p.config); st.en = st.h.pendulums.map(x => x.amplitude > 0); st.preset = slug;
    if (live) afterLoad(p.name);
  }
  function afterLoad(what) { // what: a preset name, or 'random' / 'smart random' / 'file' (no preset any more)
    if (bySlug[st.preset]?.name !== what) st.preset = '';
    binder.refresh(); envCb(st.h.envelope.mode); restart();
  }

  let timer = 0;
  function restartSoon() { clearTimeout(timer); timer = setTimeout(restart, 60); } // desktop debounce: 50 ms
  function restart() {
    player.restart(); playBtn.textContent = 'Pause';
    const name = bySlug[st.preset]?.name;
    cv.setAttribute('aria-label', `Rhythmogram${name ? ` "${name}"` : ''}: four-pendulum trace drawn on the canvas`);
  }
  function toggle() {
    if (player.done) { restart(); return; }
    player.playing = !player.playing; playBtn.textContent = player.playing ? 'Pause' : 'Play';
    if (!player.playing) player.present(true);
  }
  function readout(p, t) {
    const h = st.h, mode = player.mode === 'trail' ? 'trail' : player.mode === 'continuous' ? 'continuous' : 'standard';
    ro.innerHTML = `<div><span>t</span><b>${t.toFixed(1)} s</b></div><div><span>progress</span><b>${(p * 100).toFixed(0)}%</b></div>
      <div><span>duration · rate</span><b>${h.duration} s · ${h.sample_rate} Hz</b></div><div><span>mode</span><b>${mode}</b></div>
      <div><span>preset</span><b>${esc(bySlug[st.preset]?.name || 'custom')}</b></div>`;
    if (player.done) playBtn.textContent = 'Play again';
  }
  function fileName(ext) { return `rhythmogram_${st.preset || 'custom'}.${ext}`; }

  document.addEventListener('keydown', onKey);
  function onKey(e) {
    if (e.target.closest && e.target.closest('input, select, textarea, button')) return;
    if (e.key === ' ') { e.preventDefault(); toggle(); } else if (e.key === 'r' || e.key === 'R') restart();
  }

  envCb(st.h.envelope.mode);
  if (st.c.palette_name) paldesc.textContent = setup.palettes.find(p => p.name === st.c.palette_name)?.description || '';
  restart();
  let last = performance.now();
  const stop = animate(now => { const dt = (now - last) / 1000; last = now; player.step(dt); });
  onLeave(() => { stop(); document.removeEventListener('keydown', onKey); }); // replaces animate's own stop hook
});
