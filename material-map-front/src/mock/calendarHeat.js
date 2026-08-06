// 风险异常日历热力图 Mock 数据 — 最近一年每日风险指数
function generateYearData() {
  const now = new Date()
  const year = now.getFullYear()
  const data = []
  const baseRisk = 35

  for (let m = 1; m <= 12; m++) {
    const daysInMonth = new Date(year, m, 0).getDate()
    for (let d = 1; d <= daysInMonth; d++) {
      const dateStr = `${year}-${String(m).padStart(2, '0')}-${String(d).padStart(2, '0')}`
      // 模拟季节性和随机波动
      const seasonal = 15 * Math.sin((m - 1) / 12 * Math.PI * 2)
      let special = 0
      // 模拟一些异常事件
      const md = m * 100 + d
      if ([115, 308, 422, 515, 620, 718, 805, 912, 1008, 1122].includes(md)) {
        special = 30 + Math.random() * 20
      }
      const noise = (Math.random() - 0.5) * 20
      const risk = Math.round(Math.max(5, Math.min(95, baseRisk + seasonal + noise + special)))
      data.push([dateStr, risk])
    }
  }
  return data
}

export const calendarData = generateYearData()

// 环比异常月份汇总
export const monthAbnormal = [
  { month: '2026-01', avg: 42, abnormal: 3, top1: '原油价格剧烈波动', top2: '铁矿库存预警' },
  { month: '2026-02', avg: 38, abnormal: 2, top1: '天然气供应紧张', top2: '大豆到港延迟' },
  { month: '2026-03', avg: 55, abnormal: 5, top1: '铜价突破阻力位', top2: '煤炭港口积压' },
  { month: '2026-04', avg: 48, abnormal: 4, top1: '稀土出口管制', top2: '铝库存低位' },
  { month: '2026-05', avg: 52, abnormal: 4, top1: '原油供应中断', top2: '棕榈油期货涨停' },
  { month: '2026-06', avg: 35, abnormal: 1, top1: '锂价触底反弹', top2: null },
]
