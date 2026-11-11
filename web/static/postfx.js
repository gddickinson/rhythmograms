// Port of effects/postprocess.py (invert, solarize, multi-radius bloom, vignette) plus the image primitives the
// atmosphere effects share: scipy-compatible gaussian_filter / uniform_filter / map_coordinates (order 1) / zoom.
// Images are RGBA Uint8ClampedArray (canvas ImageData); NumPy's BGRA order is handled by the callers' channel indices.
// Results are truncated to integers like ndarray.astype(np.uint8) (a Uint8ClampedArray would round instead).

export const toU8 = (f, out) => { for (let i = 0; i < f.length; i++) { const v = f[i]; out[i] = v <= 0 ? 0 : v >= 255 ? 255 : Math.trunc(v); } return out; };

// Index mapping of scipy.ndimage boundary modes: 'reflect' (d c b a | a b c d | d c b a) and 'nearest'.
export function reflectIndex(i, n) { const p = 2 * n; let m = ((i % p) + p) % p; return m >= n ? p - 1 - m : m; }
export const nearestIndex = (i, n) => (i < 0 ? 0 : i >= n ? n - 1 : i);

// 1-D correlation along rows (axis 1) or columns (axis 0) of a single-channel float image.
function correlate1d(src, h, w, weights, axis, idx) {
  const r = (weights.length - 1) / 2, out = new Float64Array(src.length);
  if (axis === 1) {
    for (let y = 0; y < h; y++) {
      const row = y * w;
      for (let x = 0; x < w; x++) {
        let s = 0;
        for (let k = -r; k <= r; k++) { const xx = x + k; s += weights[k + r] * src[row + (xx >= 0 && xx < w ? xx : idx(xx, w))]; }
        out[row + x] = s;
      }
    }
  } else {
    for (let y = 0; y < h; y++) {
      for (let x = 0; x < w; x++) {
        let s = 0;
        for (let k = -r; k <= r; k++) { const yy = y + k; s += weights[k + r] * src[(yy >= 0 && yy < h ? yy : idx(yy, h)) * w + x]; }
        out[y * w + x] = s;
      }
    }
  }
  return out;
}

// scipy.ndimage.gaussian_filter(sigma, truncate=4.0, mode='reflect')
export function gaussianWeights(sigma) {
  const r = Math.trunc(4.0 * sigma + 0.5), w = [];
  let sum = 0;
  for (let k = -r; k <= r; k++) { const v = Math.exp(-0.5 / (sigma * sigma) * k * k); w.push(v); sum += v; }
  return w.map(v => v / sum);
}
export function gaussianFilter(src, h, w, sigma) {
  const wt = gaussianWeights(sigma);
  return correlate1d(correlate1d(src, h, w, wt, 0, reflectIndex), h, w, wt, 1, reflectIndex);
}

// Running-sum box filter, scipy.ndimage.uniform_filter(size=2r+1, mode='nearest') on one channel.
export function uniformFilter(src, h, w, r) {
  const ks = 2 * r + 1, tmp = new Float64Array(src.length), out = new Float64Array(src.length);
  for (let y = 0; y < h; y++) {
    let s = 0;
    for (let k = -r; k <= r; k++) s += src[y * w + nearestIndex(k, w)];
    for (let x = 0; x < w; x++) {
      tmp[y * w + x] = s / ks;
      s += src[y * w + nearestIndex(x + r + 1, w)] - src[y * w + nearestIndex(x - r, w)];
    }
  }
  for (let x = 0; x < w; x++) {
    let s = 0;
    for (let k = -r; k <= r; k++) s += tmp[nearestIndex(k, h) * w + x];
    for (let y = 0; y < h; y++) {
      out[y * w + x] = s / ks;
      s += tmp[nearestIndex(y + r + 1, h) * w + x] - tmp[nearestIndex(y - r, h) * w + x];
    }
  }
  return out;
}

// Split / join RGBA into float channels.
export function channels(px, n) {
  const c = [0, 1, 2, 3].map(() => new Float64Array(n));
  for (let i = 0; i < n; i++) { c[0][i] = px[4 * i]; c[1][i] = px[4 * i + 1]; c[2][i] = px[4 * i + 2]; c[3][i] = px[4 * i + 3]; }
  return c;
}
export function join(c, n) {
  const f = new Float64Array(4 * n);
  for (let i = 0; i < n; i++) { f[4 * i] = c[0][i]; f[4 * i + 1] = c[1][i]; f[4 * i + 2] = c[2][i]; f[4 * i + 3] = c[3][i]; }
  return f;
}

