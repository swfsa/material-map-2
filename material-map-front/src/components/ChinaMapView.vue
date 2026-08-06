<template>
  <div class="china-map-view">
    <div class="breadcrumb-bar">
      <template v-for="(level, idx) in drillStack" :key="level.adcode">
        <span v-if="idx > 0" class="breadcrumb-sep">&gt;</span>
        <span
          class="breadcrumb-item"
          :class="{ clickable: idx < drillStack.length - 1 }"
          @click="idx < drillStack.length - 1 && goBackTo(idx)"
        >{{ level.name }}</span>
      </template>
      <span v-if="drillStack.length > 1" class="back-btn" @click="goBack">返回</span>
      <span v-if="drillStack.length < 3" class="debug-info"></span>
    </div>
    <div v-if="loading" class="loading-overlay">
      <span class="loading-spinner"></span>
    </div>
    <div v-if="errorMsg" class="error-toast">{{ errorMsg }}</div>
    <div ref="mapRef" class="map-body"></div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import * as echarts from 'echarts'
import { disasterEvents, supplyPoints } from '../mock/disaster.js'
import chinaGeo from '../mock/china.json'

const MAX_DEPTH = 3

const mapRef = ref(null)
const loading = ref(false)
const drilling = ref(false)
const errorMsg = ref('')
const drillStack = ref([{ adcode: 100000, name: '中国' }])
const regionCount = ref(0)

let amap = null
let chart = null
let currentGeo = null
let nameToFeature = new Map()
let regionPolys = []
let scatterMarkers = []
let textLabels = []
let infoWin = null
let useAmap = false

const geoCache = new Map()
geoCache.set(100000, chinaGeo)

const DISASTER_COLORS = {
  '地震': '#ff5252',
  '洪水': '#448aff',
  '台风': '#ffab40',
  '滑坡': '#e040fb',
  '泥石流': '#795548',
}

async function fetchGeoJSON(adcode) {
  const localUrl = `/geojson/${adcode}.json`
  let resp = await fetch(localUrl)
  if (resp.ok) return resp.json()

  const apiUrl = `/api/geojson/areas_v3/bound/${adcode}_full.json`
  resp = await fetch(apiUrl)
  if (!resp.ok) throw new Error(`GeoJSON fetch failed: ${resp.status}`)
  return resp.json()
}

async function getGeoJSON(adcode) {
  if (geoCache.has(adcode)) return geoCache.get(adcode)
  const geo = await fetchGeoJSON(adcode)
  geoCache.set(adcode, geo)
  return geo
}

function flattenCoords(geom) {
  if (!geom) return []
  const { type, coordinates } = geom
  if (type === 'Polygon') return coordinates.flat()
  if (type === 'MultiPolygon') return coordinates.flat(2)
  return []
}

function computeBBox(geo) {
  let minLng = Infinity, maxLng = -Infinity
  let minLat = Infinity, maxLat = -Infinity
  geo.features?.forEach(f => {
    flattenCoords(f.geometry).forEach(([lng, lat]) => {
      if (lng < minLng) minLng = lng
      if (lng > maxLng) maxLng = lng
      if (lat < minLat) minLat = lat
      if (lat > maxLat) maxLat = lat
    })
  })
  return { minLng, maxLng, minLat, maxLat }
}

function isInside(p, bbox) {
  const [lng, lat] = p
  return lng >= bbox.minLng && lng <= bbox.maxLng && lat >= bbox.minLat && lat <= bbox.maxLat
}

function getCenter(geo) {
  const feat = geo.features?.[0]
  if (feat?.properties?.center) return feat.properties.center
  if (feat?.properties?.centroid) return feat.properties.centroid
  return [104.5, 36]
}

// === Cleanup helpers ===
function clearRegionPolys() {
  regionPolys.forEach(p => p.setMap(null))
  regionPolys = []
}

function clearScatterMarkers() {
  scatterMarkers.forEach(m => m.setMap(null))
  scatterMarkers = []
}

function clearTextLabels() {
  textLabels.forEach(t => t.setMap(null))
  textLabels = []
}

function closeInfoWin() {
  if (infoWin) {
    infoWin.close()
    infoWin = null
  }
}

function clearAllOverlays() {
  clearRegionPolys()
  clearScatterMarkers()
  clearTextLabels()
  closeInfoWin()
}

// === Polygon builders ===
function geoToPolygonPaths(geometry) {
  if (!geometry) return []
  const paths = []
  const type = geometry.type
  const coords = type === 'Polygon' ? [geometry.coordinates] : (geometry.coordinates || [])

  coords.forEach(ring => {
    ring.forEach(polygonCoords => {
      paths.push(polygonCoords.map(([lng, lat]) => [lng, lat]))
    })
  })
  return paths
}

