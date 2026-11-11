// Pure JS port of core/harmonograph.py (HarmonographEngine), core/pendulum.py (config defaults, smart_random),
// core/trails.py (TrailBuffer), core/projection.py (compute_z, apply_perspective) and core/morph.py (morph_config).
// Same formulas, same evaluation order, so the numbers match NumPy to ~1e-12 (harmonograph_engine.test.mjs checks
// them against tests/fixtures/engine_fixture.json, written by scripts/make_engine_fixture.py).
// No DOM here: the module runs in the browser and in node.

const PI = Math.PI;
export const ENVELOPE_MODES = ['none', 'breathe', 'pulse', 'bounce'];
const PEND_KEYS = ['frequency', 'phase', 'amplitude', 'damping', 'fm_freq', 'fm_depth', 'pm_freq', 'pm_depth', 'nonlinearity'];
const PEND_DEFAULT = { frequency: 1.0, phase: 0.0, amplitude: 1.0, damping: 0.01, fm_freq: 0, fm_depth: 0, pm_freq: 0, pm_depth: 0, nonlinearity: 0 };

// PendulumParams.from_dict / HarmonographConfig.from_dict (missing keys take the dataclass defaults).
export function pendulumFromDict(d = {}) {
  const p = { ...PEND_DEFAULT };
  for (const k of PEND_KEYS) if (d[k] != null) p[k] = +d[k];
  return p;
}
export function configFromDict(d) {
  if (!d || !Array.isArray(d.pendulums) || d.pendulums.length !== 4) throw new Error('Exactly 4 pendulums required');
  const e = d.envelope || {};
  return {
    pendulums: d.pendulums.map(pendulumFromDict),
    duration: d.duration ?? 60.0, sample_rate: d.sample_rate ?? 1000.0,
    envelope: { mode: e.mode ?? 'none', frequency: e.frequency ?? 0.1, strength: e.strength ?? 0.7 },
    strobe_freq: d.strobe_freq ?? 0.0, strobe_duty: d.strobe_duty ?? 0.5,
    chorus_count: d.chorus_count ?? 1, chorus_spread: d.chorus_spread ?? 0.02,
  };
}
export const cloneConfig = c => configFromDict(JSON.parse(JSON.stringify(c)));
export const totalPoints = c => Math.trunc(c.duration * c.sample_rate);

// numpy.linspace(start, stop, n) with endpoint=True.
export function linspace(start, stop, n) {
  const y = new Float64Array(Math.max(0, n));
  if (n === 1) { y[0] = start; return y; }
  const step = (stop - start) / (n - 1);
  for (let i = 0; i < n; i++) y[i] = i * step + start;
  if (n > 1) y[n - 1] = stop;
  return y;
}

// HarmonographEngine._compute_envelope for one time value.
export function envelopeAt(t, damping, env) {
  const base = Math.exp(-damping * t);
  if (env.mode === 'none' || env.strength <= 0) return base;
  const s = env.strength, f = Math.max(env.frequency, 0.001);
  if (env.mode === 'breathe') return base * ((1.0 - s) + s * (0.5 * (1.0 + Math.cos(2.0 * PI * f * t))));
  if (env.mode === 'pulse') { const period = 1.0 / f; return (1.0 - s) * base + s * Math.exp(-damping * (t % period)); }
  if (env.mode === 'bounce') {
    const period = 1.0 / f, phase = (t % period) / period;
    const tri = 1.0 - 2.0 * Math.abs(phase - 0.5);
    return (1.0 - s) * base + s * Math.sin(tri * PI * 0.5);
  }
  return base;
}

export class Engine {
  constructor(config) {
    this.config = config;
    const p = config.pendulums;
    this.freq = p.map(q => q.frequency * 2 * PI);
    this.phase = p.map(q => q.phase); this.amp = p.map(q => q.amplitude); this.damp = p.map(q => q.damping);
    this.fmFreq = p.map(q => q.fm_freq * 2 * PI); this.fmDepth = p.map(q => q.fm_depth * 2 * PI);
    this.pmFreq = p.map(q => q.pm_freq * 2 * PI); this.pmDepth = p.map(q => q.pm_depth);
    this.nonlin = p.map(q => q.nonlinearity);
    this.hasNonlin = this.nonlin.some(v => v !== 0);
    this._full = null;
  }

