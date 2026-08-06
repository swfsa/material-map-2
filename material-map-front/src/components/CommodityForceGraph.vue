<template>
  <div class="panel commodity-panel">
    <div class="panel-title">大宗商品联动网络</div>
    <div ref="chartRef" class="chart-body"></div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import * as echarts from 'echarts'
import { commodityNodes, commodityLinks, commodityCategories } from '../mock/commodity.js'

const chartRef = ref(null)
let chart = null

function buildOption() {
  return {
    tooltip: {
      backgroundColor: 'rgba(6,12,36,0.85)',
      borderColor: 'rgba(0,180,255,0.4)',
      textStyle: { color: '#e0f0ff', fontSize: 12 },
      formatter: (p) => {
        if (p.dataType === 'edge') {
          return `${p.data.source} → ${p.data.target}<br/>关联系数: <span style="color:#00e5ff;font-weight:700">${(p.data.value * 100).toFixed(0)}%</span>`
        }
        return `<span style="font-weight:700;color:#00e5ff">${p.name}</span><br/>影响力指数: <span style="color:#ffab40">${p.value}</span>`
      },
    },
    legend: {
      data: commodityCategories.map(c => c.name),
      textStyle: { color: '#a0b8cc', fontSize: 11 },
      bottom: 0,
    },
    series: [{
      type: 'graph',
      layout: 'force',
      roam: true,
      draggable: true,
      categories: commodityCategories,
      nodes: commodityNodes.map(n => ({
        ...n,
        itemStyle: { shadowBlur: 12, shadowColor: 'rgba(0,0,0,0.5)' },
      })),
      edges: commodityLinks.map(l => ({
        ...l,
        lineStyle: {
          color: 'rgba(0,180,255,0.3)',
          curveness: 0.2,
        },
      })),
      force: {
        repulsion: 500,
        gravity: 0.08,
        edgeLength: [120, 220],
        layoutAnimation: true,
      },
      edgeSymbol: ['none', 'none'],
      edgeLabel: { show: false },
      label: {
        show: true,
        color: '#c0d0e0',
        fontSize: 11,
        position: 'right',
      },
      emphasis: {
        focus: 'adjacency',
        lineStyle: { color: '#00e5ff', width: 2 },
        itemStyle: { shadowBlur: 20, shadowColor: 'rgba(0,229,255,0.6)' },
        label: { color: '#fff', fontSize: 12 },
      },
      lineStyle: {
        opacity: 0.5,
        width: 1.5,
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
.commodity-panel { width: 100%; height: 100%; display: flex; flex-direction: column; }
.chart-body { width: 100%; flex: 1; min-height: 0; }
</style>