function buildRegionPolygons(geo, onDrill) {
  geo.features?.forEach(f => {
    const { geometry, properties } = f
    if (!geometry || !properties?.name) return

    const paths = geoToPolygonPaths(geometry)
    paths.forEach(path => {
      const poly = new window.AMap.Polygon({
        path,
        fillColor: 'rgba(10, 30, 60, 0.35)',
        fillOpacity: 0.6,
        strokeColor: 'rgba(0, 180, 255, 0.5)',
        strokeWeight: 1,
        strokeOpacity: 0.8,
      })
      poly.on('click', () => {
        if (properties.adcode) onDrill(properties.adcode, properties.name)
      })
      poly.on('mouseover', () => {
        poly.setOptions({
          fillColor: 'rgba(20, 60, 100, 0.55)',
          strokeColor: '#00e5ff',
          strokeWeight: 1.5,
        })
        amap.setDefaultCursor('pointer')
      })
      poly.on('mouseout', () => {
        poly.setOptions({
          fillColor: 'rgba(10, 30, 60, 0.35)',
          strokeColor: 'rgba(0, 180, 255, 0.5)',
          strokeWeight: 1,
        })
        amap.setDefaultCursor('default')
      })
      poly.setMap(amap)
      regionPolys.push(poly)
    })
  })
}

// === Scatter marker builders ===
function buildDisasterMarkers(bbox) {
  const filtered = disasterEvents.filter(d => isInside(d.value, bbox))
  filtered.forEach(d => {
    const size = Math.max(Math.sqrt(d.value[2]) * 6, 6)
    const color = DISASTER_COLORS[d.type] || '#ff5252'

    const el = document.createElement('div')
    el.style.cssText = `width:${size}px;height:${size}px;border-radius:50%;background:${color};border:1px solid #fff;box-shadow:0 0 ${size}px ${color};opacity:0.85;transition:transform 0.15s,opacity 0.15s`
    el.dataset.size = size

    const marker = new window.AMap.Marker({
      position: [d.value[0], d.value[1]],
      content: el,
      offset: new window.AMap.Pixel(-size / 2, -size / 2),
      zIndex: 10,
    })

    const infoHtml = `<div style="font-weight:700;color:#ff5252;margin-bottom:4px">${d.name}</div>
      <table style="font-size:11px;line-height:1.8">
        <tr><td style="color:#90a4ae;padding-right:8px">类型</td><td style="color:#ffab40">${d.type}</td></tr>
        <tr><td style="color:#90a4ae">等级</td><td style="color:#ff5252">${d.level}</td></tr>
        <tr><td style="color:#90a4ae">时间</td><td style="color:#e0f0ff">${d.time}</td></tr>
        <tr><td style="color:#90a4ae">震级/量级</td><td>${d.value[2]}级</td></tr>
      </table>`

    marker.on('mouseover', () => {
      openInfoWin([d.value[0], d.value[1]], infoHtml)
      el.style.opacity = '1'
      el.style.transform = 'scale(1.3)'
    })
    marker.on('mouseout', () => {
      closeInfoWin()
      el.style.opacity = '0.85'
      el.style.transform = 'scale(1)'
    })

    marker.setMap(amap)
    scatterMarkers.push(marker)

    const label = new window.AMap.Text({
      position: [d.value[0], d.value[1]],
      text: d.name,
      offset: new window.AMap.Pixel(0, size / 2 + 10),
      style: {
        'background': 'transparent',
        'border': 'none',
        'color': color,
        'font-size': '11px',
        'text-shadow': `0 0 4px ${color}`,
        'white-space': 'nowrap',
      },
      zIndex: 8,
    })
    label.setMap(amap)
    textLabels.push(label)
  })
}

