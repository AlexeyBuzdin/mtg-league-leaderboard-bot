import { test } from 'node:test';
import assert from 'node:assert/strict';
import { quarterOf, quarterKey } from '../../web/lib/quarter.js';

test('quarterOf maps months to calendar quarters', () => {
  assert.deepEqual(quarterOf('2026-01-15'), { year: 2026, quarter: 1 });
  assert.deepEqual(quarterOf('2026-03-31'), { year: 2026, quarter: 1 });
  assert.deepEqual(quarterOf('2026-04-01'), { year: 2026, quarter: 2 });
  assert.deepEqual(quarterOf('2026-07-06'), { year: 2026, quarter: 3 });
  assert.deepEqual(quarterOf('2026-12-31'), { year: 2026, quarter: 4 });
});

test('quarterKey formats year and quarter', () => {
  assert.equal(quarterKey('2026-07-06'), '2026-Q3');
  assert.equal(quarterKey('2025-11-02'), '2025-Q4');
});
