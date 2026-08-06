<template>
  <div class="panel agri-panel">
    <div class="panel-title">农产品价格</div>
    <div ref="chartRef" class="chart-body"></div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import * as echarts from 'echarts'
import { soybean, corn, months2025 } from '../mock/agriculture.js'

const chartRef = ref(null)
let chart = null

function buildOption() {
  return {
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(6,12,36,0.85)',
      borderColor: 'rgba(0,180,255,0.4)',
      textStyle: { color: '#e0f0ff', fontSize: 13 },
    },
    legend: {
      data: ['大豆价格', '玉米价格', '大豆产量', '玉米产量'],
      bottom: 0,
      textStyle: { color: '#a0b8cc', fontSize: 11 },
      itemWidth: 14,
      itemHeight: 8,
    },
    grid: { top: 12, right: 68, bottom: 32, left: 52 },
    xAxis: {
      type: 'category',
      data: months2025,
      axisLine: { lineStyle: { color: 'rgba(255,255,255,0.15)' } },
      axisLabel: { color: '#90a4ae', fontSize: 10 },
    },
    yAxis: [
      {
        type: 'value',
        name: '价格 (元/吨)',
        nameTextStyle: { color: '#ffab40', fontSize: 10 },
        splitLine: { lineStyle: { color: 'rgba(255,255,255,0.06)' } },
        axisLabel: { color: '#ffab40', fontSize: 10 },
      },
      {
        type: 'value',
        name: '产量 (万吨)',
        nameTextStyle: { color: '#00e5ff', fontSize: 10 },
        splitLine: { show: false },
        axisLabel: { color: '#00e5ff', fontSize: 10 },
      },
    ],
    series: [
      {
        name: '大豆价格',
        type: 'bar',
        data: soybean.price,
        barWidth: 8,
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: '#ff8a65' },
            { offset: 1, color: 'rgba(255,138,101,0.2)' },
          ]),
          borderRadius: [3, 3, 0, 0],
        },
      },
      {
        name: '玉米价格',
        type: 'bar',
        data: corn.price,
        barWidth: 8,
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: '#ffd54f' },
            { offset: 1, color: 'rgba(255,213,79,0.2)' },
          ]),
          borderRadius: [3, 3, 0, 0],
        },
      },
      {
        name: '大豆产量',
        type: 'line',
        yAxisIndex: 1,
        data: soybean.yield,
        smooth: true,
        symbol: 'circle',
        symbolSize: 5,
        lineStyle: { color: '#00e5ff', width: 2 },
        itemStyle: { color: '#00e5ff' },
      },
      {
        name: '玉米产量',
        type: 'line',
        yAxisIndex: 1,
        data: corn.yield,
        smooth: true,
        symbol: 'diamond',
        symbolSize: 5,
        lineStyle: { color: '#69f0ae', width: 2 },
        itemStyle: { color: '#69f0ae' },
      },
    ],
  }
}

onMounted(() => {
  chart = echarts.init(chartRef.value)
  chart.setOption(buildOption())
  window.addEventListener('resize', () => chart?.resize())
})

onUnmounted(() => {
  chart?.dispose()
})
</script>

<style scoped>
.agri-panel { grid-area: agri; width: 100%; height: 100%; display: flex; flex-direction: column; }
.chart-body { width: 100%; flex: 1; min-height: 0; }
</style>
