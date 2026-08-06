<template>
  <div class="app-root" :class="{ 'detail-mode': showDetail }">
    <canvas ref="starsCanvas" class="stars-canvas"></canvas>
    <header class="header">
      <div class="header-left">
        <span class="datetime">{{ currentTime }}</span>
      </div>
      <div class="header-title-block" :class="{ 'shift-left': showDetail }">
        <h1 class="main-title">物资态势监测与自动简报系统</h1>
      </div>
      <div class="header-right">
        <span class="status-dot online"></span>
        <span>系统运行中</span>
        <span class="status-sep">|</span>
        <span>数据更新: {{ lastUpdate }}</span>
      </div>
    </header>

    <div class="main-stage">
      <!-- 左侧面板 -->
      <div class="side-panels left-panels" :class="{ hide: showDetail }">
        <EnergyPriceChart class="panel-slot" />
        <WorldMap2D class="panel-slot" />
        <CommodityForceGraph class="panel-slot" />
      </div>

      <!-- 地球背景层 -->
      <div class="globe-area" :class="{ 'globe-left': showDetail }">
        <MapChart ref="globeMapRef" />
      </div>
      <!-- 占位 —— 保持 flex 布局空间 -->
      <div class="globe-spacer">
        <div class="mode-toggle">
          <button :class="['toggle-btn', { active: globeMode === 'world' }]" @click="setGlobeMode('world')">世界</button>
          <button :class="['toggle-btn', { active: globeMode === 'china' }]" @click="setGlobeMode('china')">中国</button>
        </div>
      </div>

      <!-- 右侧面板 -->
      <div class="side-panels right-panels" :class="{ hide: showDetail }">
        <!-- 数据简报切换 —— 左凸选项卡 -->
        <div class="briefing-toggle-tab">
          <button class="bt-btn" @click="toggleDetail">
            {{ showDetail ? '← 返回' : '数据简报' }}
          </button>
        </div>
        <div ref="agriRef" class="panel-slot flying-panel">
          <DualAxisAgriChart />
        </div>
        <div ref="dashRef" class="panel-slot flying-panel">
          <DashboardPanel />
        </div>
        <div class="panel-slot">
          <ImportSankeyChart />
        </div>
      </div>

      <!-- 数据简报区 -->
      <div class="detail-tables" :class="{ show: showDetail }">
        <button class="detail-back-btn" @click="toggleDetail">返回仪表盘</button>
        <BriefingStream :active="showDetail" @report-loaded="handleReportLoaded" />
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import EnergyPriceChart from './components/EnergyPriceChart.vue'
import DualAxisAgriChart from './components/DualAxisAgriChart.vue'
import WorldMap2D from './components/WorldMap2D.vue'
import DashboardPanel from './components/DashboardPanel.vue'
import MapChart from './components/MapChart.vue'
import CommodityForceGraph from './components/CommodityForceGraph.vue'
import ImportSankeyChart from './components/ImportSankeyChart.vue'
import BriefingStream from './components/BriefingStream.vue'

const showDetail = ref(false)
const currentTime = ref('')
const lastUpdate = ref('')

const agriRef = ref(null)
const dashRef = ref(null)
const starsCanvas = ref(null)
const globeMapRef = ref(null)
const globeMode = ref('world')

function setGlobeMode(mode) {
  globeMode.value = mode
  globeMapRef.value?.switchMode(mode)
}

async function toggleDetail() {
  showDetail.value = !showDetail.value
  await nextTick()
  // 等 CSS 过渡完成（width 0.5s）后再触发 resize，否则 ECharts 容器宽度为 0 无法正确渲染
  setTimeout(() => window.dispatchEvent(new Event('resize')), 550)
}

