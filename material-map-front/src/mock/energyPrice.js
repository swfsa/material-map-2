/**
 * 能源价格布林带数据
 * 模拟 2024.01-2025.06 月度数据 (18 个月)
 */
const months = []
for (let i = 0; i < 18; i++) {
  const y = 2024 + Math.floor(i / 12)
  const m = String((i % 12) + 1).padStart(2, '0')
  months.push(`${y}.${m}`)
}

// 布林带计算: 中轨(MA20), 上轨(MA+2σ), 下轨(MA-2σ)
function bollinger(base, noise, period = 5) {
  const raw = months.map((_, i) => base + Math.sin(i * 0.6) * noise + (Math.random() - 0.5) * noise * 0.5)
  const ma = []
  const upper = []
  const lower = []
  for (let i = 0; i < raw.length; i++) {
    const start = Math.max(0, i - period + 1)
    const slice = raw.slice(start, i + 1)
    const avg = slice.reduce((a, b) => a + b, 0) / slice.length
    const std = Math.sqrt(slice.reduce((s, v) => s + (v - avg) ** 2, 0) / slice.length)
    ma.push(+avg.toFixed(2))
    upper.push(+(avg + 2 * std).toFixed(2))
    lower.push(+(avg - 2 * std).toFixed(2))
  }
  return { dates: months, values: raw.map(v => +v.toFixed(2)), ma, upper, lower }
}

export const crudeOil = {
  name: '原油 (WTI)',
  unit: '美元/桶',
  ...bollinger(75, 12),
}

export const naturalGas = {
  name: '天然气 (HH)',
  unit: '美元/百万英热',
  ...bollinger(3.5, 1.2),
}

export const coal = {
  name: '动力煤 (秦皇岛)',
  unit: '元/吨',
  ...bollinger(850, 80),
}
