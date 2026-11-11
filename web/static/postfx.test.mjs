// Node test: trace colours (effects/color.py, values computed with PyQt6), post-processing (effects/postprocess.py)
// and atmosphere (effects/atmosphere.py) in JS against tests/fixtures/engine_fixture.json.
// Run: node web/static/postfx.test.mjs
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { prepareColor, colorAt, widthAtSpeed, alphaAtSpeed } from './color.js';
import { invert, solarize, bloom, vignette, uniformFilter, channels } from './postfx.js';
import { colorGrading, chromaticAberration, heatDistortion, godRays } from './atmosphere.js';

const FIX = JSON.parse(readFileSync(new URL('../../tests/fixtures/engine_fixture.json', import.meta.url)));
let n = 0;

// 1. gradient colours of every palette, RGB and HSV interpolation (QColor emulation), within 1/255
if (FIX.colors) {
  for (const g of FIX.colors.gradients) {
    const cc = prepareColor({ line_color: '#ffffff', bg_color: '#000000', gradient_start: g.start, gradient_end: g.end,
      gradient_mid: g.mid || '#808080', use_gradient: true, use_mid_color: !!g.mid, interpolation: g.interpolation, line_alpha: 170 });
    g.t.forEach((t, k) => {
      const js = colorAt(cc, t), py = g.rgba[k];
      js.forEach((v, c) => assert.ok(Math.abs(v - py[c]) <= 1, `${g.start}->${g.end} ${g.interpolation} t=${t}: js ${js} py ${py}`));
    });
    n++;
  }
  const cc = { velocity_width: true, velocity_opacity: true, velocity_width_min: 0.3, velocity_width_max: 3.0, velocity_opacity_min: 40, velocity_opacity_max: 255 };
  FIX.colors.speed.forEach((s, k) => { assert.ok(Math.abs(widthAtSpeed(cc, s) - FIX.colors.width[k]) < 1e-12); assert.equal(alphaAtSpeed(cc, s), FIX.colors.alpha[k]); });
  n++;
}

// 2. image effects on the fixture's BGRA test image (converted to RGBA here)
const P = FIX.postfx, W = P.w, H = P.h;
const bgraToRgba = a => { const o = new Uint8ClampedArray(a.length); for (let i = 0; i < a.length; i += 4) { o[i] = a[i + 2]; o[i + 1] = a[i + 1]; o[i + 2] = a[i]; o[i + 3] = a[i + 3]; } return o; };
const img = bgraToRgba(P.input);
function compare(name, js, tol = 1, maxBadFrac = 0) {
  const py = bgraToRgba(P[name]);
  let bad = 0, worst = 0;
  for (let i = 0; i < py.length; i++) { const d = Math.abs(js[i] - py[i]); worst = Math.max(worst, d); if (d > tol) bad++; }
  assert.ok(bad <= maxBadFrac * py.length, `${name}: ${bad} values differ by more than ${tol} (worst ${worst})`);
  n++;
}
compare('invert', invert(img), 0);
compare('solarize', solarize(img, 140), 0);
compare('bloom1', bloom(img, W, H, 2, 0.5, 1));
compare('bloom3', bloom(img, W, H, 1, 0.7, 3));
compare('vignette', vignette(img, W, H, 0.8));
compare('grading', colorGrading(img, W, H, [10, 3, 0], [0, 5, 10], 1.3, 0.6));
compare('chromatic', chromaticAberration(img, W, H, 40.0));
compare('heat', heatDistortion(img, W, H, 2.5, 0.07));
compare('rays', godRays(img, W, H, 0.9, 24, 0.95));
{ // the box blur behind the smoke glow (_fast_blur_rgb: two uniform_filter passes, mode 'nearest'), on the BGR channels
  const c = channels(Uint8ClampedArray.from(P.input), W * H);
  const py = P.fastblur;
  for (let k = 0; k < 3; k++) {
    const b = uniformFilter(uniformFilter(c[k], H, W, 2), H, W, 2);
    b.forEach((v, i) => assert.ok(Math.abs(v - py[3 * i + k]) < 1e-3, `fastblur ch${k}[${i}]: ${v} vs ${py[3 * i + k]}`));
  }
  n++;
}
console.log(`postfx: ${n} checks passed`);
