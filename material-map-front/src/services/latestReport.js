const REPORT_BLOCK_TYPES = new Set([
  'heading',
  'paragraph',
  'kpiGrid',
  'callout',
  'table',
])

const TREND_VALUES = new Set(['up', 'down', 'flat', 'unknown'])
const STATUS_VALUES = new Set(['normal', 'watch', 'warning', 'critical'])
const SEVERITY_VALUES = new Set(['info', 'watch', 'warning', 'critical'])

export class ReportApiError extends Error {
  constructor(message, { status = null, code = 'api_error' } = {}) {
    super(message)
    this.name = 'ReportApiError'
    this.status = status
    this.code = code
  }
}

export class ReportContractError extends Error {
  constructor(message) {
    super(message)
    this.name = 'ReportContractError'
  }
}

function isObject(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
}

function requireObject(value, path) {
  if (!isObject(value)) {
    throw new ReportContractError(`${path} 必须是对象`)
  }
  return value
}

function requireString(value, path, { allowEmpty = false } = {}) {
  if (typeof value !== 'string' || (!allowEmpty && value.trim().length === 0)) {
    throw new ReportContractError(`${path} 必须是非空字符串`)
  }
}

function requireStringArray(value, path) {
  if (!Array.isArray(value) || value.some((item) => typeof item !== 'string')) {
    throw new ReportContractError(`${path} 必须是字符串数组`)
  }
}

function validateHeading(data, path) {
  requireString(data.text, `${path}.text`)
  if (![1, 2, 3].includes(data.level)) {
    throw new ReportContractError(`${path}.level 必须是 1、2 或 3`)
  }
}

function validateParagraph(data, path) {
  requireString(data.text, `${path}.text`)
  requireStringArray(data.evidence_ids, `${path}.evidence_ids`)
}

function validateKpiGrid(data, path) {
  if (data.title !== null && data.title !== undefined) {
    requireString(data.title, `${path}.title`)
  }
  if (!Array.isArray(data.items) || data.items.length === 0) {
    throw new ReportContractError(`${path}.items 必须是非空数组`)
  }

  data.items.forEach((item, index) => {
    const itemPath = `${path}.items[${index}]`
    requireObject(item, itemPath)
    requireString(item.label, `${itemPath}.label`)
    if (typeof item.value !== 'string' && typeof item.value !== 'number') {
      throw new ReportContractError(`${itemPath}.value 必须是字符串或数字`)
    }
    if (!TREND_VALUES.has(item.trend)) {
      throw new ReportContractError(`${itemPath}.trend 无效`)
    }
    if (!STATUS_VALUES.has(item.status)) {
      throw new ReportContractError(`${itemPath}.status 无效`)
    }
    requireStringArray(item.source_record_ids, `${itemPath}.source_record_ids`)
  })
}

function validateCallout(data, path) {
  requireString(data.title, `${path}.title`)
  requireString(data.text, `${path}.text`)
  if (!SEVERITY_VALUES.has(data.severity)) {
    throw new ReportContractError(`${path}.severity 无效`)
  }
  requireStringArray(data.evidence_ids, `${path}.evidence_ids`)
}

function validateTable(data, path) {
  if (data.title !== null && data.title !== undefined) {
    requireString(data.title, `${path}.title`)
  }
  if (!Array.isArray(data.columns) || data.columns.length === 0) {
    throw new ReportContractError(`${path}.columns 必须是非空数组`)
  }
  if (!Array.isArray(data.rows)) {
    throw new ReportContractError(`${path}.rows 必须是数组`)
  }

  const keys = new Set()
  data.columns.forEach((column, index) => {
    const columnPath = `${path}.columns[${index}]`
    requireObject(column, columnPath)
    requireString(column.key, `${columnPath}.key`)
    requireString(column.label, `${columnPath}.label`)
    if (keys.has(column.key)) {
      throw new ReportContractError(`${path}.columns 包含重复 key`)
    }
    keys.add(column.key)
  })
  data.rows.forEach((row, index) => {
    requireObject(row, `${path}.rows[${index}]`)
    const unknownKeys = Object.keys(row).filter((key) => !keys.has(key))
    if (unknownKeys.length > 0) {
      throw new ReportContractError(`${path}.rows[${index}] 包含未声明列`)
    }
  })
}

export function validateReportBlock(block, index = 0) {
  const path = `report_ir.blocks[${index}]`
  requireObject(block, path)
  if (!REPORT_BLOCK_TYPES.has(block.type)) {
    throw new ReportContractError(`${path}.type 无效`)
  }
  const data = requireObject(block.data, `${path}.data`)

  const validators = {
    heading: validateHeading,
    paragraph: validateParagraph,
    kpiGrid: validateKpiGrid,
    callout: validateCallout,
    table: validateTable,
  }
  validators[block.type](data, `${path}.data`)
  return block
}

export function normalizeLatestReport(payload) {
  const root = requireObject(payload, 'response')
  const reportIr = requireObject(root.report_ir, 'report_ir')
  if (!Array.isArray(reportIr.blocks) || reportIr.blocks.length === 0) {
    throw new ReportContractError('report_ir.blocks 必须是非空数组')
  }
  reportIr.blocks.forEach(validateReportBlock)
  requireString(root.html, 'html', { allowEmpty: true })
  requireString(root.generated_at, 'generated_at')
  if (Number.isNaN(Date.parse(root.generated_at))) {
    throw new ReportContractError('generated_at 必须是有效时间')
  }

  return {
    reportIr: { blocks: reportIr.blocks },
    html: root.html,
    generatedAt: root.generated_at,
  }
}

export function buildLatestReportUrl({ apiBaseUrl = '' } = {}) {
  return `${apiBaseUrl.replace(/\/$/, '')}/api/reports/latest`
}

export async function fetchLatestReport({
  fetchImpl = fetch,
  apiBaseUrl = import.meta.env?.VITE_API_BASE_URL ?? '',
  signal,
} = {}) {
  const response = await fetchImpl(buildLatestReportUrl({ apiBaseUrl }), {
    method: 'GET',
    headers: { Accept: 'application/json' },
    signal,
  })

  if (response.status === 404) {
    throw new ReportApiError('尚未生成能源市场简报', {
      status: 404,
      code: 'not_found',
    })
  }
  if (!response.ok) {
    throw new ReportApiError(`能源简报请求失败（HTTP ${response.status}）`, {
      status: response.status,
    })
  }

  let payload
  try {
    payload = await response.json()
  } catch {
    throw new ReportContractError('能源简报响应不是有效 JSON')
  }
  return normalizeLatestReport(payload)
}
