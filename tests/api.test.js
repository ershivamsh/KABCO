import test, { after } from 'node:test';
import assert from 'node:assert/strict';
import { rm } from 'node:fs/promises';
import { createServer } from '../src/server.js';

const server = createServer();
await rm(new URL('../data/sortai.json', import.meta.url), { force: true });
await new Promise((resolve) => server.listen(0, resolve));
const base = `http://127.0.0.1:${server.address().port}`;
const json = (path, options = {}) => fetch(`${base}${path}`, { ...options, headers: { 'content-type': 'application/json', ...(options.headers || {}) } });
after(() => server.close());

test('health and categories are public', async () => {
  assert.equal((await json('/health')).status, 200);
  const response = await json('/api/categories');
  assert.equal(response.status, 200);
  assert.equal((await response.json()).length, 7);
});

test('collector can scan and confirm once; other roles cannot', async () => {
  const denied = await json('/api/scans', { method: 'POST', body: JSON.stringify({ mode: 'whole-device', filename: 'phone.jpg' }), headers: { authorization: 'Bearer demo-recycler' } });
  assert.equal(denied.status, 401);
  const scanResponse = await json('/api/scans', { method: 'POST', body: JSON.stringify({ mode: 'whole-device', filename: 'phone.jpg' }), headers: { authorization: 'Bearer demo-collector' } });
  assert.equal(scanResponse.status, 201);
  const scan = await scanResponse.json();
  assert.equal(scan.prediction.provider, 'mock');
  assert.equal(scan.prediction.colour, 'green');
  const confirmResponse = await json(`/api/scans/${scan.id}/confirm`, { method: 'POST', body: JSON.stringify({ confirmedCategory: 'pcb' }), headers: { authorization: 'Bearer demo-collector' } });
  assert.equal(confirmResponse.status, 201);
  const duplicate = await json(`/api/scans/${scan.id}/confirm`, { method: 'POST', body: JSON.stringify({ confirmedCategory: 'pcb' }), headers: { authorization: 'Bearer demo-collector' } });
  assert.equal(duplicate.status, 409);
  const inventory = await json('/api/inventory', { headers: { authorization: 'Bearer demo-collector' } });
  assert.equal((await inventory.json()).items.length, 1);
});
