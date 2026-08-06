/**
 * GIS 灾害-物资打点数据
 * 模拟全国范围内的灾害事件及物资投放点
 */
export const disasterEvents = [
  { name: '四川甘孜地震', value: [101.96, 30.05, 6.8], type: '地震', level: '重大', time: '2025-03-15', materials: ['帐篷', '食品', '医疗'] },
  { name: '云南昭通滑坡', value: [103.72, 27.34, 5.2], type: '滑坡', level: '较大', time: '2025-04-02', materials: ['帐篷', '饮用水'] },
  { name: '湖南洞庭湖洪水', value: [112.95, 29.15, 7.5], type: '洪水', level: '重大', time: '2025-06-20', materials: ['救生衣', '食品', '医疗', '冲锋舟'] },
  { name: '广东湛江台风', value: [110.36, 21.27, 8.0], type: '台风', level: '特大', time: '2025-07-10', materials: ['帐篷', '食品', '发电机', '医疗'] },
  { name: '新疆喀什地震', value: [75.99, 39.47, 5.5], type: '地震', level: '较大', time: '2025-05-08', materials: ['帐篷', '棉被', '食品'] },
  { name: '甘肃陇南泥石流', value: [104.92, 33.40, 4.8], type: '泥石流', level: '一般', time: '2025-06-01', materials: ['帐篷', '饮用水'] },
  { name: '江西鄱阳湖洪水', value: [116.03, 29.25, 6.2], type: '洪水', level: '较大', time: '2025-06-25', materials: ['救生衣', '食品', '医疗'] },
  { name: '福建厦门台风', value: [118.08, 24.48, 7.8], type: '台风', level: '重大', time: '2025-07-12', materials: ['帐篷', '食品', '发电机'] },
]

// 物资投放点
export const supplyPoints = [
  { name: '成都储备库', value: [104.07, 30.67, 5000], category: '中央库', status: '充足' },
  { name: '武汉储备库', value: [114.30, 30.60, 3800], category: '中央库', status: '充足' },
  { name: '昆明储备库', value: [102.83, 24.88, 2200], category: '省级库', status: '正常' },
  { name: '广州储备库', value: [113.26, 23.13, 3000], category: '中央库', status: '充足' },
  { name: '兰州储备库', value: [103.83, 36.05, 1500], category: '省级库', status: '偏低' },
  { name: '郑州储备库', value: [113.65, 34.76, 2600], category: '省级库', status: '正常' },
  { name: '长沙储备库', value: [112.97, 28.23, 1800], category: '省级库', status: '正常' },
  { name: '乌鲁木齐储备库', value: [87.62, 43.82, 1200], category: '省级库', status: '偏低' },
]
