/**
 * 综合仪表盘数据
 */
export const gaugeMetrics = [
  { name: '物资覆盖率', value: 87.5, min: 0, max: 100, unit: '%', color: '#00e676' },
  { name: '响应时效', value: 4.2, min: 0, max: 24, unit: 'h', color: '#ffab40', inverse: true },
  { name: '库存储备率', value: 72.3, min: 0, max: 100, unit: '%', color: '#448aff' },
  { name: '运输完成率', value: 94.1, min: 0, max: 100, unit: '%', color: '#00e5ff' },
]

export const statCards = [
  { label: '今日灾害事件', value: 23, trend: '+5', trendUp: true },
  { label: '活跃物资调拨', value: 147, trend: '+12', trendUp: true },
  { label: '在途运输批次', value: 89, trend: '-3', trendUp: false },
  { label: '覆盖省份', value: 31, trend: '—', trendUp: null },
  { label: '物资总量(吨)', value: '28,500', trend: '+2.1%', trendUp: true },
  { label: '预警信息', value: 7, trend: '+2', trendUp: true },
]

export const barData = {
  categories: ['帐篷', '食品', '饮用水', '医疗', '棉被', '发电机', '救生衣', '冲锋舟'],
  stock: [12500, 8900, 15600, 4200, 9800, 2100, 5600, 380],
  allocated: [8700, 6200, 10200, 2800, 5400, 1200, 3400, 200],
}
