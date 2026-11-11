// Entry point: registers the lazily loaded pages, sets the footer mode text and starts the router.
import { start, route, lazy, app, isStatic, $ } from './core.js';

const PAGES = {
  'home.js': ['home'], 'studio.js': ['studio'], 'presets.js': ['presets', 'gallery'], 'morph.js': ['morph'],
  'check.js': ['check'], 'about.js': ['about'],
};
lazy(Object.fromEntries(Object.entries(PAGES).flatMap(([file, names]) => names.map(n => [n, () => import('./' + file)]))));

route('notfound', () => { app().innerHTML = '<h1>Not found</h1><p><a href="#/">Back to the start</a></p>'; });

$('#mode').textContent = isStatic()
  ? 'static site: the rhythmograms are drawn in your browser (JS port of the Python engine)'
  : 'local app: Python server on this machine';
start();
