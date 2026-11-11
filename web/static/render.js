// Canvas drawing of traces: port of gui/trace_renderer.py (symmetry, mirrors, velocity width/opacity) and
// effects/brushes.py (line, dot, airbrush, chalk, ribbon), with additive 'lighter' compositing like the desktop's
// QPainter CompositionMode_Plus. Also the trail-mode frame of gui/canvas.py and a full-trace renderer for thumbnails,
// PNG export and the gallery.
import { Engine, scaleTo, linspace, computeZ, applyPerspective, totalPoints } from './harmonograph_engine.js';
import { colorAt, widthAtSpeed, alphaAtSpeed } from './color.js';

const css = ([r, g, b], a) => `rgba(${r},${g},${b},${(a / 255).toFixed(3)})`;

// _build_transforms: N-fold rotation about the centre, each with optional horizontal / vertical / both mirrors.
export function transforms(cc, cx, cy) {
  const out = [], sym = Math.max(1, cc.symmetry_order | 0);
  for (let k = 0; k < sym; k++) {
    const a = sym > 1 ? 2 * Math.PI * k / sym : 0, c = Math.cos(a), s = Math.sin(a);
    const base = sym <= 1 ? (x, y) => [x, y] : (x, y) => [cx + (x - cx) * c - (y - cy) * s, cy + (x - cx) * s + (y - cy) * c];
    out.push(base);
    if (cc.mirror_horizontal) out.push((x, y) => { const p = base(x, y); return [2 * cx - p[0], p[1]]; });
    if (cc.mirror_vertical) out.push((x, y) => { const p = base(x, y); return [p[0], 2 * cy - p[1]]; });
    if (cc.mirror_horizontal && cc.mirror_vertical) out.push((x, y) => { const p = base(x, y); return [2 * cx - p[0], 2 * cy - p[1]]; });
  }
  return out;
}

// Normalised speed (0 slow .. 1 fast) of segment i, measured in pixels against the trace's pixel speed range
// (core/trace.py TraceState._pixel_speed_range). sp holds the 2-D pixel coordinates the speeds are measured on.
export function speedOf(sp, i, [smin, smax]) {
  const dx = sp.x[i + 1] - sp.x[i], dy = sp.y[i + 1] - sp.y[i], span = smax - smin;
  if (span < 1e-10) return 0;
  return Math.max(0, Math.min(1, (Math.sqrt(dx * dx + dy * dy) - smin) / span));
}

export function pixelSpeedRange(px) {
  let lo = Infinity, hi = -Infinity;
  for (let i = 0; i + 1 < px.x.length; i++) {
    const s = Math.hypot(px.x[i + 1] - px.x[i], px.y[i + 1] - px.y[i]);
    if (Number.isNaN(s)) continue;
    if (s < lo) lo = s; if (s > hi) hi = s;
  }
  return lo === Infinity ? [0.0, 1.0] : [lo, hi];
}

// Draw segments i0 .. i1-1 of a trace already in pixels (px.x, px.y). tOf(i) gives the gradient position 0..1.
// rand: seeded RNG for the chalk brush.
export function drawSegments(ctx, px, sp, i0, i1, tOf, cc, speedRange, w, h, rand = Math.random) {
  const tf = transforms(cc, w / 2, h / 2), vel = cc.velocity_width || cc.velocity_opacity;
  ctx.globalCompositeOperation = 'lighter';
  ctx.lineCap = 'round'; ctx.lineJoin = 'round';
  const brush = cc.brush_type || 'line';
  for (const T of tf) {
    let batchStyle = '', batchW = 0, batchN = 0;
    const flush = () => { if (batchN) { ctx.stroke(); batchN = 0; batchStyle = ''; } };
    for (let i = Math.max(0, i0); i < i1 && i + 1 < px.x.length; i++) {
      if (Number.isNaN(px.x[i]) || Number.isNaN(px.x[i + 1])) { flush(); continue; }
      const col = colorAt(cc, tOf(i));
      let width = cc.line_width;
      if (vel) { const s = speedOf(sp, i, speedRange); if (cc.velocity_width) width = widthAtSpeed(cc, s); if (cc.velocity_opacity) col[3] = alphaAtSpeed(cc, s); }
      const [x1, y1] = T(px.x[i], px.y[i]), [x2, y2] = T(px.x[i + 1], px.y[i + 1]);
      if (brush === 'line') {
        // consecutive segments of the same colour and width share one path (at most 12 segments, so crossings still add up)
        const style = css(col, col[3]), wq = Math.round(width * 10) / 10;
        if (style !== batchStyle || wq !== batchW || batchN >= 12) {
          flush(); ctx.beginPath(); ctx.strokeStyle = style; ctx.lineWidth = Math.max(0.1, wq); ctx.moveTo(x1, y1);
          batchStyle = style; batchW = wq;
        }
        ctx.lineTo(x2, y2); batchN++;
      } else {
        drawBrush(ctx, brush, x1, y1, x2, y2, col, width, rand);
      }
    }
    flush();
  }
  ctx.globalCompositeOperation = 'source-over';
}