  computeFull() {
    if (!this._full) {
      const c = this.config, n = totalPoints(c), t = linspace(0, c.duration, n);
      this._full = this.computeWithChorus(t);
      if (this.hasNonlin) { this.nlFullEnd = this.nlOut; this.nlCursor = [n, this.nlOut]; this.nlStep = n > 1 ? t[1] - t[0] : 1.0 / c.sample_rate; }
    }
    return this._full;
  }

  computeChunk(startIdx, chunkSize, unbounded = false) {
    const n = totalPoints(this.config);
    let end = startIdx + chunkSize;
    if (!unbounded) { end = Math.min(end, n); if (startIdx >= n) return { x: new Float64Array(0), y: new Float64Array(0) }; }
    if (this.hasNonlin) { // cut from the full trajectory and continued past it, as compute_chunk does for Duffing pendulums
      const f = this.computeFull();
      if (end <= n) return { x: f.x.slice(startIdx, end), y: f.y.slice(startIdx, end) };
      return this.nonlinearBeyond(startIdx, end);
    }
    const sr = this.config.sample_rate;
    return this.computeWithChorus(linspace(startIdx / sr, end / sr, end - startIdx));
  }

  // _nonlinear_beyond: continue the Duffing integration past the full trace on its grid t_k = k * step.
  nonlinearBeyond(start, end) {
    const f = this.computeFull(), n = f.x.length;
    if (this.nlCursor[0] > Math.max(start, n)) this.nlCursor = [n, this.nlFullEnd];
    const xs = [f.x.slice(start, n)], ys = [f.y.slice(start, n)];
    let [idx, state] = this.nlCursor;
    while (idx < end) {
      const stop = idx < start ? Math.min(start, idx + 5000) : end;
      const r = this.computeWithChorus(Float64Array.from({ length: stop - idx }, (_, k) => (idx + k) * this.nlStep), state);
      state = this.nlOut;
      if (stop > start) { const off = Math.max(0, start - idx); xs.push(r.x.slice(off)); ys.push(r.y.slice(off)); }
      idx = stop;
    }
    this.nlCursor = [idx, state];
    const cat = a => { const o = new Float64Array(a.reduce((k, v) => k + v.length, 0)); let k = 0; for (const v of a) { o.set(v, k); k += v.length; } return o; };
    return { x: cat(xs), y: cat(ys) };
  }

  // nlState (Duffing only): per chorus copy, [states, scales] to continue from; the new ones are left in this.nlOut.
  computeWithChorus(t, nlState = null) {
    const cc = this.config;
    this.nlOut = [];
    if (cc.chorus_count <= 1) { const r = this.computeAt(t, nlState && nlState[0]); return this.applyStrobe(t, r.x, r.y); }
    const xa = new Float64Array(t.length), ya = new Float64Array(t.length);
    const nc = cc.chorus_count, scale = 1.0 / nc, orig = this.freq.slice();
    for (let i = 0; i < nc; i++) {
      const offset = (i - (nc - 1) / 2.0) * cc.chorus_spread;
      this.freq = orig.map(f => f + offset * 2 * PI);
      const r = this.computeAt(t, nlState && nlState[i]);
      this.freq = orig;
      for (let j = 0; j < t.length; j++) { xa[j] += r.x[j] * scale; ya[j] += r.y[j] * scale; }
    }
    return this.applyStrobe(t, xa, ya);
  }

  applyStrobe(t, x, y) {
    const sf = this.config.strobe_freq;
    if (sf <= 0) return { x, y };
    const period = 1.0 / sf, duty = this.config.strobe_duty;
    for (let j = 0; j < t.length; j++) if (!((t[j] % period) / period < duty)) { x[j] = NaN; y[j] = NaN; }
    return { x, y };
  }

