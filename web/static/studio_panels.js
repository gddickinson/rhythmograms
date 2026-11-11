// Studio control tabs, laid out like the desktop app's right-hand tabs (Pend., Visual, Phys., Atmos). Ranges and
// labels follow the PyQt panels: gui/controls.py (pendulums, envelope), gui/effects_panel.py (colours, drawing,
// symmetry, 3D, post-processing), gui/physics_panel.py (FM/PM, strobe, chorus, trails), gui/atmosphere_panel.py.
// Change kinds passed to the binder: 't' redraw from the start, 'f' re-apply effects only.
import { esc } from './core.js';
import { group, tabs } from './ui.js';

const PEND_NAMES = ['X1 (Pendulum 1)', 'X2 (Pendulum 2)', 'Y1 (Pendulum 3)', 'Y2 (Pendulum 4)'];
// gui/controls.py EnvelopeControlGroup._update_description
export const ENVELOPE_TEXT = {
  none: 'Standard damping — trace decays to a point',
  breathe: 'Smooth pulsing — amplitude rises and falls sinusoidally',
  pulse: 'Energy kicks — damping resets periodically, trace snaps back',
  bounce: 'Triangle bounce — symmetric expansion and contraction cycles',
};

export function buildPanels(host, b, setup, { onPalette, onEnvelope }) {
  const { panels } = tabs(host, [['pend', 'Pend.'], ['visual', 'Visual'], ['phys', 'Phys.'], ['atmos', 'Atmos']]);
  pendulumTab(panels.pend, b, setup, onEnvelope);
  visualTab(panels.visual, b, setup, onPalette);
  physicsTab(panels.phys, b);
  atmosTab(panels.atmos, b);
}

function pendulumTab(host, b, setup, onEnvelope) {
  PEND_NAMES.forEach((name, i) => {
    const g = group(host, name);
    b.check(g, `en.${i}`, 'Enabled', 't');
    b.slider(g, `h.pendulums.${i}.frequency`, 'Frequency (Hz)', 0.1, 12.0, 0.001, 't', 3);
    b.slider(g, `h.pendulums.${i}.phase`, 'Phase (rad)', 0, 2 * Math.PI, 0.001, 't', 3);
    b.slider(g, `h.pendulums.${i}.amplitude`, 'Amplitude', 0, 1, 0.001, 't', 3);
    b.slider(g, `h.pendulums.${i}.damping`, 'Damping', 0, 0.15, 0.0001, 't', 4);
  });
  const g = group(host, 'Energy envelope');
  b.select(g, 'h.envelope.mode', 'Mode', setup.defaults.envelope_modes.map(m => [m, m]), 't');
  const d = document.createElement('p');
  d.className = 'small mute envdesc';
  g.appendChild(d);
  onEnvelope(mode => { d.textContent = ENVELOPE_TEXT[mode] || ''; });
  b.slider(g, 'h.envelope.frequency', 'Cycle Hz', 0.01, 1.0, 0.001, 't', 3);
  b.slider(g, 'h.envelope.strength', 'Strength', 0, 1, 0.01, 't', 2);
}