function buildSupplyMarkers(bbox) {
  const filtered = supplyPoints.filter(d => isInside(d.value, bbox))
  filtered.forEach(d => {
    const size = Math.max(Math.sqrt(d.value[2]) / 5, 6)

    const el = document.createElement('div')
    el.style.cssText = `width:${size}px;height:${size}px;border-radius:50%;background:#00e676;border:1px solid #fff;box-shadow:0 0 ${size}px #00e676;opacity:0.75;transition:transform 0.15s,opacity 0.15s`
    el.dataset.size = size

    const marker = new window.AMap.Marker({
      position: [d.value[0], d.value[1]],
      content: el,
      offset: new window.AMap.Pixel(-size / 2, -size / 2),
      zIndex: 9,
    })

    const infoHtml = `<div style="font-weight:700;color:#00e676;margin-bottom:4px">${d.name}</div>
      <table style="font-size:11px;line-height:1.8">
        <tr><td style="color:#90a4ae;padding-right:8px">类别</td><td style="color:#00e5ff">${d.category}</td></tr>
        <tr><td style="color:#90a4ae">库存状态</td><td style="color:#69f0ae">${d.status}</td></tr>
        <tr><td style="color:#90a4ae">库存量</td><td style="color:#e0f0ff">${d.value[2]}吨</td></tr>
      </table>`

    marker.on('mouseover', () => {
      openInfoWin([d.value[0], d.value[1]], infoHtml)
      el.style.opacity = '1'
      el.style.transform = 'scale(1.3)'
    })
    marker.on('mouseout', () => {
      closeInfoWin()
      el.style.opacity = '0.75'
      el.style.transform = 'scale(1)'
    })

    marker.setMap(amap)
    scatterMarkers.push(marker)

    const label = new window.AMap.Text({
      position: [d.value[0], d.value[1]],
      text: d.name,
      offset: new window.AMap.Pixel(0, size / 2 + 10),
      style: {
        'background': 'transparent',
        'border': 'none',
        'color': '#00e676',
        'font-size': '11px',
        'text-shadow': '0 0 4px #00e676',
        'white-space': 'nowrap',
      },
      zIndex: 8,
    })
    label.setMap(amap)
    textLabels.push(label)
  })
}

function openInfoWin(pos, content) {
  closeInfoWin()
  infoWin = new window.AMap.InfoWindow({
    content: `<div style="background:rgba(6,12,36,0.85);border:1px solid rgba(0,180,255,0.4);border-radius:4px;padding:8px 12px;color:#e0f0ff;font-size:12px;min-width:120px">${content}</div>`,
    offset: new window.AMap.Pixel(0, -15),
    isCustom: true,
  })
  infoWin.open(amap, pos)
}

// === ECharts geo fallback ===
function buildGeoOption(adcode) {
  const mapName = String(adcode)
  echarts.registerMap(mapName, currentGeo)
  const depth = drillStack.value.length
  const zoom = depth === 1 ? 1.1 : depth === 2 ? 1.3 : 1.5

  return {
    backgroundColor: 'transparent',
    tooltip: buildEChartsTooltip(),
    geo: {
      map: mapName,
      roam: true,
      zoom,
      center: getCenter(currentGeo),
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
        label: { color: '#fff', fontSize: 12 },
      },
    },
    series: buildEChartsScatterSeries(),
  }
}

function buildEChartsScatterSeries() {
  const bbox = computeBBox(currentGeo)
  const filteredDisasters = disasterEvents.filter(d => isInside(d.value, bbox))
  const filteredSupplies = supplyPoints.filter(d => isInside(d.value, bbox))

  return [
    {
      name: '灾害事件',
      type: 'scatter',
      coordinateSystem: 'geo',
      data: filteredDisasters.map(d => ({
        name: d.name,
        value: d.value,
        type: d.type,
        level: d.level,
        time: d.time,
        itemStyle: { color: DISASTER_COLORS[d.type] || '#ff5252' },
      })),
      symbolSize: val => Math.sqrt(val[2]) * 6,
      itemStyle: {
        borderColor: '#fff',
        borderWidth: 1,
        shadowBlur: 10,
        shadowColor: 'rgba(255,0,0,0.5)',
      },
      label: {
        show: true, formatter: '{b}', position: 'right',
        color: '#c0d0e0', fontSize: 10,
      },
    },
    {
      name: '物资储备库',
      type: 'scatter',
      coordinateSystem: 'geo',
      data: filteredSupplies.map(d => ({
        name: d.name,
        value: d.value,
        category: d.category,
        status: d.status,
      })),
      symbolSize: val => Math.sqrt(val[2]) / 5,
      symbol: 'pin',
      itemStyle: {
        color: '#00e676',
        borderColor: '#fff',
        borderWidth: 1,
        shadowBlur: 8,
        shadowColor: 'rgba(0,230,118,0.5)',
      },
      label: {
        show: true, formatter: '{b}', position: 'bottom',
        color: '#69f0ae', fontSize: 10,
      },
    },
  ]
}

function buildEChartsTooltip() {
  return {
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
  }
}

// === Render ===
async function renderCurrentLevel() {
  const level = drillStack.value[drillStack.value.length - 1]
  loading.value = true
  try {
    currentGeo = await getGeoJSON(level.adcode)
    nameToFeature.clear()
    if (currentGeo.features) {
      currentGeo.features.forEach(f => {
        if (f.properties?.name) nameToFeature.set(f.properties.name, f)
      })
    }
    regionCount.value = nameToFeature.size

    if (useAmap) {
      clearAllOverlays()

      const center = getCenter(currentGeo)
      const depth = drillStack.value.length
      const zoom = depth === 1 ? 4.8 : depth === 2 ? 7.5 : 9
      amap.setZoomAndCenter(zoom, center)

      if (currentGeo.features?.length > 0) {
        buildRegionPolygons(currentGeo, (adcode, name) => {
          errorMsg.value = ''
          drillDown(adcode, name)
        })
      }

      const bbox = computeBBox(currentGeo)
      buildDisasterMarkers(bbox)
      buildSupplyMarkers(bbox)
    } else {
      chart.setOption(buildGeoOption(level.adcode), true)
    }
  } catch (e) {
    console.error('地图加载失败:', e)
    errorMsg.value = '加载失败: ' + e.message
    setTimeout(() => errorMsg.value = '', 5000)
  } finally {
    loading.value = false
  }
}

