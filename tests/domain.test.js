import test from 'node:test';
import assert from 'node:assert/strict';
import { applySafetyPolicy, CATEGORIES, inferMock } from '../src/domain.js';

test('taxonomy preserves the required crate colours', () => {
  assert.equal(CATEGORIES.pcb.colour, 'green');
  assert.equal(CATEGORIES.battery.colour, 'red');
  assert.equal(CATEGORIES.motor.colour, 'orange');
  assert.equal(CATEGORIES.cable.colour, 'yellow');
  assert.equal(CATEGORIES.display.colour, 'blue');
  assert.equal(CATEGORIES.plastic.colour, 'purple');
  assert.equal(CATEGORIES.unknown.colour, 'grey');
});

test('battery predictions always require conservative review', () => {
  const result = applySafetyPolicy(inferMock('swollen-battery.jpg'));
  assert.equal(result.category, 'battery');
  assert.equal(result.reviewRequired, true);
  assert.match(result.warning, /Do not dismantle/);
});

test('unknown predictions reach Needs Review', () => {
  const result = applySafetyPolicy(inferMock('unrecognised-object.jpg'));
  assert.equal(result.category, 'unknown');
  assert.equal(result.reviewRequired, true);
});