// map_coordinates(order=1) sample of one channel at fractional (sy, sx); mode 'nearest' or 'reflect'.
function mapCoord(c, n, mode) {
  if (mode === 'nearest') return c < 0 ? 0 : c > n - 1 ? n - 1 : c;
  if (c < 0) { const p = 2 * n; if (c < -p) c = p * Math.trunc(-c / p) + c; return c < -n ? c + p : -c - 1; }
  if (c > n - 1) { const p = 2 * n; c -= p * Math.trunc(c / p); if (c >= n) c = p - c - 1; }
  return c;
}
export function sampleBilinear(ch, h, w, sy, sx, mode) {
  const idx = mode === 'nearest' ? nearestIndex : reflectIndex;
  const y = mapCoord(sy, h, mode), x = mapCoord(sx, w, mode);
  const y0 = Math.floor(y), x0 = Math.floor(x), fy = y - y0, fx = x - x0;
  const ya = idx(y0, h), yb = idx(y0 + 1, h), xa = idx(x0, w), xb = idx(x0 + 1, w);
  return (1 - fy) * ((1 - fx) * ch[ya * w + xa] + fx * ch[ya * w + xb]) + fy * ((1 - fx) * ch[yb * w + xa] + fx * ch[yb * w + xb]);
}

// scipy.ndimage.zoom(order=1) of one channel from (h, w) to (oh, ow) (corner-aligned, grid_mode=False).
export function zoom(ch, h, w, oh, ow) {
  const out = new Float64Array(oh * ow);
  const ry = oh > 1 ? (h - 1) / (oh - 1) : 0, rx = ow > 1 ? (w - 1) / (ow - 1) : 0;
  for (let y = 0; y < oh; y++) for (let x = 0; x < ow; x++) out[y * ow + x] = sampleBilinear(ch, h, w, y * ry, x * rx, 'nearest');
  return out;
}

// --- effects/postprocess.py ------------------------------------------------------------------------------------
export function invert(px) { const o = new Uint8ClampedArray(px); for (let i = 0; i < o.length; i += 4) { o[i] = 255 - o[i]; o[i + 1] = 255 - o[i + 1]; o[i + 2] = 255 - o[i + 2]; } return o; }
export function solarize(px, thr = 128) {
  const o = new Uint8ClampedArray(px);
  for (let i = 0; i < o.length; i++) if ((i & 3) !== 3 && o[i] > thr) o[i] = 255 - o[i];
  return o;
}
export function bloom(px, w, h, radius = 5, intensity = 0.4, layers = 1) {
  const n = w * h, c = channels(px, n), res = c.map(a => Float64Array.from(a));
  const add = (sigma, k) => { for (let ch = 0; ch < 3; ch++) { const b = gaussianFilter(c[ch], h, w, sigma); for (let i = 0; i < n; i++) res[ch][i] += b[i] * k; } for (let i = 0; i < n; i++) res[3][i] += c[3][i] * k; };
  if (layers <= 1) add(radius, intensity);
  else for (let i = 0; i < layers; i++) add(radius * 2 ** i, intensity / 1.5 ** i);
  return toU8(join(res, n), new Uint8ClampedArray(4 * n));
}
export function vignette(px, w, h, strength = 0.5) {
  const o = new Uint8ClampedArray(px.length), cy = h / 2.0, cx = w / 2.0, md = Math.sqrt(cx * cx + cy * cy);
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    const d = Math.fround(Math.sqrt((x - cx) ** 2 + (y - cy) ** 2) / md), m = Math.max(0, Math.min(1, 1.0 - strength * d * d));
    const i = 4 * (y * w + x);
    for (let k = 0; k < 3; k++) o[i + k] = Math.min(255, Math.trunc(px[i + k] * m));
    o[i + 3] = px[i + 3];
  }
  return o;
}
// EffectsConfig chain in apply_effects order: bloom, vignette, solarize, invert.
export function applyEffects(px, w, h, ec) {
  if (ec.bloom) px = bloom(px, w, h, ec.bloom_radius, ec.bloom_intensity, ec.bloom_layers);
  if (ec.vignette) px = vignette(px, w, h, ec.vignette_strength);
  if (ec.solarize) px = solarize(px, ec.solarize_threshold);
  if (ec.invert) px = invert(px);
  return px;
}
export const hasEffects = ec => !!(ec.invert || ec.solarize || ec.bloom || ec.vignette);
