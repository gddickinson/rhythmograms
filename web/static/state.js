// Studio state: a fresh state from the API defaults, and a hand-off so other pages (Gallery, Morph) can open a
// configuration in the Studio.
import { go } from './core.js';
import { configFromDict } from './harmonograph_engine.js';

const clone = o => JSON.parse(JSON.stringify(o));
let handoff = null;

// h: HarmonographConfig, en: pendulum enabled flags, c: ColorConfig, e: EffectsConfig, a: AtmosphereConfig,
// p: Projection3DConfig, tr: TrailConfig (all as their to_dict() JSON); cont/fade: continuous mode; speed: web only.
export function freshState(setup) {
  const d = setup.defaults;
  return { h: configFromDict(d.harmonograph), en: [true, true, true, true], c: clone(d.color), e: clone(d.effects),
    a: clone(d.atmosphere), p: clone(d.projection), tr: clone(d.trail), cont: false, fade: 3, speed: 1, preset: '' };
}
export function openInStudio(partial) { handoff = clone(partial); go('#/studio'); }
export function takeHandoff() { const h = handoff; handoff = null; return h; }
