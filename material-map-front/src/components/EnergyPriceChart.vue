<template>
  <div class="panel energy-panel">
    <div class="panel-title">
      能源价格趋势
      <span class="data-badge" :class="dataMode">{{ dataModeLabel }}</span>
    </div>
    <div v-if="errorMessage" class="chart-state error-state">{{ errorMessage }}</div>
    <div v-else ref="chartRef" class="chart-body"></div>
  </div>
</template>

<script setup>
import { computed, ref, onMounted, onUnmounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import { fetchWtiEnergyChart } from '../services/energyRecords.js'

const chartRef = ref(null)
const dataMode = ref('loading')
const errorMessage = ref('')
let chart = null
const useMock = import.meta.env.VITE_USE_MOCK_ENERGY === 'true'

const dataModeLabel = computed(() => ({
  loading: '加载中',
  real: '真实 EIA',
  mock: 'Mock',
  error: '接口失败',
})[dataMode.value])

function buildOption(data) {
  return {
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(6,12,36,0.85)',
      borderColor: 'rgba(0,180,255,0.4)',
      textStyle: { color: '#e0f0ff', fontSize: 13 },
    },
    legend: {
      data: ['价格', '中轨(MA)', '上轨', '下轨'],
      bottom: 0,
      textStyle: { color: '#a0b8cc', fontSize: 11 },
      itemWidth: 14,
      itemHeight: 8,
    },
    grid: { top: 12, right: 20, bottom: 32, left: 48 },
    xAxis: {
      type: 'category',
      data: data.dates,
      axisLine: { lineStyle: { color: 'rgba(255,255,255,0.15)' } },
      axisLabel: { color: '#90a4ae', fontSize: 10, rotate: 30 },
      boundaryGap: false,
    },
    yAxis: {
      type: 'value',
      name: data.unit,
      nameTextStyle: { color: '#90a4ae', fontSize: 10 },
      splitLine: { lineStyle: { color: 'rgba(255,255,255,0.06)' } },
      axisLabel: { color: '#90a4ae', fontSize: 10 },
    },
    series: [
      {
        name: '价格',
        type: 'line',
        data: data.values,
        smooth: true,
        symbol: 'circle',
        symbolSize: 4,
        lineStyle: { color: '#00e5ff', width: 2 },
        itemStyle: { color: '#00e5ff' },
      },
      {
        name: '上轨',
        type: 'line',
        data: data.upper,
        lineStyle: { color: '#ff5252', width: 1, type: 'dashed' },
        symbol: 'none',
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(255,82,82,0.15)' },
            { offset: 1, color: 'rgba(255,82,82,0)' },
          ]),
        },
      },
      {
        name: '中轨(MA)',
        type: 'line',
        data: data.ma,
        lineStyle: { color: '#ffab40', width: 1.5 },
        symbol: 'none',
      },
      {
        name: '下轨',
        type: 'line',
        data: data.lower,
        lineStyle: { color: '#00e676', width: 1, type: 'dashed' },
        symbol: 'none',
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(0,230,118,0)' },
            { offset: 1, color: 'rgba(0,230,118,0.1)' },
          ]),
        },
      },
    ],
  }
}

function resizeChart() {
  chart?.resize()
}

onMounted(async () => {
  try {
    const data = useMock
      ? (await import('../mock/energyPrice.js')).crudeOil
      : await fetchWtiEnergyChart()
    dataMode.value = useMock ? 'mock' : 'real'
    await nextTick()
    chart = echarts.init(chartRef.value)
    chart.setOption(buildOption(data))
    window.addEventListener('resize', resizeChart)
  } catch (error) {
    dataMode.value = 'error'
    errorMessage.value = error instanceof Error ? error.message : 'EIA 数据加载失败'
  }
})

onUnmounted(() => {
  window.removeEventListener('resize', resizeChart)
  chart?.dispose()
})
</script>

<style scoped>
.energy-panel { grid-area: energy; width: 100%; height: 100%; display: flex; flex-direction: column; }
.chart-body { width: 100%; flex: 1; min-height: 0; }
.data-badge { margin-left: 8px; padding: 1px 5px; border-radius: 3px; font-size: 9px; letter-spacing: 0; }
.data-badge.real { color: #00e676; border: 1px solid rgba(0, 230, 118, 0.4); }
.data-badge.mock { color: #ffab40; border: 1px solid rgba(255, 171, 64, 0.4); }
.data-badge.loading { color: #90a4ae; border: 1px solid rgba(144, 164, 174, 0.3); }
.data-badge.error { color: #ff5252; border: 1px solid rgba(255, 82, 82, 0.4); }
.chart-state { flex: 1; display: flex; align-items: center; justify-content: center; padding: 16px; font-size: 12px; text-align: center; }
.error-state { color: #ff8a80; }
</style>
