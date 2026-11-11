// Cross-check: the browser engine (harmonograph_engine.js) against the Python engine (core/harmonograph.py) for
// every preset. The Python side is /api/trace/<slug> (compute_full sampled at 600 points, plus ranges and speed
// range); on the static site these were computed at build time. On the local app a random Smart Randomize
// configuration can also be sent to Python (POST /api/trace).
import { route, app, api, esc, isStatic, needsServer, rng } from './core.js';
import { Engine, configFromDict, smartRandom } from './harmonograph_engine.js';
import { loadSetup, button } from './ui.js';

function compare(cfg, py) {
  const t0 = performance.now(), eng = new Engine(cfg), { x, y } = eng.computeFull(), ms = performance.now() - t0;
  let worst = 0, nanOk = true, nan = 0;
  py.idx.forEach((i, k) => {
    if (py.x[k] === null) { nanOk = nanOk && Number.isNaN(x[i]); return; }
    worst = Math.max(worst, Math.abs(x[i] - py.x[k]), Math.abs(y[i] - py.y[k]));
  });
  for (const v of x) if (Number.isNaN(v)) nan++;
  const r = eng.ranges(), s = eng.speedRange();
  const rangeErr = Math.max(...[r.x[0] - py.x_range[0], r.x[1] - py.x_range[1], r.y[0] - py.y_range[0], r.y[1] - py.y_range[1], (s[1] - py.speed_range[1]) / Math.max(py.speed_range[1], 1e-12)].map(Math.abs));
  return { worst, rangeErr, ok: x.length === py.n && nanOk && nan === py.nan_count && worst < 1e-9 && rangeErr < 1e-9, ms, n: x.length, nan, xjs: x, yjs: y };
}

function plot(canvas, xs, ys, color) {
  const ctx = canvas.getContext('2d'), W = canvas.width;
  let lo = Infinity, hi = -Infinity;
  for (const v of [...xs, ...ys]) if (v !== null && !Number.isNaN(v)) { lo = Math.min(lo, v); hi = Math.max(hi, v); }
  const sc = v => 4 + (v - lo) / (hi - lo || 1) * (W - 8);
  ctx.strokeStyle = color; ctx.lineWidth = 0.8; ctx.beginPath();
  let pen = false;
  for (let k = 0; k < xs.length; k++) {
    if (xs[k] === null || Number.isNaN(xs[k])) { pen = false; continue; }
    if (pen) ctx.lineTo(sc(xs[k]), sc(ys[k])); else ctx.moveTo(sc(xs[k]), sc(ys[k]));
    pen = true;
  }
  ctx.stroke();
}

route('check', async () => {
  const setup = await loadSetup();
  app().innerHTML = `<p class="kicker">Cross-check</p><h1 class="glow">Browser engine vs Python engine</h1>
  <p class="lead">Each preset is computed twice: by NumPy (core/harmonograph.py, HarmonographEngine.compute_full) and by
  the JavaScript port running in this page. The table compares 600 sampled points, the strobe gaps, the x/y ranges and
  the speed range. Pink: Python samples; cyan: the browser trace at the same indices.</p>
  <p id="sum" class="callout a">Comparing...</p>
  <div id="custom"></div>
  <div class="scroll"><table class="check"><thead><tr><th>Preset</th><th>Python / JS</th><th>Points</th><th>Strobe gaps</th>
  <th>Max |Δ| of samples</th><th>Ranges</th><th>JS time</th><th></th></tr></thead><tbody id="rows"></tbody></table></div>`;
  const rows = app().querySelector('#rows');
  let okCount = 0, done = 0;
  for (const p of setup.presets) {
    const py = await api(`/trace/${p.slug}`);
    if (!rows.isConnected) return; // the page was left while comparing
    const r = compare(configFromDict(p.config), py);
    okCount += r.ok; done++;
    const tr = document.createElement('tr');
    tr.innerHTML = `<td><a href="#/studio?p=${encodeURIComponent(p.slug)}">${esc(p.name)}</a></td><td></td><td>${r.n.toLocaleString('en')}</td>
      <td>${r.nan.toLocaleString('en')}</td><td>${r.worst.toExponential(1)}</td><td>${r.rangeErr.toExponential(1)}</td><td>${r.ms.toFixed(0)} ms</td>
      <td class="${r.ok ? 'ok' : 'err'}">${r.ok ? 'match' : 'DIFFERS'}</td>`;
    const c = document.createElement('canvas');
    c.width = c.height = 96; c.setAttribute('role', 'img'); c.setAttribute('aria-label', `${p.name}: Python samples and JS trace overlaid`);
    tr.children[1].appendChild(c);
    rows.appendChild(tr);
    plot(c, py.x, py.y, 'rgba(255,79,216,.9)');
    plot(c, py.idx.map(i => r.xjs[i]), py.idx.map(i => r.yjs[i]), 'rgba(94,231,255,.55)');
    app().querySelector('#sum').textContent = `${okCount} of ${done} presets match the Python engine (tolerance 1e-9)${done < setup.presets.length ? '...' : '.'}`;
    await new Promise(res => setTimeout(res, 0));
    if (!rows.isConnected) return;
  }
  const cu = app().querySelector('#custom');
  if (isStatic()) { cu.innerHTML = needsServer('Checking a new random configuration against Python'); return; }
  let seed = 1;
  const out = document.createElement('p');
  button(cu, 'Check a random configuration with Python', async () => {
    const cfg = smartRandom(rng(seed++), true);
    out.textContent = 'Computing in Python...';
    const py = await api('/trace', { body: cfg });
    const r = compare(cfg, py);
    out.innerHTML = `Seed ${seed - 1}: ${r.n.toLocaleString('en')} points, max |Δ| ${r.worst.toExponential(1)} — <b class="${r.ok ? 'ok' : 'err'}">${r.ok ? 'match' : 'differs'}</b>`;
  }, true);
  cu.appendChild(out);
});
