<template>
  <div class="panel calendar-panel">
    <div class="panel-title">风险异常监测 — 日历热力图</div>
    <div ref="chartRef" class="chart-body"></div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import * as echarts from 'echarts'
import { calendarData } from '../mock/calendarHeat.js'

const chartRef = ref(null)
let chart = null

function buildOption() {
  const now = new Date()
  const year = now.getFullYear()

  return {
    tooltip: {
      backgroundColor: 'rgba(6,12,36,0.85)',
      borderColor: 'rgba(0,180,255,0.4)',
      textStyle: { color: '#e0f0ff', fontSize: 12 },
      formatter: (p) => {
        return `<span style="color:#78909c">${p.data[0]}</span><br/>风险指数: <span style="color:#ff5252;font-weight:700">${p.data[1]}</span>`
      },
    },
    visualMap: {
      min: 0,
      max: 100,
      type: 'piecewise',
      orient: 'horizontal',
      left: 'center',
      bottom: 0,
      textStyle: { color: '#90a4ae', fontSize: 11 },
      pieces: [
        { min: 80, color: '#ff1744', label: '极高 (>80)' },
        { min: 60, max: 79, color: '#ff5252', label: '高 (60-79)' },
        { min: 40, max: 59, color: '#ffab40', label: '中 (40-59)' },
        { min: 20, max: 39, color: '#448aff', label: '低 (20-39)' },
        { max: 19, color: '#69f0ae', label: '安全 (<20)' },
      ],
    },
    calendar: {
      top: 20,
      left: 30,
      right: 30,
      range: String(year),
      cellSize: ['auto', 15],
      yearLabel: { show: true, color: '#00e5ff', fontSize: 15 },
      dayLabel: { color: '#90a4ae', fontSize: 11, nameMap: 'cn' },
      monthLabel: { color: '#90a4ae', fontSize: 11, nameMap: 'cn' },
      splitLine: {
        lineStyle: { color: 'rgba(0,180,255,0.1)', width: 1 },
      },
      itemStyle: {
        borderColor: 'rgba(6,12,36,0.9)',
        borderWidth: 2,
        borderRadius: 2,
      },
    },
    series: [{
      type: 'heatmap',
      coordinateSystem: 'calendar',
      data: calendarData,
      emphasis: {
        itemStyle: {
          shadowBlur: 10,
          shadowColor: 'rgba(0,229,255,0.6)',
          borderColor: '#fff',
          borderWidth: 1.5,
        },
      },
    }],
  }
}

onMounted(() => {
  chart = echarts.init(chartRef.value)
  chart.setOption(buildOption())
  window.addEventListener('resize', () => chart?.resize())
})

onUnmounted(() => {
  chart?.dispose()
  chart = null
})
</script>

<style scoped>
.calendar-panel { width: 100%; height: 100%; display: flex; flex-direction: column; }
.chart-body { width: 100%; flex: 1; min-height: 0; }
</style>
