// 大宗商品联动网络 Mock 数据
export const commodityNodes = [
  // 能源类
  { name: '原油', category: 0, symbolSize: 60, value: 82.5 },
  { name: '天然气', category: 0, symbolSize: 48, value: 65.3 },
  { name: '煤炭', category: 0, symbolSize: 42, value: 58.1 },
  { name: '成品油', category: 0, symbolSize: 35, value: 44.7 },
  // 金属类
  { name: '铁矿石', category: 1, symbolSize: 52, value: 71.2 },
  { name: '铜', category: 1, symbolSize: 44, value: 60.8 },
  { name: '铝', category: 1, symbolSize: 36, value: 49.3 },
  { name: '镍', category: 1, symbolSize: 28, value: 35.6 },
  { name: '锂', category: 1, symbolSize: 30, value: 42.1 },
  { name: '稀土', category: 1, symbolSize: 25, value: 33.8 },
  // 农产品类
  { name: '大豆', category: 2, symbolSize: 46, value: 63.5 },
  { name: '玉米', category: 2, symbolSize: 40, value: 55.2 },
  { name: '小麦', category: 2, symbolSize: 34, value: 47.8 },
  { name: '棕榈油', category: 2, symbolSize: 28, value: 38.4 },
  { name: '天然橡胶', category: 2, symbolSize: 26, value: 34.9 },
  // 化工类
  { name: '乙烯', category: 3, symbolSize: 22, value: 29.3 },
  { name: 'PX', category: 3, symbolSize: 20, value: 26.7 },
  { name: '甲醇', category: 3, symbolSize: 18, value: 23.1 },
]

export const commodityLinks = [
  // 原油关联
  { source: '原油', target: '成品油', value: 0.85 },
  { source: '原油', target: '乙烯', value: 0.62 },
  { source: '原油', target: 'PX', value: 0.55 },
  { source: '原油', target: '天然气', value: 0.48 },
  // 天然气关联
  { source: '天然气', target: '甲醇', value: 0.71 },
  { source: '天然气', target: '乙烯', value: 0.38 },
  { source: '天然气', target: '煤炭', value: 0.35 },
  // 煤炭关联
  { source: '煤炭', target: '铁矿石', value: 0.52 },
  { source: '煤炭', target: '铝', value: 0.44 },
  { source: '煤炭', target: '甲醇', value: 0.41 },
  // 铁矿石关联
  { source: '铁矿石', target: '铜', value: 0.38 },
  { source: '铁矿石', target: '镍', value: 0.33 },
  // 铜镍关联
  { source: '铜', target: '铝', value: 0.58 },
  { source: '铜', target: '镍', value: 0.45 },
  { source: '镍', target: '锂', value: 0.52 },
  { source: '锂', target: '稀土', value: 0.35 },
  // 农产品关联
  { source: '大豆', target: '玉米', value: 0.65 },
  { source: '大豆', target: '棕榈油', value: 0.42 },
  { source: '玉米', target: '小麦', value: 0.72 },
  { source: '小麦', target: '天然橡胶', value: 0.25 },
  { source: '棕榈油', target: '天然橡胶', value: 0.38 },
  // 跨类关联
  { source: '原油', target: '大豆', value: 0.22 },
  { source: '铜', target: '锂', value: 0.42 },
  { source: '煤炭', target: '小麦', value: 0.18 },
]

export const commodityCategories = [
  { name: '能源', itemStyle: { color: '#ff6e40' } },
  { name: '金属', itemStyle: { color: '#40c4ff' } },
  { name: '农产品', itemStyle: { color: '#69f0ae' } },
  { name: '化工', itemStyle: { color: '#e040fb' } },
]
