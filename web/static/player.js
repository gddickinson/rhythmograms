// Animated drawing of a rhythmogram onto a canvas, like gui/canvas.py RhythmogramCanvas: progressive trace (300
// points per 16 ms at 1x), continuous mode with background fade, trail mode, 3D projection and the post-processing
// and atmosphere chains on the displayed image. Settings come from a Studio state object (see studio.js).
import { Engine, linspace, scaleTo, TrailBuffer, totalPoints } from './harmonograph_engine.js';
import { prepareColor } from './color.js';
import { drawSegments, drawTrailFrame, fullTrace, project, pixelSpeedRange } from './render.js';
import { applyEffects, hasEffects } from './postfx.js';
import { applyAtmosphere, hasAtmosphere } from './atmosphere.js';
import { rng } from './core.js';

export const POINTS_PER_SECOND = 300 / 0.016; // desktop: CHUNK_SIZE 300 every TIMER_INTERVAL_MS 16

// The configuration actually drawn: a disabled pendulum has amplitude 0 (gui/controls.py "Enabled").
export function effectiveConfig(st) {
  const h = JSON.parse(JSON.stringify(st.h));
  h.pendulums.forEach((p, i) => { if (!st.en[i]) p.amplitude = 0; });
  return h;
}

export class Player {
  constructor(display, onProgress = () => {}) {
    this.display = display; this.dctx = display.getContext('2d');
    this.expo = document.createElement('canvas'); this.ectx = this.expo.getContext('2d');
    this.onProgress = onProgress; this.playing = false; this.fxCost = 0; this.lastFx = 0; this.fxDirty = true;
  }

  setState(st) { this.st = st; }

  restart() {
    const st = this.st, W = this.display.width, H = this.display.height;
    this.expo.width = W; this.expo.height = H;
    this.cfg = effectiveConfig(st); this.cc = prepareColor(st.c); this.rand = rng(11);
    this.ectx.globalCompositeOperation = 'source-over';
    this.ectx.fillStyle = this.cc.bg_color; this.ectx.fillRect(0, 0, W, H);
    this.pos = 0; this.time = 0; this.mode = st.tr.enabled ? 'trail' : st.cont ? 'continuous' : 'finite';
    this.N = totalPoints(this.cfg); this.tr = null; this.tb = null; this.eng = null;
    if (this.mode === 'trail') this.tb = new TrailBuffer(this.cfg, st.tr, W, H);
    else if (this.mode === 'finite') this.tr = fullTrace(this.cfg, W, H);
    if (this.mode === 'continuous') {
      this.eng = new Engine(this.cfg); this.amp = this.eng.amplitudeRanges();
      const f = this.eng.computeFull(); // pixel speed range with the amplitude scaling, as TraceState(continuous=True)
      this.speedRange = pixelSpeedRange({ x: scaleTo(f.x, this.amp.x, W), y: scaleTo(f.y, this.amp.y, H) });
    }
    this.t = linspace(0, this.cfg.duration, this.N);
    this.fxDirty = true; this.playing = true; this.done = false;
    this.present(true);
  }

  // Advance by dt seconds of wall time; returns false when a finite drawing is complete.
  step(dt) {
    if (!this.playing || this.done) return;
    const st = this.st, W = this.display.width, H = this.display.height;
    const pts = Math.max(2, Math.round(POINTS_PER_SECOND * st.speed * Math.min(dt, 0.1)));
    if (this.mode === 'trail') {
      this.tb.advance(Math.max(1, Math.round(25 * st.speed * Math.min(dt, 0.1) / 0.016)));
      drawTrailFrame(this.ectx, this.tb, st.tr, this.cc, W, H);
      this.onProgress(Math.min(1, this.tb.currentTime / Math.max(this.cfg.duration, 1)), this.tb.currentTime);
    } else if (this.mode === 'finite') {
      const a = this.pos, b = Math.min(this.N - 1, a + pts);
      this.drawRange(this.tr.px, this.tr.raw, a, b, i => i / Math.max(this.N - 1, 1), this.tr.speedRange, this.t);
      this.pos = b;
      this.onProgress(this.N > 1 ? b / (this.N - 1) : 1, b / this.cfg.sample_rate);
      if (b >= this.N - 1) { this.done = true; this.playing = false; }
    } else {
      this.fade(st.fade);
      const chunk = this.chunk(this.pos, pts);
      const prog = (this.pos % this.N) / this.N;
      this.drawRange(chunk.px, chunk.raw, 0, chunk.px.x.length - 1, i => prog + i / this.N, chunk.speedRange, chunk.t);
      this.pos += pts;
      this.onProgress(prog, this.pos / this.cfg.sample_rate);
    }
    this.fxDirty = true;
    this.present(false);
  }

  // Unbounded chunk for continuous mode (compute_chunk, scaled with the amplitude ranges); Duffing configurations
  // continue their integration past the end of the trace, as on the desktop.
  chunk(pos, n) {
    const W = this.display.width, H = this.display.height;
    const raw = this.eng.computeChunk(pos, n, true), sr = this.cfg.sample_rate;
    const px = { x: scaleTo(raw.x, this.amp.x, W), y: scaleTo(raw.y, this.amp.y, H) };
    return { raw: px, px, speedRange: this.speedRange,
      t: linspace(pos / sr, (pos + n) / sr, n) };
  }

  drawRange(px, raw, a, b, tOf, speedRange, t) {
    const st = this.st, W = this.display.width, H = this.display.height;
    if (b <= a) return;
    if (st.p.enabled) { // project only this stretch (auto-rotate turns the view with drawing time, as on the desktop)
      const sl = arr => arr.subarray ? arr.subarray(a, b + 1) : arr.slice(a, b + 1);
      const extra = st.p.auto_rotate ? (b / this.cfg.sample_rate) * st.p.auto_rotate_speed : 0;
      const p = project({ x: sl(px.x), y: sl(px.y) }, sl(t), st.p, W, H, extra);
      drawSegments(this.ectx, p, { x: sl(raw.x), y: sl(raw.y) }, 0, b - a, i => tOf(i + a), this.cc, speedRange, W, H, this.rand);
    } else {
      drawSegments(this.ectx, px, raw, a, b, tOf, this.cc, speedRange, W, H, this.rand);
    }
  }

  fade(rate) {
    this.ectx.globalCompositeOperation = 'source-over';
    this.ectx.globalAlpha = rate / 255; this.ectx.fillStyle = this.cc.bg_color;
    this.ectx.fillRect(0, 0, this.expo.width, this.expo.height); this.ectx.globalAlpha = 1;
  }

  // Copy the exposure to the display, through the effects when any are on (throttled while drawing).
  present(force) {
    const st = this.st, W = this.display.width, H = this.display.height;
    const fx = hasEffects(st.e) || hasAtmosphere(st.a);
    if (!fx) { this.dctx.drawImage(this.expo, 0, 0); return; }
    const now = performance.now();
    if (!force && this.playing && now - this.lastFx < Math.max(200, 4 * this.fxCost)) return;
    if (!force && !this.fxDirty) return;
    const t0 = performance.now();
    const img = this.ectx.getImageData(0, 0, W, H);
    let px = applyEffects(img.data, W, H, st.e);
    px = applyAtmosphere(px, W, H, st.a);
    img.data.set(px);
    this.dctx.putImageData(img, 0, 0);
    this.fxCost = performance.now() - t0; this.lastFx = performance.now(); this.fxDirty = false;
  }
}
