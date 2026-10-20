import http from 'node:http';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { URL } from 'node:url';
import { CATEGORIES, ROLES, applySafetyPolicy, confirmableCategory, createId, demoUserFromToken, inferMock } from './domain.js';

const PORT = Number(process.env.PORT || 3000);
const DATA_DIR = new URL('../data/', import.meta.url);
const DATA_FILE = new URL('../data/sortai.json', import.meta.url);
const emptyStore = () => ({ scans: [], inventory: [], auditEvents: [] });

async function loadStore() {
  if (!existsSync(DATA_FILE)) return emptyStore();
  return JSON.parse(await readFile(DATA_FILE, 'utf8'));
}
async function saveStore(store) {
  await mkdir(DATA_DIR, { recursive: true });
  await writeFile(DATA_FILE, JSON.stringify(store, null, 2));
}
async function body(req) {
  let text = '';
  for await (const chunk of req) text += chunk;
  return text ? JSON.parse(text) : {};
}
function send(res, status, payload) {
  res.writeHead(status, { 'content-type': 'application/json; charset=utf-8', 'access-control-allow-origin': '*' });
  res.end(JSON.stringify(payload));
}
function auth(req, requiredRole) {
  const token = req.headers.authorization?.replace(/^Bearer\s+/i, '');
  const user = demoUserFromToken(token);
  return user && (!requiredRole || user.role === requiredRole) ? user : null;
}
function error(res, status, message) { send(res, status, { error: message }); }

export function createServer() {
  return http.createServer(async (req, res) => {
    try {
      const url = new URL(req.url, `http://${req.headers.host || 'localhost'}`);
      if (req.method === 'OPTIONS') { res.writeHead(204); return res.end(); }
      if (req.method === 'GET' && url.pathname === '/health') return send(res, 200, { status: 'ok', service: 'sortai-api', phase: 1 });
      if (req.method === 'GET' && url.pathname === '/api/categories') return send(res, 200, Object.values(CATEGORIES));
      if (req.method === 'POST' && url.pathname === '/api/demo-login') {
        const data = await body(req);
        if (!ROLES.includes(data.role)) return error(res, 400, 'Role must be collector, recycler, or admin');
        return send(res, 200, { demoOnly: true, token: `demo-${data.role}`, user: demoUserFromToken(`demo-${data.role}`) });
      }
      if (req.method === 'POST' && url.pathname === '/api/scans') {
        const user = auth(req, 'collector');
        if (!user) return error(res, 401, 'Collector authentication required');
        const data = await body(req);
        if (!['whole-device', 'separated-component'].includes(data.mode)) return error(res, 400, 'mode must be whole-device or separated-component');
        const prediction = applySafetyPolicy(inferMock(data.filename));
        const store = await loadStore();
        const scan = { id: createId('scan'), collectorId: user.id, mode: data.mode, filename: data.filename || null, prediction, status: 'pending_confirmation', createdAt: new Date().toISOString() };
        store.scans.push(scan); store.auditEvents.push({ id: createId('audit'), action: 'scan.created', actorId: user.id, entityId: scan.id, at: scan.createdAt });
        await saveStore(store);
        return send(res, 201, scan);
      }
      const confirmMatch = url.pathname.match(/^\/api\/scans\/([^/]+)\/confirm$/);
      if (req.method === 'POST' && confirmMatch) {
        const user = auth(req, 'collector');
        if (!user) return error(res, 401, 'Collector authentication required');
        const store = await loadStore();
        const scan = store.scans.find((item) => item.id === confirmMatch[1]);
        if (!scan || scan.collectorId !== user.id) return error(res, 404, 'Scan not found');
        if (scan.status !== 'pending_confirmation') return error(res, 409, 'Scan has already been confirmed or cancelled');
        const data = await body(req);
        if (!confirmableCategory(data.confirmedCategory)) return error(res, 400, 'confirmedCategory is not a supported category');
        const predictedCategory = scan.prediction.category;
        const confirmed = applySafetyPolicy({ ...scan.prediction, category: data.confirmedCategory });
        scan.confirmedCategory = data.confirmedCategory; scan.confirmedAt = new Date().toISOString(); scan.status = 'confirmed'; scan.prediction = confirmed;
        const item = { id: createId('inventory'), scanId: scan.id, collectorId: user.id, category: data.confirmedCategory, predictedCategory, confidence: scan.prediction.confidence, crate: confirmed.crate, colour: confirmed.colour, safetyFlags: confirmed.reviewRequired ? ['review_required'] : [], quantity: data.quantity ?? 1, weightKg: data.weightKg ?? null, weightSource: data.weightKg == null ? 'not_measured' : 'manual', createdAt: scan.confirmedAt };
        store.inventory.push(item); store.auditEvents.push({ id: createId('audit'), action: 'inventory.confirmed', actorId: user.id, entityId: item.id, at: item.createdAt });
        await saveStore(store);
        return send(res, 201, { scan, inventoryItem: item });
      }
      if (req.method === 'GET' && url.pathname === '/api/inventory') {
        const user = auth(req, 'collector');
        if (!user) return error(res, 401, 'Collector authentication required');
        const store = await loadStore();
        return send(res, 200, { items: store.inventory.filter((item) => item.collectorId === user.id) });
      }
      return error(res, 404, 'Route not found');
    } catch (err) { console.error(err); return error(res, 500, 'Unexpected server error'); }
  });
}

if (process.argv[1] === new URL(import.meta.url).pathname) createServer().listen(PORT, () => console.log(`SortAI API listening on http://localhost:${PORT}`));
