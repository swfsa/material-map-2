<template>
  <div class="panel sankey-panel">
    <div class="panel-title">中国关键物资进口结构</div>
    <div ref="chartRef" class="chart-body"></div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import * as echarts from 'echarts'
import { sankeyData } from '../mock/importSankey.js'

const chartRef = ref(null)
let chart = null

const depthColors = [
  '#40c4ff', // 来源国
  '#ffab40', // 品类
  '#69f0ae', // 用途
]

function buildOption() {
  const nodes = sankeyData.nodes.map((n, i) => ({
    ...n,
    itemStyle: {
      color: depthColors[n.depth],
      borderColor: 'rgba(255,255,255,0.1)',
    },
    label: {
      color: '#a0b8cc',
      fontSize: 11,
    },
  }))

  return {
    tooltip: {
      trigger: 'item',
      triggerOn: 'mousemove',
      backgroundColor: 'rgba(6,12,36,0.85)',
      borderColor: 'rgba(0,180,255,0.4)',
      textStyle: { color: '#e0f0ff', fontSize: 12 },
      formatter: (p) => {
        if (p.dataType === 'edge') {
          return `${p.data.source} → ${p.data.target}<br/>贸易额: <span style="color:#00e5ff;font-weight:700">${p.data.value} 亿美元</span>`
        }
        return `<span style="font-weight:700;color:#00e5ff">${p.name}</span>`
      },
    },
    series: [{
      type: 'sankey',
      layout: 'none',
      layoutIterations: 32,
      emphasis: {
        focus: 'adjacency',
        lineStyle: { opacity: 0.8 },
        itemStyle: { borderWidth: 2, borderColor: '#fff' },
      },
      data: nodes,
      links: sankeyData.links,
      lineStyle: {
        color: 'gradient',
        curveness: 0.5,
        opacity: 0.3,
      },
      nodeWidth: 18,
      nodeGap: 12,
      label: {
        show: true,
        position: 'right',
        color: '#a0b8cc',
        fontSize: 11,
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
.sankey-panel { width: 100%; height: 100%; display: flex; flex-direction: column; }
.chart-body { width: 100%; flex: 1; min-height: 0; }
</style>
