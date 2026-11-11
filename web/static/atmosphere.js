// Port of effects/atmosphere.py: heat distortion, smoke glow, god rays, chromatic aberration, colour grading and
// film grain, applied in apply_atmosphere's order. Heat, rays, chromatic aberration and grading follow the NumPy/SciPy
// code step for step (postfx.test.mjs compares them with Python output). Smoke and grain use the same algorithm
// with a different random field (NumPy's RandomState(42/123/77) is replaced by a seeded mulberry32).
import { channels, join, toU8, uniformFilter, zoom, sampleBilinear } from './postfx.js';
import { rng } from './core.js';

export const hasAtmosphere = a => !!(a.smoke_glow || a.god_rays || a.chromatic_aberration || a.film_grain || a.heat_distortion || a.color_grading);

const cache = new Map();
function cached(key, fn) { if (!cache.has(key)) { if (cache.size > 12) cache.clear(); cache.set(key, fn()); } return cache.get(key); }

function noiseField(h, w, scale) {
  return cached(`noise${h}x${w}s${scale}`, () => {
    const sh = Math.max(4, Math.trunc(h / scale)), sw = Math.max(4, Math.trunc(w / scale));
    const r1 = rng(42), r2 = rng(123);
    const base = zoom(Float64Array.from({ length: sh * sw }, r1), sh, sw, h, w);
    const fine = zoom(Float64Array.from({ length: 4 * sh * sw }, r2), 2 * sh, 2 * sw, h, w);
    return base.map((v, i) => Math.max(0, Math.min(1, 0.6 * v + 0.4 * fine[i])));
  });
}
function grainField(h, w, size) {
  return cached(`grain${h}x${w}s${size}`, () => {
    const sh = Math.max(4, Math.trunc(h / size)), sw = Math.max(4, Math.trunc(w / size)), r = rng(77);
    const g = Float64Array.from({ length: sh * sw }, () => Math.sqrt(-2 * Math.log(1 - r())) * Math.cos(2 * Math.PI * r()));
    return zoom(g, sh, sw, h, w);
  });
}

export function heatDistortion(px, w, h, amplitude = 3.0, frequency = 0.02) {
  const n = w * h, c = channels(px, n), out = c.map(a => Float64Array.from(a));
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    const sy = y + amplitude * Math.sin(x * frequency * 2 * Math.PI * 0.7), sx = x + amplitude * Math.sin(y * frequency * 2 * Math.PI);
    for (let k = 0; k < 3; k++) out[k][y * w + x] = sampleBilinear(c[k], h, w, sy, sx, 'reflect');
  }
  return toU8(join(out, n), new Uint8ClampedArray(4 * n));
}

export function smokeGlow(px, w, h, intensity = 0.4, scale = 8.0) {
  const n = w * h, c = channels(px, n), noise = noiseField(h, w, scale), res = c.map(a => Float64Array.from(a));
  for (const [radius, weight] of [[3, 0.4], [8, 0.3], [20, 0.2], [40, 0.1]]) {
    for (let k = 0; k < 3; k++) {
      const b = uniformFilter(uniformFilter(c[k], h, w, radius), h, w, radius);
      for (let i = 0; i < n; i++) res[k][i] += b[i] * (weight * intensity) * (0.3 + 0.7 * noise[i]);
    }
  }
  return toU8(join(res, n), new Uint8ClampedArray(4 * n));
}

export function godRays(px, w, h, intensity = 0.5, samples = 24, decay = 0.95) {
  const n = w * h, c = channels(px, n), ds = 4, sh = Math.trunc(h / ds), sw = Math.trunc(w / ds);
  if (sh < 2 || sw < 2) return px;
  const small = [0, 1, 2].map(k => zoom(c[k], h, w, sh, sw));
  const acc = [0, 1, 2].map(() => new Float64Array(sh * sw));
  for (let y = 0; y < sh; y++) for (let x = 0; x < sw; x++) {
    const uy = y / sh, ux = x / sw, dy = (uy - 0.5) / samples, dx = (ux - 0.5) / samples;
    let cy = uy, cx = ux;
    for (let i = 0; i < samples; i++) {
      cy -= dy; cx -= dx;
      const syi = Math.min(sh - 1, Math.max(0, Math.trunc(cy * sh))), sxi = Math.min(sw - 1, Math.max(0, Math.trunc(cx * sw)));
      const wgt = decay ** i * 0.02, j = syi * sw + sxi;
      for (let k = 0; k < 3; k++) acc[k][y * sw + x] += small[k][j] * wgt;
    }
  }
  const res = c.map(a => Float64Array.from(a));
  for (let k = 0; k < 3; k++) { const up = zoom(acc[k], sh, sw, h, w); for (let i = 0; i < n; i++) res[k][i] += Math.fround(up[i] * intensity); }
  return toU8(join(res, n), new Uint8ClampedArray(4 * n));
}