  computeAt(t, nlState = null) {
    const env = this.config.envelope, n = t.length;
    if (this.hasNonlin) return this.computeNonlinear(t, env, nlState);
    const sig = [0, 1, 2, 3].map(() => new Float64Array(n));
    for (let i = 0; i < 4; i++) {
      const f0 = this.freq[i], fmd = this.fmDepth[i], fmf = this.fmFreq[i], p0 = this.phase[i], pmd = this.pmDepth[i], pmf = this.pmFreq[i];
      const a = this.amp[i], d = this.damp[i], s = sig[i];
      for (let j = 0; j < n; j++) {
        const tj = t[j];
        const freq = fmd !== 0 ? f0 + fmd * Math.sin(fmf * tj) : f0;
        const phase = pmd !== 0 ? p0 + pmd * Math.sin(pmf * tj) : p0;
        s[j] = (a * Math.sin(freq * tj + phase)) * envelopeAt(tj, d, env);
      }
    }
    const x = new Float64Array(n), y = new Float64Array(n);
    for (let j = 0; j < n; j++) { x[j] = sig[0][j] + sig[1][j]; y[j] = sig[2][j] + sig[3][j]; }
    return { x, y };
  }

  // RK4 Duffing integration exactly as _compute_nonlinear: released at x0 = A sin(phase), v0 = A w cos(phase);
  // phase modulation rotates the state in the (x, v/w) plane.
  computeNonlinear(t, env, nlState = null) {
    const n = t.length, dt = n > 1 ? t[1] - t[0] : 1.0 / this.config.sample_rate;
    const sig = [0, 1, 2, 3].map(() => new Float64Array(n)), finals = [], scales = [];
    for (let i = 0; i < 4; i++) {
      const omega = this.freq[i], d = this.damp[i], nl = this.nonlin[i], fmd = this.fmDepth[i], fmf = this.fmFreq[i];
      const pmd = this.pmDepth[i], pmf = this.pmFreq[i], rotate = pmd !== 0 && omega !== 0;
      let pos = this.amp[i] * Math.sin(this.phase[i]), vel = this.amp[i] * omega * Math.cos(this.phase[i]);
      if (nlState) [pos, vel] = nlState[0][i];
      const acc = (p, v, tt) => { const wt = omega + (fmd !== 0 ? fmd * Math.sin(fmf * tt) : 0); return -2 * d * v - wt * wt * p - nl * p * p * p; };
      const s = sig[i];
      for (let j = 0; j < n; j++) {
        const tj = t[j];
        if (rotate) { const dl = pmd * Math.sin(pmf * tj); s[j] = pos * Math.cos(dl) + vel / omega * Math.sin(dl); } else s[j] = pos;
        const k1v = vel, k1a = acc(pos, vel, tj);
        const k2v = vel + 0.5 * dt * k1a, k2a = acc(pos + 0.5 * dt * k1v, k2v, tj + 0.5 * dt);
        const k3v = vel + 0.5 * dt * k2a, k3a = acc(pos + 0.5 * dt * k2v, k3v, tj + 0.5 * dt);
        const k4v = vel + dt * k3a, k4a = acc(pos + dt * k3v, k4v, tj + dt);
        pos += dt / 6.0 * (k1v + 2 * k2v + 2 * k3v + k4v);
        vel += dt / 6.0 * (k1a + 2 * k2a + 2 * k3a + k4a);
      }
      finals.push([pos, vel]);
      let maxAbs = 0;
      if (nlState) maxAbs = nlState[1][i]; else for (let j = 0; j < n; j++) maxAbs = Math.max(maxAbs, Math.abs(s[j]));
      scales.push(maxAbs);
      for (let j = 0; j < n; j++) {
        if (maxAbs > 1e-10) s[j] = s[j] / maxAbs * this.amp[i];
        s[j] *= envelopeAt(t[j], d, env);
      }
    }
    this.nlOut.push([finals, scales]);
    const x = new Float64Array(n), y = new Float64Array(n);
    for (let j = 0; j < n; j++) { x[j] = sig[0][j] + sig[1][j]; y[j] = sig[2][j] + sig[3][j]; }
    return { x, y };
  }

  ranges() {
    const { x, y } = this.computeFull();
    const xr = validRange(x), yr = validRange(y);
    return xr ? { x: xr, y: yr } : { x: [-1, 1], y: [-1, 1] };
  }

