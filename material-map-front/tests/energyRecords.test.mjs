import test from 'node:test'
import assert from 'node:assert/strict'

import {
  buildWtiRecordsUrl,
  calculateBollinger,
  recordsToEnergyChart,
} from '../src/services/energyRecords.js'


test('converts EIA records to chronological WTI chart data', () => {
  const chart = recordsToEnergyChart([
    {
      source: 'eia',
      sub_category: 'crude_oil',
      metric_type: 'price',
      region: 'US-OK-CUSHING',
      period: '2026-07-02T00:00:00',
      value: 66.5,
      unit: 'USD/barrel',
    },
    {
      source: 'eia',
      sub_category: 'crude_oil',
      metric_type: 'price',
      region: 'US-OK-CUSHING',
      period: '2026-07-01T00:00:00',
      value: 65.12,
      unit: 'USD/barrel',
    },
  ], 2)

  assert.deepEqual(chart.dates, ['2026.07.01', '2026.07.02'])
  assert.deepEqual(chart.values, [65.12, 66.5])
  assert.equal(chart.unit, 'USD/barrel')
  assert.deepEqual(chart.ma, [65.12, 65.81])
})

test('does not mix Brent prices or crude inventories into the WTI chart', () => {
  const chart = recordsToEnergyChart([
    {
      source: 'eia',
      sub_category: 'crude_oil',
      metric_type: 'price',
      region: 'EUROPE',
      period: '2026-07-01T00:00:00',
      value: 68.2,
      unit: 'USD/barrel',
    },
    {
      source: 'eia',
      sub_category: 'crude_oil',
      metric_type: 'volume',
      region: 'US',
      period: '2026-07-01T00:00:00',
      value: 420000,
      unit: 'thousand_barrels',
    },
    {
      source: 'eia',
      sub_category: 'crude_oil',
      metric_type: 'price',
      region: 'US-OK-CUSHING',
      period: '2026-07-01T00:00:00',
      value: 65.12,
      unit: 'USD/barrel',
    },
  ])

  assert.deepEqual(chart.values, [65.12])
})

test('rejects empty or non-EIA data instead of presenting it as real', () => {
  assert.throws(() => recordsToEnergyChart([]), /没有可展示/)
  assert.throws(
    () => recordsToEnergyChart([{ source: 'mock', value: 1, period: '2026-01-01' }]),
    /没有可展示/,
  )
})

test('builds the precise poc4 query used by the WTI panel', () => {
  const url = new URL(buildWtiRecordsUrl({
    apiBaseUrl: 'http://127.0.0.1:8000',
    periodFrom: '2026-01-01',
  }))

  assert.equal(url.pathname, '/api/records')
  assert.equal(url.searchParams.get('category'), 'energy')
  assert.equal(url.searchParams.get('sub_category'), 'crude_oil')
  assert.equal(url.searchParams.get('source'), 'eia')
  assert.equal(url.searchParams.get('period_from'), '2026-01-01')
})

test('validates the rolling window', () => {
  assert.throws(() => calculateBollinger([1, 2], 0), /正整数/)
})