function visualTab(host, b, setup, onPalette) {
  let g = group(host, 'Palette');
  b.select(g, 'c.palette_name', 'Palette', [['', 'Custom'], ...setup.palettes.map(p => [p.name, p.name])], 't', v => onPalette(v));
  const desc = document.createElement('p');
  desc.className = 'small mute paldesc';
  g.appendChild(desc);

  g = group(host, 'Colors');
  const row = document.createElement('div'); row.className = 'colors'; g.appendChild(row);
  b.color(row, 'c.line_color', 'Line', 't'); b.color(row, 'c.bg_color', 'Background', 't');
  b.check(g, 'c.use_gradient', 'Use gradient', 't');
  b.select(g, 'c.interpolation', 'Mode', [['rgb', 'rgb'], ['hsv', 'hsv']], 't');
  const row2 = document.createElement('div'); row2.className = 'colors'; g.appendChild(row2);
  b.color(row2, 'c.gradient_start', 'Start', 't'); b.color(row2, 'c.gradient_end', 'End', 't'); b.color(row2, 'c.gradient_mid', 'Mid', 't');
  b.check(g, 'c.use_mid_color', 'Mid color (3-stop gradient)', 't');
  b.slider(g, 'c.line_alpha', 'Opacity', 10, 255, 1, 't');
  b.slider(g, 'c.line_width', 'Line width', 0.1, 10, 0.1, 't', 1);

  g = group(host, 'Drawing');
  b.select(g, 'c.brush_type', 'Brush', setup.defaults.brush_types.map(t => [t, t]), 't');
  b.check(g, 'c.velocity_width', 'Velocity-sensitive width (slow = thick)', 't');
  b.slider(g, 'c.velocity_width_min', 'Min width', 0.1, 5, 0.1, 't', 1);
  b.slider(g, 'c.velocity_width_max', 'Max width', 0.5, 15, 0.5, 't', 1);
  b.check(g, 'c.velocity_opacity', 'Velocity-sensitive opacity (slow = bright)', 't');

  g = group(host, 'Symmetry and mirrors');
  b.slider(g, 'c.symmetry_order', 'Rotational symmetry (fold)', 1, 12, 1, 't');
  b.check(g, 'c.mirror_horizontal', 'Mirror horizontal', 't');
  b.check(g, 'c.mirror_vertical', 'Mirror vertical', 't');

  g = group(host, '3D projection', 'Two Z-axis pendulums give depth; perspective x\' = f·x/(z+f).');
  b.check(g, 'p.enabled', 'Enable 3D depth', 't');
  b.slider(g, 'p.focal_length', 'Focal length', 0.5, 20, 0.5, 't', 1);
  b.slider(g, 'p.rotation_x', 'Rotate X (rad)', -3.14, 3.14, 0.01, 't', 2);
  b.slider(g, 'p.rotation_y', 'Rotate Y (rad)', -3.14, 3.14, 0.01, 't', 2);
  b.check(g, 'p.auto_rotate', 'Auto-rotate', 't');

  g = group(host, 'Post-processing');
  b.check(g, 'e.invert', 'Invert', 'f');
  b.check(g, 'e.solarize', 'Solarize', 'f');
  b.slider(g, 'e.solarize_threshold', 'Threshold', 0, 255, 1, 'f');
  b.check(g, 'e.bloom', 'Bloom / glow', 'f');
  b.slider(g, 'e.bloom_radius', 'Radius', 1, 20, 1, 'f');
  b.slider(g, 'e.bloom_intensity', 'Intensity', 0, 1, 0.01, 'f', 2);
  b.slider(g, 'e.bloom_layers', 'HDR layers', 1, 3, 1, 'f');
  b.check(g, 'e.vignette', 'Vignette', 'f');
  b.slider(g, 'e.vignette_strength', 'Strength', 0, 1, 0.01, 'f', 2);
  return desc;
}

