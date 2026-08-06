/**
 * 农产品双轴对比数据
 * 左轴: 价格(元/吨), 右轴: 产量(万吨)
 */
const months = []
for (let i = 0; i < 12; i++) {
  months.push(`2025.${String(i + 1).padStart(2, '0')}`)
}

function gen(base, amp, length = 12) {
  return Array.from({ length }, (_, i) => +(base + Math.sin(i * 0.8) * amp + (Math.random() - 0.5) * amp * 0.3).toFixed(1))
}

export const soybean = {
  name: '大豆',
  price: gen(5200, 400),
  yield: gen(1800, 200),
}

export const corn = {
  name: '玉米',
  price: gen(2700, 200),
  yield: gen(2800, 300),
}

export const wheat = {
  name: '小麦',
  price: gen(3100, 150),
  yield: gen(1350, 120),
}

export const months2025 = months
