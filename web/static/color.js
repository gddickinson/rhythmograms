// Port of effects/color.py ColorConfig: trace colour along the drawing (solid, 2- or 3-stop gradient, RGB or HSV
// interpolation along the shortest hue arc) and velocity-sensitive width / opacity. QColor's HSV conversion is
// emulated (16-bit channels, hue in 1/100 degree, float32 maths) so colours match the desktop app to within 1/255
// (postfx.test.mjs checks this against values computed with PyQt6).

const U = 65535, f32 = Math.fround;
const qRound = v => (v >= 0 ? Math.floor(v + 0.5) : Math.ceil(v - 0.5));
const div257 = x => (x - (x >> 8) + 0x80) >> 8;

export function hexToRgb(hex) {
  const h = String(hex).replace('#', '');
  const v = h.length === 3 ? h.split('').map(c => c + c).join('') : h.padEnd(6, '0').slice(0, 6);
  return [parseInt(v.slice(0, 2), 16), parseInt(v.slice(2, 4), 16), parseInt(v.slice(4, 6), 16)];
}
export const rgbToHex = ([r, g, b]) => '#' + [r, g, b].map(v => Math.round(v).toString(16).padStart(2, '0')).join('');

// QColor::toHsv for an 8-bit RGB colour: [hueF (-1 if achromatic), saturationF, valueF]
function toHsvF([r8, g8, b8]) {
  const r = f32(r8 * 257 / U), g = f32(g8 * 257 / U), b = f32(b8 * 257 / U);
  const max = Math.max(r, g, b), min = Math.min(r, g, b), delta = f32(max - min);
  const value = qRound(f32(max * U));
  if (Math.abs(delta) <= 0.00001) return [-1, 0, value / U];
  const sat = qRound(f32(f32(delta / max) * U));
  let hue;
  if (r === max) hue = f32((g - b) / delta);
  else if (g === max) hue = f32(2 + f32((b - r) / delta));
  else hue = f32(4 + f32((r - g) / delta));
  hue = f32(hue * 60); if (hue < 0) hue = f32(hue + 360);
  return [qRound(f32(hue * 100)) / 36000, sat / U, value / U];
}

// QColor.fromHsvF(h, s, v) followed by red()/green()/blue()
function fromHsvF(hF, sF, vF) {
  const hue = qRound(hF * 36000), sat = qRound(sF * U), val = qRound(vF * U);
  if (sat === 0) { const c = div257(val); return [c, c, c]; }
  const h = hue === 36000 ? 0 : f32(hue / 6000), s = f32(sat / U), v = f32(val / U);
  const i = Math.trunc(h), f = f32(h - i), p = f32(v * f32(1 - s));
  let rgb;
  if (i & 1) {
    const q = f32(v * f32(1 - f32(s * f)));
    rgb = i === 1 ? [q, v, p] : i === 3 ? [p, q, v] : [v, p, q];
  } else {
    const t = f32(v * f32(1 - f32(s * f32(1 - f))));
    rgb = i === 0 ? [v, t, p] : i === 2 ? [p, v, t] : [t, p, v];
  }
  return rgb.map(c => div257(qRound(f32(c * U))));
}

function interpRgb(c1, c2, t) { return [0, 1, 2].map(k => Math.trunc(c1[k] + t * (c2[k] - c1[k]))); }

function interpHsv(c1, c2, t) {
  let [h1, s1, v1] = toHsvF(c1), [h2, s2, v2] = toHsvF(c2);
  if (h1 < 0) h1 = h2;
  if (h2 < 0) h2 = h1;
  if (h1 < 0 && h2 < 0) { h1 = 0; h2 = 0; }
  const dh = h2 - h1;
  if (dh > 0.5) h1 += 1.0; else if (dh < -0.5) h2 += 1.0;
  const h = ((h1 + t * (h2 - h1)) % 1.0 + 1.0) % 1.0;
  const cl = v => Math.max(0, Math.min(1, v));
  return fromHsvF(h, cl(s1 + t * (s2 - s1)), cl(v1 + t * (v2 - v1)));
}

// A ColorConfig-like object (the JSON of ColorConfig.to_dict) with parsed colours cached.
export function prepareColor(cc) {
  return { ...cc, _line: hexToRgb(cc.line_color), _start: hexToRgb(cc.gradient_start), _mid: hexToRgb(cc.gradient_mid),
    _end: hexToRgb(cc.gradient_end), _bg: hexToRgb(cc.bg_color) };
}

// ColorConfig.color_at -> [r, g, b, a] (0-255)
export function colorAt(cc, t) {
  if (!cc.use_gradient) return [...cc._line, cc.line_alpha];
  const interp = (a, b, u) => { u = Math.max(0, Math.min(1, u)); return cc.interpolation === 'hsv' ? interpHsv(a, b, u) : interpRgb(a, b, u); };
  let rgb;
  if (cc.use_mid_color) rgb = t < 0.5 ? interp(cc._start, cc._mid, t * 2.0) : interp(cc._mid, cc._end, (t - 0.5) * 2.0);
  else rgb = interp(cc._start, cc._end, t);
  return [...rgb, cc.line_alpha];
}

// ColorConfig.width_at_speed / alpha_at_speed: slow -> thick and bright (speed normalised 0..1)
export function widthAtSpeed(cc, s) {
  return cc.velocity_width ? cc.velocity_width_min + (1.0 - s) * (cc.velocity_width_max - cc.velocity_width_min) : cc.line_width;
}
export function alphaAtSpeed(cc, s) {
  return cc.velocity_opacity ? Math.trunc(cc.velocity_opacity_min + (1.0 - s) * (cc.velocity_opacity_max - cc.velocity_opacity_min)) : cc.line_alpha;
}

// effects/palettes.py palette applied as the desktop Visual tab does (_on_palette_change)
export function applyPalette(cc, p) {
  return { ...cc, palette_name: p.name, bg_color: p.bg, gradient_start: p.start, gradient_end: p.end, use_gradient: true,
    interpolation: p.interpolation, use_mid_color: !!p.mid, gradient_mid: p.mid || cc.gradient_mid };
}