function physicsTab(host, b) {
  PEND_NAMES.forEach((name, i) => {
    const g = group(host, `${name}: modulation`);
    b.slider(g, `h.pendulums.${i}.fm_freq`, 'FM rate (Hz)', 0, 5, 0.01, 't', 2);
    b.slider(g, `h.pendulums.${i}.fm_depth`, 'FM depth (Hz)', 0, 3, 0.01, 't', 2);
    b.slider(g, `h.pendulums.${i}.pm_freq`, 'PM rate (Hz)', 0, 5, 0.01, 't', 2);
    b.slider(g, `h.pendulums.${i}.pm_depth`, 'PM depth (rad)', 0, 3.14, 0.01, 't', 2);
    b.slider(g, `h.pendulums.${i}.nonlinearity`, 'Nonlinear (Duffing)', 0, 2, 0.001, 't', 3);
  });
  let g = group(host, 'Light extinction (strobe)');
  b.slider(g, 'h.strobe_freq', 'Strobe Hz (0 = off)', 0, 20, 0.1, 't', 1);
  b.slider(g, 'h.strobe_duty', 'Duty cycle', 0.1, 0.95, 0.05, 't', 2);
  g = group(host, 'Multi-trace chorus');
  b.slider(g, 'h.chorus_count', 'Copies (1 = off)', 1, 8, 1, 't');
  b.slider(g, 'h.chorus_spread', 'Spread (Hz)', 0.005, 0.1, 0.005, 't', 3);
  g = group(host, 'Trail mode', 'A moving point with a fading trail; optionally each pendulum\'s own contribution.');
  b.check(g, 'tr.enabled', 'Enable trail mode', 't');
  b.slider(g, 'tr.trail_length', 'Trail length', 50, 3000, 50, 't');
  b.slider(g, 'tr.point_size', 'Point size', 1, 10, 0.5, 't', 1);
  b.slider(g, 'tr.fade_power', 'Fade curve', 0.5, 3, 0.1, 't', 1);
  b.check(g, 'tr.show_pendulums', 'Show pendulum trails', 't');
  ['X1', 'X2', 'Y1', 'Y2'].forEach((n, i) => b.slider(g, `tr.pendulum_trail_lengths.${i}`, `${n} trail`, 50, 2000, 50, 't'));
}

function atmosTab(host, b) {
  host.insertAdjacentHTML('beforeend', `<p class="small mute">${esc('Atmospheric post-processing simulating light through smoke and air. Heavy effects are recomputed a few times a second while drawing.')}</p>`);
  let g = group(host, 'Smoke glow');
  b.check(g, 'a.smoke_glow', 'Enable smoke glow', 'f');
  b.slider(g, 'a.smoke_intensity', 'Intensity', 0.1, 1, 0.01, 'f', 2);
  b.slider(g, 'a.smoke_scale', 'Scale', 2, 20, 1, 'f');
  g = group(host, 'God rays');
  b.check(g, 'a.god_rays', 'Enable god rays', 'f');
  b.slider(g, 'a.god_rays_intensity', 'Intensity', 0.1, 1.5, 0.01, 'f', 2);
  b.slider(g, 'a.god_rays_decay', 'Decay', 0.85, 0.99, 0.01, 'f', 2);
  g = group(host, 'Chromatic aberration');
  b.check(g, 'a.chromatic_aberration', 'Enable', 'f');
  b.slider(g, 'a.chromatic_strength', 'Strength', 0.5, 15, 0.1, 'f', 1);
  g = group(host, 'Film grain');
  b.check(g, 'a.film_grain', 'Enable film grain', 'f');
  b.slider(g, 'a.grain_intensity', 'Intensity', 0.02, 0.2, 0.01, 'f', 2);
  b.slider(g, 'a.grain_size', 'Grain size', 1, 4, 0.1, 'f', 1);
  g = group(host, 'Heat distortion');
  b.check(g, 'a.heat_distortion', 'Enable heat distortion', 'f');
  b.slider(g, 'a.heat_amplitude', 'Amplitude', 1, 15, 0.1, 'f', 1);
  b.slider(g, 'a.heat_frequency', 'Frequency', 0.005, 0.05, 0.001, 'f', 3);
  g = group(host, 'Color grading');
  b.check(g, 'a.color_grading', 'Enable color grading', 'f');
  b.slider(g, 'a.grade_contrast', 'Contrast', 0.5, 2, 0.01, 'f', 2);
  b.slider(g, 'a.grade_saturation', 'Saturation', 0, 2, 0.01, 'f', 2);
  b.slider(g, 'a.shadow_tint_b', 'Shadow tint B', 0, 30, 1, 'f');
  b.slider(g, 'a.highlight_tint_r', 'Highlight tint R', 0, 30, 1, 'f');
}
