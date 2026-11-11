// Static-site data layer: answers api() calls from the JSON files exported by scripts/build_static.py.
// Everything the pages draw is computed in the browser; only the Python reference traces of the presets are files
// (api/trace/<slug>.json). Checking a custom configuration against Python needs the local server.
const files = new Map();
async function file(rel) {
  if (!files.has(rel)) files.set(rel, fetch('api/' + rel + '.json').then(r => { if (!r.ok) throw new Error(`${r.status} ${rel}`); return r.json(); }));
  return files.get(rel);
}

export async function staticApi(path, body) {
  const clean = path.split('?')[0].replace(/^\/+/, '');
  if (body) throw new Error('Checking a custom configuration against the Python engine needs the local app (Python server).');
  return file(clean);
}
