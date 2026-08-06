<template>
  <div class="panel dash-panel">
    <div class="panel-title">综合仪表盘</div>
    <div class="dash-grid">
      <!-- 指标卡片 -->
      <div class="stat-cards">
        <div v-for="(card, idx) in statCards" :key="card.label" class="stat-card">
          <div class="stat-label">{{ card.label }}</div>
          <div class="stat-value">{{ animatedValues[idx] }}</div>
          <div
            class="stat-trend"
            :class="{
              'trend-up': card.trendUp === true,
              'trend-down': card.trendUp === false,
            }"
          >
            {{ card.trend }}
          </div>
        </div>
      </div>
      <!-- 仪表盘 -->
      <div class="gauges">
        <div v-for="g in gaugeMetrics" :key="g.name" ref="gaugeRefs" class="gauge-item"></div>
      </div>
      <!-- 物资柱状图 -->
      <div ref="barRef" class="bar-chart"></div>
      <!-- 日历热力图 -->
      <div ref="calendarRef" class="dash-calendar"></div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import * as echarts from 'echarts'
import { gaugeMetrics, statCards, barData } from '../mock/dashboard.js'
import { calendarData } from '../mock/calendarHeat.js'

const gaugeRefs = ref([])
const barRef = ref(null)
const calendarRef = ref(null)
let gaugeCharts = []
let barChart = null
let calendarChart = null

// Count-up animation
const animatedValues = ref(statCards.map(() => '0'))

function parseNum(str) {
  return parseFloat(String(str).replace(/,/g, '')) || 0
}

function formatNum(num, template) {
  if (String(template).includes(',')) {
    return num.toLocaleString('en-US')
  }
  return String(Math.round(num))
}

let countUpAnimIds = []

function startCountUp() {
  countUpAnimIds.forEach(id => cancelAnimationFrame(id))
  countUpAnimIds = []

  statCards.forEach((card, idx) => {
    const target = parseNum(card.value)
    const start = performance.now()
    const duration = 1200

    function easeOutCubic(t) {
      return 1 - Math.pow(1 - t, 3)
    }

    function tick(now) {
      const elapsed = now - start
      const progress = Math.min(elapsed / duration, 1)
      const current = Math.round(target * easeOutCubic(progress))
      animatedValues.value[idx] = formatNum(current, card.value)
      if (progress < 1) {
        countUpAnimIds.push(requestAnimationFrame(tick))
      }
    }

    countUpAnimIds.push(requestAnimationFrame(tick))
  })
}

function buildGaugeOption(metric) {
  const val = metric.inverse ? metric.max - metric.value : metric.value
  return {
    series: [
      {
        type: 'gauge',
        startAngle: 210,
        endAngle: -30,
        min: metric.min,
        max: metric.max,
        center: ['50%', '50%'],
        radius: '65%',
        axisLine: {
          lineStyle: {
            width: 6,
            color: [
              [0.3, '#ff5252'],
              [0.7, '#ffab40'],
              [1, '#00e676'],
            ],
          },
        },
        pointer: {
          length: '55%',
          width: 3,
          itemStyle: { color: metric.color },
        },
        axisTick: { show: false },
        splitLine: { show: false },
        axisLabel: {
          color: '#a0b8cc',
          fontSize: 10,
          fontWeight: 'bold',
          distance: 16,
          formatter: (v) => (metric.inverse ? metric.max - v : v),
        },
        detail: {
          valueAnimation: true,
          formatter: '{value}' + metric.unit,
          color: '#e0f0ff',
          fontSize: 14,
          fontWeight: 'bold',
          offsetCenter: [0, '70%'],
        },
        title: {
          color: '#a0b8cc',
          fontSize: 11,
          fontWeight: 'bold',
          offsetCenter: [0, '115%'],
        },
        data: [{ value: val, name: metric.name }],
      },
    ],
  }
}

function buildBarOption() {
  return {
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(6,12,36,0.85)',
      borderColor: 'rgba(0,180,255,0.4)',
      textStyle: { color: '#e0f0ff', fontSize: 11 },
    },
    legend: {
      data: ['库存', '已调拨'],
      bottom: 0,
      textStyle: { color: '#a0b8cc', fontSize: 10 },
      itemWidth: 12,
      itemHeight: 7,
    },
    grid: { top: 8, right: 16, bottom: 28, left: 40 },
    xAxis: {
      type: 'category',
      data: barData.categories,
      axisLabel: { color: '#a0b8cc', fontSize: 10, rotate: 30, fontWeight: 'bold' },
      axisLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } },
    },
    yAxis: {
      type: 'value',
      name: '吨',
      nameTextStyle: { color: '#a0b8cc', fontSize: 10, fontWeight: 'bold' },
      splitLine: { lineStyle: { color: 'rgba(255,255,255,0.05)' } },
      axisLabel: { color: '#a0b8cc', fontSize: 10, fontWeight: 'bold' },
    },
    series: [
      {
        name: '库存',
        type: 'bar',
        data: barData.stock,
        barWidth: 10,
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: '#448aff' },
            { offset: 1, color: 'rgba(68,138,255,0.2)' },
          ]),
          borderRadius: [2, 2, 0, 0],
        },
      },
      {
        name: '已调拨',
        type: 'bar',
        data: barData.allocated,
        barWidth: 10,
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: '#ffab40' },
            { offset: 1, color: 'rgba(255,171,64,0.2)' },
          ]),
          borderRadius: [2, 2, 0, 0],
        },
      },
    ],
  }
}