function gauss(rand) { return Math.sqrt(-2 * Math.log(1 - rand())) * Math.cos(2 * Math.PI * rand()); }

// effects/brushes.py draw_segment for the non-line brushes
export function drawBrush(ctx, brush, x1, y1, x2, y2, col, width, rand) {
  const mx = (x1 + x2) / 2, my = (y1 + y2) / 2;
  if (brush === 'dot') {
    ctx.fillStyle = css(col, col[3]); ctx.beginPath(); ctx.arc(mx, my, width * 1.5, 0, 2 * Math.PI); ctx.fill();
  } else if (brush === 'airbrush') {
    const r = width * 4, g = ctx.createRadialGradient(mx, my, 0, mx, my, r);
    g.addColorStop(0, css(col, Math.min(80, col[3]))); g.addColorStop(1, css(col, 0));
    ctx.fillStyle = g; ctx.beginPath(); ctx.arc(mx, my, r, 0, 2 * Math.PI); ctx.fill();
  } else if (brush === 'chalk') {
    const scatter = width * 3, count = Math.max(2, Math.trunc(width * 2));
    ctx.fillStyle = css(col, Math.max(10, Math.trunc(col[3] / 3)));
    for (let k = 0; k < count; k++) {
      const t = rand(), px = x1 + t * (x2 - x1) + gauss(rand) * scatter, py = y1 + t * (y2 - y1) + gauss(rand) * scatter;
      const r = width * (0.3 + 0.7 * rand());
      ctx.beginPath(); ctx.arc(px, py, r, 0, 2 * Math.PI); ctx.fill();
    }
  } else if (brush === 'ribbon') {
    const dx = x2 - x1, dy = y2 - y1, len = Math.sqrt(dx * dx + dy * dy);
    if (len < 0.1) return;
    const nx = -dy / len, ny = dx / len, off = width * 0.5;
    ctx.lineWidth = Math.max(0.5, width * 0.3);
    ctx.strokeStyle = css(col, col[3]);
    ctx.beginPath(); ctx.moveTo(x1 + nx * off, y1 + ny * off); ctx.lineTo(x2 + nx * off, y2 + ny * off); ctx.stroke();
    ctx.strokeStyle = css(col, Math.max(20, Math.trunc(col[3] / 2)));
    ctx.beginPath(); ctx.moveTo(x1 - nx * off, y1 - ny * off); ctx.lineTo(x2 - nx * off, y2 - ny * off); ctx.stroke();
  }
}

// Full trace in pixels (TraceState.compute_full_normalized, margin 0.05) with optional 3D (canvas._apply_3d).
export function fullTrace(config, w, h, proj = null, margin = 0.05) {
  const eng = new Engine(config), data = eng.computeFull(), r = eng.ranges();
  const flat = { x: scaleTo(data.x, r.x, w, margin), y: scaleTo(data.y, r.y, h, margin) };
  const px = proj && proj.enabled ? project(flat, linspace(0, config.duration, data.x.length), proj, w, h, 0) : flat;
  // raw: the 2-D pixel trace that velocity speeds are measured on
  return { eng, raw: flat, px, speedRange: pixelSpeedRange(flat), n: data.x.length };
}

