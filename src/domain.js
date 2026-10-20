import crypto from 'node:crypto';

export const ROLES = Object.freeze(['collector', 'recycler', 'admin']);
export const CATEGORIES = Object.freeze({
  pcb: { id: 'pcb', label: 'Printed circuit boards', crate: 'Crate 1', colour: 'green', hazardous: false },
  battery: { id: 'battery', label: 'Batteries — hazardous', crate: 'Crate 2', colour: 'red', hazardous: true },
  motor: { id: 'motor', label: 'Copper coils, transformers, motors', crate: 'Crate 3', colour: 'orange', hazardous: false },
  cable: { id: 'cable', label: 'Cables and wires', crate: 'Crate 4', colour: 'yellow', hazardous: false },
  display: { id: 'display', label: 'Display panels', crate: 'Crate 5', colour: 'blue', hazardous: true },
  plastic: { id: 'plastic', label: 'Glass and engineered plastics', crate: 'Crate 6', colour: 'purple', hazardous: false },
  unknown: { id: 'unknown', label: 'Unknown / Needs Review', crate: 'Review state', colour: 'grey', hazardous: true }
});
const DEMO_USERS = Object.freeze({
  'demo-collector': { id: 'user-collector-demo', role: 'collector', displayName: 'Demo Collector' },
  'demo-recycler': { id: 'user-recycler-demo', role: 'recycler', displayName: 'Demo Recycler' },
  'demo-admin': { id: 'user-admin-demo', role: 'admin', displayName: 'Demo Administrator' }
});
export function demoUserFromToken(token) { return DEMO_USERS[token] ?? null; }
export function createId(prefix) { return `${prefix}_${crypto.randomUUID()}`; }
export function inferMock(filename = '') {
  const name = filename.toLowerCase();
  let category = 'unknown';
  if (/battery|cell|lithium|swollen/.test(name)) category = 'battery';
  else if (/phone|laptop|board|pcb|circuit/.test(name)) category = 'pcb';
  else if (/cable|wire|charger/.test(name)) category = 'cable';
  else if (/motor|fan|transformer|coil/.test(name)) category = 'motor';
  else if (/display|screen|tv|monitor/.test(name)) category = 'display';
  else if (/plastic|casing|glass/.test(name)) category = 'plastic';
  const confidence = category === 'unknown' ? 0.41 : category === 'battery' ? 0.86 : 0.9;
  return { category, confidence, provider: 'mock', modelVersion: 'mock-v1', inferenceMs: 3 };
}
export function applySafetyPolicy(prediction) {
  const category = CATEGORIES[prediction.category] ?? CATEGORIES.unknown;
  const reviewRequired = prediction.category === 'unknown' || prediction.confidence < 0.8 || category.hazardous;
  const warning = category.id === 'battery'
    ? 'Possible battery detected. Do not dismantle, cut, crush, or mix with ordinary scrap. Follow approved battery-handling procedures and request trained review.'
    : category.id === 'display'
      ? 'Display construction is not confirmed visually. Avoid breaking or dismantling it; request trained review for damaged or unknown displays.'
      : reviewRequired
        ? 'The result is uncertain. Keep the item separate from ordinary material and request human review.'
        : 'Prediction is a sorting aid, not a safety certification. Confirm the category before placing the item.';
  return { ...prediction, category: category.id, crate: category.crate, colour: category.colour, reviewRequired, warning };
}
export function confirmableCategory(id) { return typeof id === 'string' && Object.hasOwn(CATEGORIES, id); }
export { DEMO_USERS };
