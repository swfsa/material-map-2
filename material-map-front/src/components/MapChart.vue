<template>
  <div class="panel map-panel">
    <div v-if="loading" class="loading-overlay">
      <span class="loading-spinner"></span>
    </div>
    <div v-show="currentMode === 'world'" ref="globeRef" class="chart-body"></div>
    <ChinaMapView v-if="currentMode === 'china'" ref="chinaMapRef" />
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import earthFlyLine from 'earth-flyline'
import ChinaMapView from './ChinaMapView.vue'
import { feature } from 'topojson-client'
import { BufferGeometry, BufferAttribute, ShaderMaterial, Points, AdditiveBlending, TextureLoader, Color } from 'three'

const globeRef = ref(null)
const chinaMapRef = ref(null)
const loading = ref(true)
const currentMode = ref('world')
let chart = null
let cachedGeoJSON = null
let stars = null
let starMaterial = null
let starAnimId = null

const TOPO_URL = 'https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json'

const config = {
  R: 150,
  earth: { color: '#ffffff', dragConfig: { disableY: true } },
  texture: {
    path: '/textures/earth-day.jpg',
    mixed: false,
  },
  bgStyle: { color: '#040D21', opacity: 0 },
  mapStyle: { areaColor: '#013e87', lineColor: '#516aaf' },
  spriteStyle: { color: '#138cdf', size: 2.5 },
  pathStyle: { color: '#7aaae9' },
  flyLineStyle: { color: '#02fff6' },
  roadStyle: {
    flyLineStyle: { color: '#02fff6' },
    pathStyle: { color: '#02fff6' },
  },
  scatterStyle: { color: '#02fff6' },
  wallStyle: { color: '#02fff6', opacity: 0.5 },

}

function initGlobe() {
  destroyGlobeResources()
  chart = earthFlyLine.init({
    dom: globeRef.value,
    map: 'world',
    autoRotate: true,
    stopRotateByHover: false,
    rotateSpeed: 0.005,
    mode: '3d',
    config,
  })
  createStarfield()
  animateStars()
  addFlyLines()
  highlightChina()
}


function addFlyLines() {
  const targets = [
    { name: '北京', lon: 116.4, lat: 39.9 },
    { name: '上海', lon: 121.5, lat: 31.2 },
    { name: '广州', lon: 113.3, lat: 23.1 },
    { name: '成都', lon: 104.1, lat: 30.6 },
    { name: '乌鲁木齐', lon: 87.6, lat: 43.8 },
  ]
  const origins = [
    { name: '纽约', lon: -74.0, lat: 40.7 },
    { name: '伦敦', lon: -0.1, lat: 51.5 },
    { name: '悉尼', lon: 151.2, lat: -33.9 },
    { name: '莫斯科', lon: 37.6, lat: 55.8 },
    { name: '迪拜', lon: 55.3, lat: 25.3 },
    { name: '圣保罗', lon: -46.6, lat: -23.5 },
    { name: '东京', lon: 139.7, lat: 35.7 },
    { name: '新加坡', lon: 103.8, lat: 1.4 },
  ]

  const flyLines = origins.map((o, i) => ({
    from: { lon: o.lon, lat: o.lat },
    to: { lon: targets[i % targets.length].lon, lat: targets[i % targets.length].lat },
  }))

  chart.setData('flyLine', flyLines)
}

function highlightChina() {
  if (!chart?.scene) return
  chart.scene.traverse((obj) => {
    if (!obj.material) return
    if (obj.userData?.type === 'country') {
      if (obj.name === 'China') {
        obj.material.color?.set('#00e5ff')
        obj.material.opacity = 0.6
        obj.material.transparent = true
      } else {
        obj.material.opacity = 0
        obj.material.transparent = true
      }
      obj.material.needsUpdate = true
    }
  })
}