// Perspective projection of pixel coordinates about the canvas centre (z from the two Z pendulums at times t).
export function project(px, t, proj, w, h, extraRotY = 0) {
  const cx = w / 2, cy = h / 2, n = px.x.length;
  const xn = new Float64Array(n), yn = new Float64Array(n);
  for (let i = 0; i < n; i++) { xn[i] = (px.x[i] - cx) / cx; yn[i] = (px.y[i] - cy) / cy; }
  const z = computeZ(t, proj.z_pendulums);
  const p = applyPerspective(xn, yn, z, proj.focal_length, proj.rotation_x, proj.rotation_y + extraRotY);
  for (let i = 0; i < n; i++) { p.x[i] = p.x[i] * cx + cx; p.y[i] = p.y[i] * cy + cy; }
  return p;
}

// Render a whole configuration onto ctx (background + full trace), as export_png / render_full do.
export function renderFull(ctx, config, cc, w, h, { proj = null, rand = Math.random, maxSegments = Infinity, margin = 0.05 } = {}) {
  ctx.globalCompositeOperation = 'source-over';
  ctx.fillStyle = cc.bg_color; ctx.fillRect(0, 0, w, h);
  const tr = fullTrace(config, w, h, proj, margin);
  if (tr.n < 2) return tr;
  if (tr.n - 1 > maxSegments) { // thumbnails: every k-th point, like the desktop preset thumbnails
    const k = Math.ceil((tr.n - 1) / maxSegments), idx = [];
    for (let i = 0; i < tr.n; i += k) idx.push(i);
    const pick = a => Float64Array.from(idx, i => a[i]);
    const sub = { x: pick(tr.px.x), y: pick(tr.px.y) }, raw = { x: pick(tr.raw.x), y: pick(tr.raw.y) };
    const m = idx.length;
    drawSegments(ctx, sub, raw, 0, m - 1, i => i / Math.max(m - 1, 1), cc, tr.speedRange.map(v => v * k), w, h, rand);
  } else {
    drawSegments(ctx, tr.px, tr.raw, 0, tr.n - 1, i => i / Math.max(tr.n - 1, 1), cc, tr.speedRange, w, h, rand);
  }
  return tr;
}

// gui/canvas.py _draw_trail_frame: clear, optional per-pendulum trails, fading combined trail, bright head.
export function drawTrailFrame(ctx, tb, tc, cc, w, h) {
  ctx.globalCompositeOperation = 'source-over';
  ctx.fillStyle = cc.bg_color; ctx.fillRect(0, 0, w, h);
  ctx.globalCompositeOperation = 'lighter'; ctx.lineCap = 'round';
  const seg = (pts, j, style, width) => { ctx.strokeStyle = style; ctx.lineWidth = width; ctx.beginPath(); ctx.moveTo(pts[j][0], pts[j][1]); ctx.lineTo(pts[j + 1][0], pts[j + 1][1]); ctx.stroke(); };
  if (tc.show_pendulums) {
    tb.pend.forEach((pts, i) => {
      const rgb = hexRgb(tc.pendulum_colors[i]), n = pts.length;
      for (let j = 0; j + 1 < n; j++) seg(pts, j, css(rgb, Math.trunc(((j / Math.max(n - 1, 1)) ** tc.fade_power) * 80)), 0.8);
      if (n) { ctx.fillStyle = css(rgb, 180); ctx.beginPath(); ctx.arc(pts[n - 1][0], pts[n - 1][1], 3, 0, 2 * Math.PI); ctx.fill(); }
    });
  }
  const pts = tb.combined, n = pts.length;
  for (let j = 0; j + 1 < n; j++) {
    const t = (j / Math.max(n - 1, 1)) ** tc.fade_power, col = colorAt(cc, j / Math.max(n - 1, 1));
    seg(pts, j, css(col, Math.trunc(t * cc.line_alpha)), cc.line_width * (0.3 + 0.7 * t));
  }
  if (n) { ctx.fillStyle = css(colorAt(cc, 1.0), 255); ctx.beginPath(); ctx.arc(pts[n - 1][0], pts[n - 1][1], tc.point_size, 0, 2 * Math.PI); ctx.fill(); }
  ctx.globalCompositeOperation = 'source-over';
}
const hexRgb = h => [1, 3, 5].map(i => parseInt(h.slice(i, i + 2), 16));

export { totalPoints };
