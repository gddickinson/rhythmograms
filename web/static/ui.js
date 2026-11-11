// Small form helpers for the Studio and the other pages: a Binder that ties sliders, checkboxes, selects and colour
// pickers to paths in a state object (and re-syncs them after a preset or file is loaded), tabs, and shared loaders.
import { api, esc } from './core.js';

let uid = 0;
const getPath = (o, path) => path.split('.').reduce((a, k) => a?.[k], o);
function setPath(o, path, v) { const ks = path.split('.'), last = ks.pop(); ks.reduce((a, k) => a[k], o)[last] = v; }
export const fmtNum = (v, d) => (d == null ? String(v) : Number(v).toFixed(d));

export class Binder {
  // state(): the object paths refer to; onChange(kind, path) after a user edit
  constructor(state, onChange) { this.state = state; this.onChange = onChange; this.items = []; }
  _add(sync) { this.items.push(sync); sync(); }
  refresh() { this.items.forEach(s => s()); }
  get(path) { return getPath(this.state(), path); }
  set(path, v, kind) { setPath(this.state(), path, v); this.onChange(kind, path); }

  slider(host, path, label, min, max, step, kind, dec = null) {
    const id = `b${uid++}`, wrap = document.createElement('div');
    wrap.className = 'ctl';
    wrap.innerHTML = `<label for="${id}">${esc(label)} <b></b></label><input type="range" id="${id}" min="${min}" max="${max}" step="${step}">`;
    host.appendChild(wrap);
    const input = wrap.querySelector('input'), out = wrap.querySelector('b');
    input.addEventListener('input', () => { out.textContent = fmtNum(+input.value, dec); this.set(path, +input.value, kind); });
    this._add(() => { const v = this.get(path); input.value = v; out.textContent = fmtNum(v, dec); });
    return input;
  }
  check(host, path, label, kind) {
    const id = `b${uid++}`, wrap = document.createElement('div');
    wrap.className = 'chk';
    wrap.innerHTML = `<input type="checkbox" id="${id}"><label for="${id}">${esc(label)}</label>`;
    host.appendChild(wrap);
    const input = wrap.querySelector('input');
    input.addEventListener('change', () => this.set(path, input.checked, kind));
    this._add(() => { input.checked = !!this.get(path); });
    return input;
  }
  select(host, path, label, options, kind, onPick = null) {
    const id = `b${uid++}`, wrap = document.createElement('div');
    wrap.className = 'ctl';
    wrap.innerHTML = `<label for="${id}">${esc(label)}</label><select id="${id}">${options.map(([v, t]) => `<option value="${esc(v)}">${esc(t)}</option>`).join('')}</select>`;
    host.appendChild(wrap);
    const sel = wrap.querySelector('select');
    sel.addEventListener('change', () => (onPick ? onPick(sel.value) : this.set(path, typeof this.get(path) === 'number' ? +sel.value : sel.value, kind)));
    if (path) this._add(() => { sel.value = String(this.get(path)); });
    return sel;
  }
  color(host, path, label, kind) {
    const id = `b${uid++}`, wrap = document.createElement('div');
    wrap.className = 'ctl color';
    wrap.innerHTML = `<input type="color" id="${id}"><label for="${id}">${esc(label)}</label>`;
    host.appendChild(wrap);
    const input = wrap.querySelector('input');
    input.addEventListener('input', () => this.set(path, input.value, kind));
    this._add(() => { input.value = this.get(path); });
    return input;
  }
}

export function group(host, title, note = '') {
  const g = document.createElement('fieldset');
  g.className = 'grp';
  g.innerHTML = `<legend>${esc(title)}</legend>${note ? `<p class="small mute">${esc(note)}</p>` : ''}`;
  host.appendChild(g);
  return g;
}

export function button(host, text, fn, alt = false, title = '') {
  const b = document.createElement('button');
  b.type = 'button'; b.textContent = text; if (alt) b.className = 'alt'; if (title) b.title = title;
  b.addEventListener('click', fn);
  host.appendChild(b);
  return b;
}

// Tabs with buttons (role=tab) and panels; returns { panels: {name: element}, show(name) }.
export function tabs(host, names) {
  const bar = document.createElement('div'), panels = {};
  bar.className = 'tabs'; bar.setAttribute('role', 'tablist');
  host.appendChild(bar);
  for (const [key, label] of names) {
    const b = document.createElement('button');
    b.type = 'button'; b.textContent = label; b.setAttribute('role', 'tab'); b.dataset.tab = key;
    b.addEventListener('click', () => show(key));
    bar.appendChild(b);
    const p = document.createElement('div');
    p.className = 'tabpanel'; p.setAttribute('role', 'tabpanel'); p.setAttribute('aria-label', label);
    host.appendChild(p);
    panels[key] = p;
  }
  function show(key) {
    for (const b of bar.children) { const on = b.dataset.tab === key; b.classList.toggle('on', on); b.setAttribute('aria-selected', on); }
    for (const [k, p] of Object.entries(panels)) p.hidden = k !== key;
  }
  show(names[0][0]);
  return { panels, show };
}

// Presets, palettes and defaults in one call (cached by api()).
export async function loadSetup() {
  const [presets, palettes, defaults] = await Promise.all([api('/presets'), api('/palettes'), api('/defaults')]);
  return { presets: presets.presets, palettes: palettes.palettes, defaults };
}

// Thumbnail canvas element with an accessible label.
export function thumbCanvas(size, label) {
  const c = document.createElement('canvas');
  c.width = size; c.height = size; c.setAttribute('role', 'img'); c.setAttribute('aria-label', label);
  return c;
}