function buildCalendarOption() {
  const year = new Date().getFullYear()
  return {
    tooltip: {
      backgroundColor: 'rgba(6,12,36,0.85)',
      borderColor: 'rgba(0,180,255,0.4)',
      textStyle: { color: '#e0f0ff', fontSize: 11 },
      formatter: (p) => `${p.data[0]}<br/>风险: <span style="color:#ff5252;font-weight:700">${p.data[1]}</span>`,
    },
    visualMap: {
      min: 0,
      max: 100,
      type: 'piecewise',
      orient: 'horizontal',
      left: 'center',
      bottom: 0,
      textStyle: { color: '#90a4ae', fontSize: 9 },
      itemWidth: 10,
      itemHeight: 6,
      pieces: [
        { min: 80, color: '#ff1744', label: '极高' },
        { min: 60, max: 79, color: '#ff5252', label: '高' },
        { min: 40, max: 59, color: '#ffab40', label: '中' },
        { min: 20, max: 39, color: '#448aff', label: '低' },
        { max: 19, color: '#69f0ae', label: '安全' },
      ],
    },
    calendar: {
      top: 10,
      left: 20,
      right: 20,
      bottom: 40,
      range: String(year),
      cellSize: ['auto', 10],
      yearLabel: { show: false },
      dayLabel: { color: '#90a4ae', fontSize: 9, nameMap: 'cn' },
      monthLabel: { color: '#90a4ae', fontSize: 10, nameMap: 'cn' },
      splitLine: { lineStyle: { color: 'rgba(0,180,255,0.08)', width: 1 } },
      itemStyle: {
        borderColor: 'rgba(6,12,36,0.6)',
        borderWidth: 1.5,
        borderRadius: 1.5,
      },
    },
    series: [{
      type: 'heatmap',
      coordinateSystem: 'calendar',
      data: calendarData,
      emphasis: {
        itemStyle: {
          shadowBlur: 8,
          shadowColor: 'rgba(0,229,255,0.5)',
          borderColor: '#fff',
          borderWidth: 1,
        },
      },
    }],
  }
}

onMounted(() => {
  startCountUp()

  // Render gauge charts (Vue 3 ref array from v-for)
  gaugeRefs.value.forEach((el, i) => {
    const c = echarts.init(el)
    c.setOption(buildGaugeOption(gaugeMetrics[i]))
    gaugeCharts.push(c)
  })

  // Render bar chart
  barChart = echarts.init(barRef.value)
  barChart.setOption(buildBarOption())

  // Render calendar heatmap
  calendarChart = echarts.init(calendarRef.value)
  calendarChart.setOption(buildCalendarOption())

  window.addEventListener('resize', handleResize)
})

function handleResize() {
  gaugeCharts.forEach((c) => c.resize())
  barChart?.resize()
  calendarChart?.resize()
}

onUnmounted(() => {
  countUpAnimIds.forEach(id => cancelAnimationFrame(id))
  window.removeEventListener('resize', handleResize)
  gaugeCharts.forEach((c) => c.dispose())
  barChart?.dispose()
  calendarChart?.dispose()
})
</script>

<style scoped>
.dash-panel { grid-area: dash; width: 100%; height: 100%; display: flex; flex-direction: column; }
.dash-grid {
  flex: 1;
  display: grid;
  grid-template-columns: 1fr 1fr;
  grid-template-rows: auto 1fr auto;
  gap: 4px;
  padding: 4px 8px 6px;
  overflow: hidden;
}
.stat-cards {
  grid-column: 1 / -1;
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 6px;
}
.stat-card {
  background: rgba(0,180,255,0.05);
  border: 1px solid rgba(0,180,255,0.1);
  border-radius: 3px;
  padding: 6px 10px;
  transition: all 0.25s ease;
  cursor: default;
}
.stat-card:hover {
  border-color: rgba(0,180,255,0.3);
  background: rgba(0,180,255,0.1);
  box-shadow: 0 0 12px rgba(0,180,255,0.08);
  transform: translateY(-1px);
}
.stat-label { font-size: 11px; color: #90a4ae; letter-spacing: 1px; margin-bottom: 2px; }
.stat-value { font-size: 22px; font-weight: 700; color: #e0f0ff; line-height: 1.2; }
.stat-trend { font-size: 11px; margin-top: 1px; }
.trend-up { color: #ff5252; }
.trend-down { color: #00e676; }
.gauges {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 4px;
}
.gauge-item { width: 100%; height: 100%; min-height: 100px; }
.bar-chart { width: 100%; height: 100%; min-height: 100px; }
.dash-calendar { grid-column: 1 / -1; width: 100%; height: 120px; min-height: 100px; }
</style>