// Red is scaled outward by 1 + 0.001*strength, blue inward (NumPy BGRA channels 2 and 0).
export function chromaticAberration(px, w, h, strength = 3.0) {
  const n = w * h, c = channels(px, n), out = new Uint8ClampedArray(px), cy = h / 2.0, cx = w / 2.0;
  for (const [k, s] of [[0, strength * 0.001], [2, -strength * 0.001]]) {
    const sc = 1.0 + s;
    for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
      const v = sampleBilinear(c[k], h, w, cy + (y - cy) / sc, cx + (x - cx) / sc, 'nearest');
      out[4 * (y * w + x) + k] = Math.trunc(Math.fround(v));
    }
  }
  return out;
}

// Split toning. shadow / highlight are [r, g, b] tints.
export function colorGrading(px, w, h, shadow = [0, 0, 10], highlight = [10, 5, 0], contrast = 1.0, saturation = 1.0) {
  const o = new Uint8ClampedArray(px);
  for (let i = 0; i < px.length; i += 4) {
    let rgb = [px[i], px[i + 1], px[i + 2]];
    const lum = Math.fround((rgb[0] + rgb[1] + rgb[2]) / 3);
    if (Math.abs(contrast - 1.0) > 0.01) rgb = rgb.map(v => (v - 128) * contrast + 128);
    if (Math.abs(saturation - 1.0) > 0.01) rgb = rgb.map(v => lum + (v - lum) * saturation);
    const ln = lum / 255.0;
    for (let k = 0; k < 3; k++) { const v = rgb[k] + (1.0 - ln) * shadow[k] + ln * highlight[k]; o[i + k] = v <= 0 ? 0 : v >= 255 ? 255 : Math.trunc(Math.fround(v)); }
  }
  return o;
}

export function filmGrain(px, w, h, intensity = 0.08, size = 1.5) {
  const g = grainField(h, w, size), o = new Uint8ClampedArray(px);
  for (let p = 0, i = 0; i < px.length; i += 4, p++) {
    const lum = (px[i] + px[i + 1] + px[i + 2]) / 3 / 255.0, d = g[p] * intensity * 255.0 * (4.0 * lum * (1.0 - lum));
    for (let k = 0; k < 3; k++) { const v = px[i + k] + d; o[i + k] = v <= 0 ? 0 : v >= 255 ? 255 : Math.trunc(v); }
  }
  return o;
}

// AtmosphereConfig chain in apply_atmosphere order.
export function applyAtmosphere(px, w, h, a) {
  if (a.heat_distortion) px = heatDistortion(px, w, h, a.heat_amplitude, a.heat_frequency);
  if (a.smoke_glow) px = smokeGlow(px, w, h, a.smoke_intensity, a.smoke_scale);
  if (a.god_rays) px = godRays(px, w, h, a.god_rays_intensity, a.god_rays_samples, a.god_rays_decay);
  if (a.chromatic_aberration) px = chromaticAberration(px, w, h, a.chromatic_strength);
  if (a.color_grading) px = colorGrading(px, w, h, [a.shadow_tint_r, a.shadow_tint_g, a.shadow_tint_b],
    [a.highlight_tint_r, a.highlight_tint_g, a.highlight_tint_b], a.grade_contrast, a.grade_saturation);
  if (a.film_grain) px = filmGrain(px, w, h, a.grain_intensity, a.grain_size);
  return px;
}