  speedRange() {
    const { x, y } = this.computeFull();
    let lo = Infinity, hi = -Infinity;
    for (let j = 0; j + 1 < x.length; j++) {
      if (Number.isNaN(x[j]) || Number.isNaN(x[j + 1])) continue;
      const dx = x[j + 1] - x[j], dy = y[j + 1] - y[j], s = Math.sqrt(dx * dx + dy * dy);
      if (s < lo) lo = s; if (s > hi) hi = s;
    }
    return lo === Infinity ? [0.0, 1.0] : [lo, hi];
  }

  amplitudeRanges() {
    const a = this.amp, xm = a[0] + a[1], ym = a[2] + a[3];
    return { x: [-xm, xm], y: [-ym, ym] };
  }
}

function validRange(v) {
  let lo = Infinity, hi = -Infinity;
  for (const a of v) { if (Number.isNaN(a)) continue; if (a < lo) lo = a; if (a > hi) hi = a; }
  return lo === Infinity ? null : [lo, hi];
}

// HarmonographEngine._scale: data units -> pixels with a margin.
export function scaleTo(values, [vmin, vmax], size, margin = 0.05) {
  const out = new Float64Array(values.length), span = vmax - vmin;
  if (span < 1e-10) return out.fill(size / 2.0);
  const m = size * margin;
  for (let i = 0; i < values.length; i++) out[i] = m + (values[i] - vmin) / span * (size - 2 * m);
  return out;
}

// --- core/pendulum.py smart_random ------------------------------------------------------------------------------
const uniform = (r, a, b) => a + (b - a) * r();
const choice = (r, arr) => arr[Math.floor(r() * arr.length)];
export function smartPendulum(r, base, advanced) {
  const freq = base * choice(r, [1, 2, 3, 4, 5, 6]) + uniform(r, -0.02, 0.02);
  const p = pendulumFromDict({ frequency: Math.max(0.5, Math.min(12.0, freq)), phase: uniform(r, 0, 2 * PI),
    amplitude: uniform(r, 0.4, 1.0), damping: uniform(r, 0.005, 0.03) });
  if (advanced) {
    if (r() < 0.4) { p.fm_freq = uniform(r, 0.05, 0.5); p.fm_depth = uniform(r, 0.1, 0.5); }
    if (r() < 0.3) { p.pm_freq = uniform(r, 0.05, 0.4); p.pm_depth = uniform(r, 0.3, 1.5); }
    if (r() < 0.2) p.nonlinearity = uniform(r, 0.05, 0.3);
  }
  return p;
}
// HarmonographConfig.random() ("Randomize All")
export function randomConfig(r = Math.random) {
  return configFromDict({ pendulums: [0, 1, 2, 3].map(() => ({ frequency: uniform(r, 0.5, 8.0), phase: uniform(r, 0, 2 * PI),
    amplitude: uniform(r, 0.3, 1.0), damping: uniform(r, 0.001, 0.05) })) });
}
export function smartRandom(r = Math.random, advanced = false) {
  const base = choice(r, [1.0, 1.5, 2.0]);
  const c = configFromDict({ pendulums: [0, 1, 2, 3].map(() => smartPendulum(r, base, advanced)) });
  if (advanced) {
    if (r() < 0.3) { c.strobe_freq = choice(r, [1.0, 2.0, 3.0, 5.0, 8.0]); c.strobe_duty = uniform(r, 0.4, 0.8); }
    if (r() < 0.25) { c.chorus_count = choice(r, [2, 3, 4, 5]); c.chorus_spread = uniform(r, 0.01, 0.05); }
    if (r() < 0.25) c.envelope = { mode: choice(r, ['breathe', 'pulse', 'bounce']), frequency: uniform(r, 0.05, 0.2), strength: uniform(r, 0.3, 0.8) };
  }
  return c;
}

