import test from 'node:test'
import assert from 'node:assert/strict'

import {
  ReportApiError,
  ReportContractError,
  buildLatestReportUrl,
  fetchLatestReport,
  normalizeLatestReport,
} from '../src/services/latestReport.js'

const validPayload = {
  report_ir: {
    blocks: [
      { type: 'heading', data: { text: 'EIA 能源简报', level: 1 } },
      {
        type: 'kpiGrid',
        data: {
          title: null,
          items: [{
            label: 'WTI 原油现货价',
            value: 80.77,
            unit: 'USD/barrel',
            change: 4.2,
            change_period: '30d',
            trend: 'up',
            status: 'watch',
            as_of: '2026-08-01T00:00:00Z',
            source_record_ids: ['record-1'],
          }],
        },
      },
      {
        type: 'table',
        data: {
          title: '指标统计',
          columns: [{ key: 'indicator', label: '指标', unit: null }],
          rows: [{ indicator: 'WTI' }],
        },
      },
    ],
  },
  html: '<article>fallback</article>',
  generated_at: '2026-08-06T08:30:00Z',
}

test('normalizes the latest report block response', () => {
  const result = normalizeLatestReport(validPayload)

  assert.equal(result.reportIr.blocks.length, 3)
  assert.equal(result.reportIr.blocks[1].data.items[0].status, 'watch')
  assert.equal(result.generatedAt, '2026-08-06T08:30:00Z')
})

test('rejects unsupported blocks and undeclared table cells', () => {
  assert.throws(
    () => normalizeLatestReport({
      ...validPayload,
      report_ir: { blocks: [{ type: 'chart', data: {} }] },
    }),
    ReportContractError,
  )
  assert.throws(
    () => normalizeLatestReport({
      ...validPayload,
      report_ir: {
        blocks: [{
          type: 'table',
          data: {
            columns: [{ key: 'name', label: '名称', unit: null }],
            rows: [{ name: 'WTI', hidden: 'not declared' }],
          },
        }],
      },
    }),
    /未声明列/,
  )
})

test('builds the unified latest report endpoint without a double slash', () => {
  assert.equal(buildLatestReportUrl(), '/api/reports/latest')
  assert.equal(
    buildLatestReportUrl({ apiBaseUrl: 'http://127.0.0.1:8000/' }),
    'http://127.0.0.1:8000/api/reports/latest',
  )
})

test('fetches and validates a successful report', async () => {
  const report = await fetchLatestReport({
    apiBaseUrl: 'http://api.test',
    fetchImpl: async (url, options) => {
      assert.equal(url, 'http://api.test/api/reports/latest')
      assert.equal(options.headers.Accept, 'application/json')
      return { ok: true, status: 200, json: async () => validPayload }
    },
  })

  assert.equal(report.reportIr.blocks[0].data.text, 'EIA 能源简报')
})

test('classifies a missing report separately from other HTTP failures', async () => {
  await assert.rejects(
    fetchLatestReport({
      fetchImpl: async () => ({ ok: false, status: 404 }),
    }),
    (error) => (
      error instanceof ReportApiError
      && error.code === 'not_found'
      && error.status === 404
    ),
  )
})
