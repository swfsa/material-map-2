<template>
  <div class="panel map2d-panel">
    <div class="panel-title">物资态势地图</div>
    <div v-if="loading" class="loading-overlay">
      <span class="loading-spinner"></span>
    </div>
    <div ref="chartRef" class="chart-body"></div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import earthFlyLine from 'earth-flyline'
import { feature } from 'topojson-client'

const chartRef = ref(null)
const loading = ref(true)
let chart = null

const TOPO_URL = 'https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json'

const config = {
  R: 150,
  earth: { color: '#0c1530' },
  bgStyle: { color: '#040D21', opacity: 0 },
  mapStyle: { areaColor: '#013e87', lineColor: '#516aaf' },
  spriteStyle: { show: false },
  pathStyle: { show: false },
  flyLineStyle: { color: '#02fff6' },
  roadStyle: {
    flyLineStyle: { color: '#02fff6' },
    pathStyle: { color: '#02fff6' },
  },
  scatterStyle: { color: '#02fff6' },
  wallStyle: { color: '#02fff6', opacity: 0.5 },
}

function addFlyLines() {
  const targets = [
    { lon: 116.4, lat: 39.9 },
    { lon: 121.5, lat: 31.2 },
    { lon: 113.3, lat: 23.1 },
    { lon: 104.1, lat: 30.6 },
    { lon: 87.6, lat: 43.8 },
  ]
  const origins = [
    { lon: -74.0, lat: 40.7 },
    { lon: -0.1, lat: 51.5 },
    { lon: 151.2, lat: -33.9 },
    { lon: 37.6, lat: 55.8 },
    { lon: 55.3, lat: 25.3 },
    { lon: -46.6, lat: -23.5 },
    { lon: 139.7, lat: 35.7 },
    { lon: 103.8, lat: 1.4 },
  ]

  chart.setData('flyLine', origins.map((o, i) => ({
    from: { lon: o.lon, lat: o.lat },
    to: { lon: targets[i % targets.length].lon, lat: targets[i % targets.length].lat },
  })))
}

onMounted(async () => {
  try {
    const resp = await fetch(TOPO_URL)
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
    const topo = await resp.json()
    const geo = feature(topo, topo.objects.countries)
    earthFlyLine.registerMap('world', geo)

    chart = earthFlyLine.init({
      dom: chartRef.value,
      map: 'world',
      autoRotate: false,
      mode: '2d',
      config,
    })
    addFlyLines()
    highlightChina()
  } catch (e) {
    console.error('2D地图初始化失败:', e)
  } finally {
    loading.value = false
  }
})

function highlightChina() {
  if (!chart?.scene) return
  chart.scene.traverse((obj) => {
    if (obj.name === 'China' && obj.material && obj.userData?.type === 'country') {
      obj.material.color?.set('#00e5ff')
      obj.material.opacity = 0.7
      obj.material.transparent = true
      obj.material.needsUpdate = true
    }
  })
}

onUnmounted(() => {
  chart?.destroy()
})
</script>

<style scoped>
.map2d-panel { width: 100%; height: 100%; position: relative; overflow: hidden; }
.chart-body { width: 100%; height: 100%; }


</style>