// === Drill down ===
async function drillDown(adcode, name) {
  if (drilling.value || drillStack.value.length >= MAX_DEPTH) return
  drilling.value = true
  drillStack.value.push({ adcode, name })
  try {
    await renderCurrentLevel()
  } finally {
    drilling.value = false
  }
}

function goBack() {
  if (drilling.value || drillStack.value.length <= 1) return
  drilling.value = true
  drillStack.value.pop()
  renderCurrentLevel().finally(() => { drilling.value = false })
}

function goBackTo(idx) {
  if (drilling.value || idx >= drillStack.value.length - 1) return
  drilling.value = true
  drillStack.value = drillStack.value.slice(0, idx + 1)
  renderCurrentLevel().finally(() => { drilling.value = false })
}

function handleGeoClick(params) {
  console.log('Map click:', JSON.stringify({ ct: params.componentType, sn: params.seriesName, name: params.name }))
  if (!params.name) return
  const feature = nameToFeature.get(params.name)
  if (!feature?.properties?.adcode) return
  errorMsg.value = ''
  drillDown(feature.properties.adcode, params.name)
}

// === Lifecycle ===
function initAMap() {
  console.log('Initializing AMap...')
  const center = getCenter(chinaGeo)
  amap = new window.AMap.Map(mapRef.value, {
    center,
    zoom: 4.8,
    viewMode: '2D',
    layers: [new window.AMap.TileLayer.Satellite(), new window.AMap.TileLayer.RoadNet()],
    zooms: [4, 18],
    resizeEnable: true,
    showBuildingBlock: false,
  })

  amap.on('complete', () => {
    console.log('AMap tiles loaded')
  })
  console.log('AMap instance created:', amap)
}

onMounted(async () => {
  if (window.AMap) {
    try {
      initAMap()
      useAmap = true
      console.log('Using AMap mode')
    } catch (e) {
      console.warn('AMap init failed, falling back to ECharts geo:', e)
      useAmap = false
    }
  } else {
    console.log('window.AMap not available, using ECharts geo mode')
    useAmap = false
  }

  if (!useAmap) {
    chart = echarts.init(mapRef.value)
    chart.on('click', handleGeoClick)
  }

  await renderCurrentLevel()

  window.addEventListener('resize', () => {
    if (useAmap) {
      amap?.resize?.()
    } else {
      chart?.resize()
    }
  })
})

onUnmounted(() => {
  clearAllOverlays()
  amap?.destroy()
  amap = null
  if (!useAmap) {
    chart?.off('click', handleGeoClick)
  }
  chart?.dispose()
  chart = null
})
</script>

<style scoped>
.china-map-view {
  width: 100%;
  height: 100%;
  position: relative;
  overflow: hidden;
}
.map-body {
  width: 100%;
  height: 100%;
  background: transparent;
}

.breadcrumb-bar {
  position: absolute;
  top: 60px;
  left: calc(30% + 20px);
  z-index: 10;
  display: flex;
  align-items: center;
  gap: 2px;
  background: rgba(6, 12, 36, 0.75);
  border: 1px solid rgba(0, 180, 255, 0.15);
  border-radius: 4px;
  padding: 4px 10px;
  font-size: 13px;
}
.breadcrumb-item {
  color: #90a4ae;
  white-space: nowrap;
}
.breadcrumb-item.clickable {
  color: #00e5ff;
  cursor: pointer;
}
.breadcrumb-item.clickable:hover {
  text-decoration: underline;
}
.breadcrumb-sep {
  color: #546e7a;
  margin: 0 4px;
}
.back-btn {
  color: #ffab40;
  font-size: 11px;
  cursor: pointer;
  margin-left: 8px;
  white-space: nowrap;
}
.back-btn:hover {
  text-decoration: underline;
}

.error-toast {
  position: absolute;
  bottom: 12px;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(255, 82, 82, 0.9);
  color: #fff;
  padding: 6px 16px;
  border-radius: 4px;
  font-size: 12px;
  z-index: 25;
  white-space: nowrap;
}

.debug-info {
  color: #78909c;
  font-size: 10px;
  margin-left: 6px;
}
</style>
