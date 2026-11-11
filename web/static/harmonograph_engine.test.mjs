// Node test: the JS engine reproduces the Python numbers (core/harmonograph.py, core/trails.py, core/projection.py,
// core/morph.py). Reference values: tests/fixtures/engine_fixture.json from `python scripts/make_engine_fixture.py --write`;
// tests/test_web.py checks that file is current. Run: node web/static/harmonograph_engine.test.mjs
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { Engine, configFromDict, envelopeAt, computeZ, applyPerspective, TrailBuffer, morphConfig } from './harmonograph_engine.js';

const FIX = JSON.parse(readFileSync(new URL('../../tests/fixtures/engine_fixture.json', import.meta.url)));
const close = (a, b, tol, what) => {
  if (b === null) { assert.ok(Number.isNaN(a), `${what}: js ${a} vs py NaN`); return; }
  assert.ok(Math.abs(a - b) <= tol * Math.max(1, Math.abs(b)), `${what}: js ${a} vs py ${b}`);
};
let n = 0;

// 1. full traces (compute_full) of every preset and of synthetic configs covering FM/PM, envelopes, strobe, chorus, Duffing
for (const [name, c] of Object.entries(FIX.traces)) {
  const eng = new Engine(configFromDict(c.config));
  const { x, y } = eng.computeFull();
  assert.equal(x.length, c.n, `${name} length`);
  c.idx.forEach((i, k) => { close(x[i], c.x[k], 1e-9, `${name} x[${i}]`); close(y[i], c.y[k], 1e-9, `${name} y[${i}]`); });
  let nan = 0, sx = 0, sy = 0;
  for (let i = 0; i < x.length; i++) { if (Number.isNaN(x[i])) nan++; else { sx += x[i]; sy += y[i]; } }
  assert.equal(nan, c.nan_count, `${name} NaN count`);
  close(sx, c.sum_x, 1e-7, `${name} sum x`); close(sy, c.sum_y, 1e-7, `${name} sum y`);
  const r = eng.ranges();
  close(r.x[0], c.ranges[0][0], 1e-9, `${name} xmin`); close(r.y[1], c.ranges[1][1], 1e-9, `${name} ymax`);
  const s = eng.speedRange();
  close(s[0], c.speed_range[0], 1e-7, `${name} speed min`); close(s[1], c.speed_range[1], 1e-9, `${name} speed max`);
  n++;
}
// 2. compute_chunk, including the unbounded chunks of continuous mode
for (const c of FIX.chunks) {
  const { x, y } = new Engine(configFromDict(FIX.traces[c.name].config)).computeChunk(c.start, c.size, c.unbounded);
  assert.equal(x.length, c.len, `chunk ${c.name}@${c.start} length`);
  c.x.forEach((v, k) => { close(x[k * 37], v, 1e-9, `chunk ${c.name}@${c.start} x`); close(y[k * 37], c.y[k], 1e-9, 'chunk y'); });
  n++;
}
// 3. envelope modes
for (const e of FIX.envelopes) {
  e.t.forEach((t, k) => close(envelopeAt(t, e.damping, e), e.v[k], 1e-12, `envelope ${e.mode} f=${e.frequency} t=${t}`));
  n++;
}
// 4. 3D projection
const P = FIX.projection;
const z = computeZ(Float64Array.from(P.t), P.z_pendulums);
P.z.forEach((v, k) => close(z[k], v, 1e-12, `z[${k}]`));
for (const c of P.cases) {
  const xs = P.t.map(Math.cos), ys = P.t.map(t => Math.sin(1.3 * t));
  const r = applyPerspective(xs, ys, z, c.focal, c.rx, c.ry);
  c.x.forEach((v, k) => { close(r.x[k], v, 1e-12, `persp x f=${c.focal}`); close(r.y[k], c.y[k], 1e-12, 'persp y'); });
  n++;
}
// 5. trail buffer after 150 steps
const T = FIX.trails;
const tb = new TrailBuffer(configFromDict(FIX.traces[T.name].config), T.trail, T.width, T.height);
for (let i = 0; i < 6; i++) tb.advance(25);
assert.equal(tb.combined.length, T.combined.length);
T.combined.forEach((p, k) => { close(tb.combined[k][0], p[0], 1e-9, `trail ${k} x`); close(tb.combined[k][1], p[1], 1e-9, `trail ${k} y`); });
T.pendulums.forEach((tr, i) => { assert.equal(tb.pend[i].length, tr.length); tr.forEach((p, k) => close(tb.pend[i][k][i < 2 ? 0 : 1], p[i < 2 ? 0 : 1], 1e-9, `pend ${i}`)); });
n++;
// 6. morph_config
for (const m of FIX.morph || []) {
  const out = morphConfig(configFromDict(m.a), configFromDict(m.b), m.t);
  assert.deepEqual(out.envelope.mode, m.out.envelope.mode);
  close(out.duration, m.out.duration, 1e-12, 'morph duration');
  out.pendulums.forEach((p, i) => ['frequency', 'phase', 'amplitude', 'damping', 'fm_depth'].forEach(k => close(p[k], m.out.pendulums[i][k], 1e-12, `morph ${k}`)));
  n++;
}
console.log(`harmonograph_engine: ${n} checks passed`);