// --- core/projection.py -------------------------------------------------------------------------------------------
export function computeZ(t, zPendulums) {
  const z = new Float64Array(t.length);
  for (const p of zPendulums) {
    const f = p.frequency * 2 * PI;
    for (let j = 0; j < t.length; j++) z[j] += p.amplitude * Math.sin(f * t[j] + p.phase) * Math.exp(-p.damping * t[j]);
  }
  return z;
}
export function applyPerspective(x, y, z, focal, rotX = 0, rotY = 0) {
  const n = x.length, xp = new Float64Array(n), yp = new Float64Array(n);
  const cy_ = Math.cos(rotY), sy_ = Math.sin(rotY), cx_ = Math.cos(rotX), sx_ = Math.sin(rotX);
  for (let j = 0; j < n; j++) {
    let a = x[j], b = y[j], c = z[j];
    if (Math.abs(rotY) > 1e-6) { const a2 = a * cy_ + c * sy_; c = -a * sy_ + c * cy_; a = a2; }
    if (Math.abs(rotX) > 1e-6) { const b2 = b * cx_ - c * sx_; c = b * sx_ + c * cx_; b = b2; }
    let den = c + focal;
    if (Math.abs(den) < 0.01) den = 0.01;
    xp[j] = focal * a / den; yp[j] = focal * b / den;
  }
  return { x: xp, y: yp };
}

// --- core/morph.py morph_config (only frequency/phase/amplitude/damping, duration, sample rate and envelope) ---------
const lerp = (a, b, t) => a + t * (b - a);
export function morphConfig(c1, c2, t) {
  return configFromDict({
    pendulums: [0, 1, 2, 3].map(i => {
      const a = c1.pendulums[i], b = c2.pendulums[i];
      return { frequency: lerp(a.frequency, b.frequency, t), phase: lerp(a.phase, b.phase, t),
        amplitude: lerp(a.amplitude, b.amplitude, t), damping: lerp(a.damping, b.damping, t) };
    }),
    duration: lerp(c1.duration, c2.duration, t), sample_rate: Math.max(c1.sample_rate, c2.sample_rate),
    envelope: { mode: t < 0.5 ? c1.envelope.mode : c2.envelope.mode, frequency: lerp(c1.envelope.frequency, c2.envelope.frequency, t),
      strength: lerp(c1.envelope.strength, c2.envelope.strength, t) },
  });
}

// --- core/trails.py TrailBuffer (ring buffers of recent screen points) ----------------------------------------------
export class TrailBuffer {
  constructor(config, trail, width, height) {
    Object.assign(this, { config, trail, width, height, position: 0 });
    const eng = new Engine(config), r = eng.ranges();
    this.xRange = r.x; this.yRange = r.y;
    this.combined = []; this.pend = [[], [], [], []];
  }
  get currentTime() { return this.position / this.config.sample_rate; }
  advance(steps = 20) {
    const c = this.config, env = c.envelope, m = 0.05, mx = this.width * m, my = this.height * m;
    const [x0, x1] = this.xRange, [y0, y1] = this.yRange;
    const xs = x1 - x0 > 1e-10 ? x1 - x0 : 1.0, ys = y1 - y0 > 1e-10 ? y1 - y0 : 1.0;
    const cx = this.width / 2.0, cy = this.height / 2.0;
    const scx = (this.width - 2 * mx) / xs * 0.5, scy = (this.height - 2 * my) / ys * 0.5;
    for (let s = 0; s < steps; s++) {
      const t = this.position / c.sample_rate;
      this.position += 1;
      const sig = c.pendulums.map(p => {
        let freq = p.frequency * 2 * PI, phase = p.phase;
        if (p.fm_depth > 0) freq += p.fm_depth * 2 * PI * Math.sin(p.fm_freq * 2 * PI * t);
        if (p.pm_depth > 0) phase += p.pm_depth * Math.sin(p.pm_freq * 2 * PI * t);
        return p.amplitude * Math.sin(freq * t + phase) * envelopeAt(t, p.damping, env);
      });
      push(this.combined, [mx + (sig[0] + sig[1] - x0) / xs * (this.width - 2 * mx), my + (sig[2] + sig[3] - y0) / ys * (this.height - 2 * my)], this.trail.trail_length);
      const lens = this.trail.pendulum_trail_lengths;
      push(this.pend[0], [cx + sig[0] * scx, cy], lens[0]); push(this.pend[1], [cx + sig[1] * scx, cy], lens[1]);
      push(this.pend[2], [cx, cy + sig[2] * scy], lens[2]); push(this.pend[3], [cx, cy + sig[3] * scy], lens[3]);
    }
  }
}
function push(buf, pt, max) { buf.push(pt); if (buf.length > max) buf.splice(0, buf.length - max); }
