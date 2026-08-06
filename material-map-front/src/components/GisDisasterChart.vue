<template>
  <div class="panel gis-panel">
    <div class="panel-title">GIS 灾害-物资打点分布</div>
    <div ref="chartRef" class="chart-body"></div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import * as echarts from 'echarts'
import { disasterEvents, supplyPoints } from '../mock/disaster.js'
import chinaGeo from '../mock/china.json'

const chartRef = ref(null)
let chart = null

const DISASTER_COLORS = {
  '地震': '#ff5252',
  '洪水': '#448aff',
  '台风': '#ffab40',
  '滑坡': '#e040fb',
  '泥石流': '#795548',
}

function buildOption(geo) {
  echarts.registerMap('china', geo)
  return {
    tooltip: {
      trigger: 'item',
      backgroundColor: 'rgba(6,12,36,0.85)',
      borderColor: 'rgba(0,180,255,0.4)',
      textStyle: { color: '#e0f0ff', fontSize: 12 },
      formatter: (p) => {
        if (p.seriesName === '灾害事件') {
          const d = p.data
          return `<div style="font-weight:700;color:#ff5252;margin-bottom:4px">${d.name}</div>
            <table style="font-size:11px;line-height:1.8">
              <tr><td style="color:#90a4ae;padding-right:8px">类型</td><td style="color:#ffab40">${d.type}</td></tr>
              <tr><td style="color:#90a4ae">等级</td><td style="color:#ff5252">${d.level}</td></tr>
              <tr><td style="color:#90a4ae">时间</td><td style="color:#e0f0ff">${d.time}</td></tr>
              <tr><td style="color:#90a4ae">震级/量级</td><td>${d.value[2]}级</td></tr>
            </table>`
        }
        if (p.seriesName === '物资储备库') {
          const d = p.data
          return `<div style="font-weight:700;color:#00e676;margin-bottom:4px">${d.name}</div>
            <table style="font-size:11px;line-height:1.8">
              <tr><td style="color:#90a4ae;padding-right:8px">类别</td><td style="color:#00e5ff">${d.category}</td></tr>
              <tr><td style="color:#90a4ae">库存状态</td><td style="color:#69f0ae">${d.status}</td></tr>
              <tr><td style="color:#90a4ae">库存量</td><td style="color:#e0f0ff">${d.value[2]}吨</td></tr>
            </table>`
        }
        return p.name
      },
    },
    geo: {
      map: 'china',
      roam: true,
      zoom: 1.1,
      center: [104.5, 36],
      itemStyle: {
        areaColor: 'rgba(10,30,60,0.85)',
        borderColor: 'rgba(0,180,255,0.4)',
        borderWidth: 0.8,
      },
      emphasis: {
        itemStyle: {
          areaColor: 'rgba(20,60,100,0.7)',
          borderColor: '#00e5ff',
          borderWidth: 1.5,
        },
      },
    },
    series: [
      {
        name: '灾害事件',
        type: 'scatter',
        coordinateSystem: 'geo',
        data: disasterEvents.map(d => ({
          name: d.name,
          value: d.value,
          type: d.type,
          level: d.level,
          time: d.time,
        })),
        symbolSize: (val) => Math.sqrt(val[2]) * 6,
        itemStyle: {
          borderColor: '#fff',
          borderWidth: 1,
          shadowBlur: 10,
          shadowColor: 'rgba(255,0,0,0.5)',
        },
        label: {
          show: true,
          formatter: '{b}',
          position: 'right',
          color: '#c0d0e0',
          fontSize: 10,
        },
        encode: { tooltip: [1, 2, 3] },
      },
      {
        name: '物资储备库',
        type: 'scatter',
        coordinateSystem: 'geo',
        data: supplyPoints.map(d => ({
          name: d.name,
          value: d.value,
          category: d.category,
          status: d.status,
        })),
        symbolSize: (val) => Math.sqrt(val[2]) / 5,
        symbol: 'pin',
        itemStyle: {
          color: '#00e676',
          borderColor: '#fff',
          borderWidth: 1,
          shadowBlur: 8,
          shadowColor: 'rgba(0,230,118,0.5)',
        },
        label: {
          show: true,
          formatter: '{b}',
          position: 'bottom',
          color: '#69f0ae',
          fontSize: 10,
        },
      },
    ],
  }
}

onMounted(() => {
  chart = echarts.init(chartRef.value)
  chart.setOption(buildOption(chinaGeo))
  window.addEventListener('resize', () => chart?.resize())
})

onUnmounted(() => {
  chart?.dispose()
})
</script>

<style scoped>
.gis-panel { grid-area: gis; width: 100%; height: 100%; display: flex; flex-direction: column; }
.chart-body { width: 100%; flex: 1; min-height: 0; }
</style>