function updateTime() {
  const now = new Date()
  const pad = (n) => String(n).padStart(2, '0')
  currentTime.value = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())} ${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`
}

function handleReportLoaded(generatedAt) {
  const date = new Date(generatedAt)
  if (Number.isNaN(date.getTime())) return
  const pad = (n) => String(n).padStart(2, '0')
  lastUpdate.value = `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`
}

let timer
let starAnimId = null
let stars = []

function initStars() {
  const canvas = starsCanvas.value
  if (!canvas) return
  const ctx = canvas.getContext('2d')

  const resize = () => {
    canvas.width = window.innerWidth
    canvas.height = window.innerHeight
  }
  resize()
  window.addEventListener('resize', resize)

  stars = Array.from({ length: 100 }, () => ({
    x: Math.random() * canvas.width,
    y: Math.random() * canvas.height,
    r: Math.random() * 1.8 + 0.4,
    baseAlpha: Math.random() * 0.5 + 0.3,
    speed: Math.random() * 0.015 + 0.004,
    phase: Math.random() * Math.PI * 2,
  }))

  function animate() {
    ctx.clearRect(0, 0, canvas.width, canvas.height)
    for (const s of stars) {
      s.phase += s.speed
      const alpha = ((Math.sin(s.phase) + 1) / 2) * s.baseAlpha + 0.08
      ctx.beginPath()
      ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2)
      ctx.fillStyle = `rgba(220, 240, 255, ${Math.min(alpha, 1)})`
      ctx.fill()
    }
    starAnimId = requestAnimationFrame(animate)
  }
  animate()
}

onMounted(() => {
  updateTime()
  lastUpdate.value = currentTime.value
  timer = setInterval(updateTime, 1000)
  initStars()
})

onUnmounted(() => {
  clearInterval(timer)
  if (starAnimId) cancelAnimationFrame(starAnimId)
})
</script>

<style scoped>
.stars-canvas {
  position: fixed;
  inset: 0;
  z-index: 0;
  pointer-events: none;
}

.app-root {
  width: 100vw;
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: radial-gradient(ellipse at 50% 50%, rgba(0,80,160,0.06) 0%, transparent 70%);
  position: relative;
  z-index: 1;
}

/* ===== Header ===== */
.header {
  height: 56px;
  min-height: 56px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  background: transparent;
  flex-shrink: 0;
  z-index: 10;
  position: relative;
}
.header::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 5%;
  right: 5%;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(0, 200, 255, 0.3), rgba(0, 229, 255, 0.5), rgba(0, 200, 255, 0.3), transparent);
}
.header-left {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 180px;
}
.header-left::before {
  content: '';
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #00e5ff;
  box-shadow: 0 0 8px rgba(0, 229, 255, 0.6);
}
.datetime {
  font-size: 13px;
  color: #a0b8cc;
  font-family: 'Consolas', 'Courier New', monospace;
  letter-spacing: 1px;
}
.header-title-block {
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
  background: linear-gradient(180deg, rgba(0, 200, 255, 0.12) 0%, rgba(0, 150, 220, 0.06) 100%);
  padding: 10px 44px;
  backdrop-filter: blur(8px);
  clip-path: polygon(0% 0%, 100% 0%, 95% 100%, 5% 100%);
  transition: all 0.5s cubic-bezier(0.4, 0, 0.2, 1);
}
.header-title-block.shift-left {
  left: 24px;
  transform: translateX(0);
}
.header-title-block::before {
  content: '';
  position: absolute;
  top: 0;
  left: 5%;
  right: 5%;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(0, 229, 255, 0.6), transparent);
}
.main-title {
  font-size: 20px;
  font-weight: 600;
  color: #b3e5fc;
  letter-spacing: 5px;
  margin: 0;
  text-shadow: 0 0 18px rgba(0, 229, 255, 0.35), 0 0 36px rgba(0, 180, 255, 0.15);
  white-space: nowrap;
}
.header-right {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 11px;
  color: #78909c;
  min-width: 180px;
  justify-content: flex-end;
}
.status-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #00e676;
  box-shadow: 0 0 8px rgba(0, 230, 118, 0.5);
  flex-shrink: 0;
  animation: statusPulse 2s ease-in-out infinite;
}
@keyframes statusPulse {
  0%, 100% { box-shadow: 0 0 6px rgba(0, 230, 118, 0.4); }
  50% { box-shadow: 0 0 14px rgba(0, 230, 118, 0.8); }
}
.status-sep { color: rgba(255, 255, 255, 0.15); margin: 0 2px; }

/* ===== Main Stage ===== */
.main-stage {
  flex: 1;
  position: relative;
  display: flex;
  padding: 8px;
  gap: 0;
  min-height: 0;
}

.side-panels {
  width: 30%;
  display: flex;
  flex-direction: column;
  gap: 4px;
  transition: opacity 0.35s ease, width 0.5s ease;
  flex-shrink: 0;
  z-index: 5;
  pointer-events: auto;
}
.side-panels.hide {
  opacity: 0;
  width: 0;
  overflow: hidden;
  pointer-events: none;
}
.panel-slot { flex: 1; min-height: 0; }

.flying-panel { will-change: transform; }

/* 地球 — 固定全屏作为背景层 */
.globe-area {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 2;
  transition: transform 0.5s cubic-bezier(0.4, 0, 0.2, 1);
}
.globe-area.globe-left {
  transform: translateX(-40%) scale(2);
}
.globe-spacer {
  flex: 1;
  min-width: 0;
  pointer-events: none;
  position: relative;
}

/* 世界/中国切换 */
.mode-toggle {
  position: absolute;
  top: 6px;
  right: 10px;
  z-index: 15;
  display: flex;
  gap: 0;
  background: rgba(6, 12, 36, 0.75);
  border: 1px solid rgba(0, 180, 255, 0.15);
  border-radius: 4px;
  overflow: hidden;
  pointer-events: auto;
}
.toggle-btn {
  padding: 3px 12px;
  font-size: 12px;
  letter-spacing: 1px;
  color: #546e7a;
  background: transparent;
  border: none;
  cursor: pointer;
  transition: all 0.2s;
  font-family: inherit;
}
.toggle-btn:hover {
  color: #00e5ff;
  background: rgba(0, 180, 255, 0.08);
}
.toggle-btn.active {
  color: #00e5ff;
  background: rgba(0, 180, 255, 0.15);
  box-shadow: inset 0 -2px 0 #00e5ff;
}
.toggle-btn + .toggle-btn {
  border-left: 1px solid rgba(0, 180, 255, 0.12);
}

/* 详情表格区 */
.detail-tables {
  width: 0;
  overflow: hidden;
  opacity: 0;
  position: relative;
  z-index: 5;
  transition: width 0.5s cubic-bezier(0.4, 0, 0.2, 1),
              opacity 0.3s ease 0.2s;
}
.detail-tables.show {
  width: 66.667%;
  opacity: 1;
  z-index: 10;
  overflow: visible;
}

.detail-back-btn {
  position: absolute;
  left: -30px;
  top: 50%;
  transform: translateY(-50%);
  z-index: 15;
  writing-mode: vertical-rl;
  text-orientation: mixed;
  padding: 16px 10px;
  font-size: 12px;
  letter-spacing: 2px;
  color: #00e5ff;
  background: transparent;
  border: 1px solid rgba(0, 180, 255, 0.2);
  border-right: none;
  border-radius: 8px 0 0 8px;
  cursor: pointer;
  transition: all 0.25s ease;
  font-family: inherit;
  white-space: nowrap;
}
.detail-back-btn:hover {
  color: #fff;
  background: rgba(0, 180, 255, 0.1);
  border-color: rgba(0, 229, 255, 0.4);
  text-shadow: 0 0 8px rgba(0, 229, 255, 0.5);
}

.detail-tables :deep(.briefing-stream) {
  height: calc(100% - 12px);
  margin: 6px;
}

/* 数据简报 —— 左凸选项卡 */
.right-panels {
  position: relative;
}
.briefing-toggle-tab {
  position: absolute;
  left: -32px;
  top: 50%;
  transform: translateY(-50%);
  z-index: 15;
  background: transparent;
  border: 1px solid rgba(0, 180, 255, 0.2);
  border-right: none;
  border-radius: 8px 0 0 8px;
}
.bt-btn {
  writing-mode: vertical-rl;
  padding: 16px 10px;
  font-size: 12px;
  letter-spacing: 2px;
  color: #00e5ff;
  background: transparent;
  border: none;
  cursor: pointer;
  transition: all 0.25s ease;
  font-family: inherit;
  white-space: nowrap;
}
.bt-btn:hover {
  color: #fff;
  background: rgba(0, 180, 255, 0.1);
  text-shadow: 0 0 8px rgba(0, 229, 255, 0.5);
}

</style>