function applyEmissiveMap() {
  new TextureLoader().load(
    '/textures/earth-night.jpg',
    (tex) => {
      tex.colorSpace = 'srgb'
      chart.scene.traverse((obj) => {
        if (obj.name === 'earthMesh' && obj.material) {
          obj.material.emissive = new Color('#ffffff')
          obj.material.emissiveMap = tex
          obj.material.needsUpdate = true
        }
      })
    }
  )
}

function createStarfield() {
  if (!chart?.scene) return
  const count = 2000
  const positions = new Float32Array(count * 3)
  const phases = new Float32Array(count)
  const speeds = new Float32Array(count)

  for (let i = 0; i < count; i++) {
    const theta = Math.random() * Math.PI * 2
    const phi = Math.acos(2 * Math.random() - 1)
    const r = 800 + Math.random() * 200
    positions[i * 3] = r * Math.sin(phi) * Math.cos(theta)
    positions[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta)
    positions[i * 3 + 2] = r * Math.cos(phi)
    phases[i] = Math.random() * Math.PI * 2
    speeds[i] = 0.3 + Math.random() * 1.5
  }

  const geom = new BufferGeometry()
  geom.setAttribute('position', new BufferAttribute(positions, 3))
  geom.setAttribute('phase', new BufferAttribute(phases, 1))
  geom.setAttribute('speed', new BufferAttribute(speeds, 1))

  starMaterial = new ShaderMaterial({
    uniforms: { uTime: { value: 0 } },
    vertexShader: `
      attribute float phase;
      attribute float speed;
      varying float vPhase;
      varying float vSpeed;
      void main() {
        vec4 mv = modelViewMatrix * vec4(position, 1.0);
        gl_Position = projectionMatrix * mv;
        gl_PointSize = 1.2 + 0.8 * sin(position.x * 3.0 + position.y * 7.0 + position.z * 5.0);
        vPhase = phase;
        vSpeed = speed;
      }
    `,
    fragmentShader: `
      varying float vPhase;
      varying float vSpeed;
      uniform float uTime;
      void main() {
        float d = length(gl_PointCoord - 0.5) * 2.0;
        if (d > 1.0) discard;
        float glow = 1.0 - d;
        float twinkle = 0.35 + 0.65 * (0.5 + 0.5 * sin(uTime * vSpeed + vPhase));
        float alpha = glow * twinkle;
        gl_FragColor = vec4(1.0, 1.0, 1.0, alpha);
      }
    `,
    transparent: true,
    depthTest: true,
    depthWrite: false,
    blending: AdditiveBlending,
  })

  stars = new Points(geom, starMaterial)
  stars.name = 'starfield'
  chart.scene.add(stars)
}

function animateStars() {
  if (!starMaterial) return
  starMaterial.uniforms.uTime.value += 0.016
  starAnimId = requestAnimationFrame(animateStars)
}

function destroyGlobeResources() {
  if (starAnimId) cancelAnimationFrame(starAnimId)
  if (stars) {
    stars.geometry?.dispose()
    stars.material?.dispose()
    chart?.scene?.remove(stars)
    stars = null
    starMaterial = null
  }
  chart?.destroy()
  chart = null
}

async function switchMode(mode) {
  if (mode === currentMode.value) return
  currentMode.value = mode
  await nextTick()
  if (mode === 'world') {
    initGlobe()
  } else {
    destroyGlobeResources()
  }
}

onMounted(async () => {
  try {
    const resp = await fetch(TOPO_URL)
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
    const topo = await resp.json()
    cachedGeoJSON = feature(topo, topo.objects.countries)
    earthFlyLine.registerMap('world', cachedGeoJSON)

    initGlobe()
  } catch (e) {
    console.error('地球初始化失败:', e)
  } finally {
    loading.value = false
  }
})

onUnmounted(() => {
  destroyGlobeResources()
})

defineExpose({ currentMode, switchMode })
</script>

<style scoped>
.map-panel { width: 100%; height: 100%; position: relative; overflow: hidden; }
.chart-body { width: 100%; height: 100%; overflow: hidden; direction: rtl; }


</style>
