const DEFAULT_WINDOW = 5

function round(value) {
  return Number(value.toFixed(2))
}

export function calculateBollinger(values, period = DEFAULT_WINDOW) {
  if (!Number.isInteger(period) || period < 1) {
    throw new Error('布林带周期必须是正整数')
  }

  const ma = []
  const upper = []
  const lower = []
  values.forEach((value, index) => {
    const start = Math.max(0, index - period + 1)
    const window = values.slice(start, index + 1)
    const average = window.reduce((sum, item) => sum + item, 0) / window.length
    const variance = window.reduce((sum, item) => sum + (item - average) ** 2, 0) / window.length
    const standardDeviation = Math.sqrt(variance)
    ma.push(round(average))
    upper.push(round(average + 2 * standardDeviation))
    lower.push(round(average - 2 * standardDeviation))
  })
  return { ma, upper, lower }
}

export function recordsToEnergyChart(records, period = DEFAULT_WINDOW) {
  if (!Array.isArray(records)) {
    throw new Error('EIA API 返回值必须是数组')
  }

  const usable = records
    .filter((record) => (
      record?.source === 'eia'
      && record?.sub_category === 'crude_oil'
      && record?.metric_type === 'price'
      && record?.region === 'US-OK-CUSHING'
      && Number.isFinite(Number(record?.value))
      && typeof record?.period === 'string'
    ))
    .sort((left, right) => left.period.localeCompare(right.period))

  if (usable.length === 0) {
    throw new Error('没有可展示的 EIA WTI 数据')
  }

  const unit = usable[0].unit
  const sameUnit = usable.filter((record) => record.unit === unit)
  const values = sameUnit.map((record) => Number(record.value))
  return {
    name: '原油 (WTI)',
    unit,
    dates: sameUnit.map((record) => record.period.slice(0, 10).replaceAll('-', '.')),
    values,
    ...calculateBollinger(values, period),
  }
}

function oneYearAgo() {
  const value = new Date()
  value.setUTCFullYear(value.getUTCFullYear() - 1)
  return value.toISOString().slice(0, 10)
}

export function buildWtiRecordsUrl({ apiBaseUrl = '', periodFrom = oneYearAgo() } = {}) {
  const params = new URLSearchParams({
    category: 'energy',
    sub_category: 'crude_oil',
    source: 'eia',
    period_from: periodFrom,
  })
  return `${apiBaseUrl}/api/records?${params.toString()}`
}

export async function fetchWtiEnergyChart({
  fetchImpl = fetch,
  apiBaseUrl = import.meta.env?.VITE_API_BASE_URL ?? '',
  periodFrom = import.meta.env?.VITE_EIA_PERIOD_FROM || oneYearAgo(),
} = {}) {
  const response = await fetchImpl(buildWtiRecordsUrl({ apiBaseUrl, periodFrom }))
  if (!response.ok) {
    throw new Error(`EIA API 请求失败（HTTP ${response.status}）`)
  }
  return recordsToEnergyChart(await response.json())
}
