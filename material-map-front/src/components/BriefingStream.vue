<template>
  <section class="briefing-stream" aria-labelledby="briefing-title">
    <header class="briefing-header">
      <div>
        <div class="briefing-eyebrow">EIA / MARKET INTELLIGENCE</div>
        <h2 id="briefing-title">能源市场简报</h2>
      </div>
      <div class="header-actions">
        <div class="report-state" :class="status" role="status" aria-live="polite">
          <span class="state-light"></span>
          {{ statusText }}
        </div>
        <button
          class="refresh-button"
          type="button"
          :disabled="status === 'loading'"
          @click="loadReport"
        >
          刷新
        </button>
      </div>
    </header>

    <div ref="bodyRef" class="briefing-body">
      <div v-if="status === 'loading'" class="loading-state">
        <div class="radar-loader" aria-hidden="true"><span></span></div>
        <div>
          <strong>正在读取最新报告</strong>
          <p>连接 ReportIR，校验市场状态、趋势、波动与风险 blocks…</p>
        </div>
      </div>

      <div v-else-if="status === 'error' || status === 'empty'" class="message-state">
        <span class="message-code">{{ status === 'empty' ? 'NO REPORT' : 'LOAD ERROR' }}</span>
        <h3>{{ errorTitle }}</h3>
        <p>{{ errorMessage }}</p>
        <button type="button" @click="loadReport">重新读取</button>
      </div>

      <article v-else-if="blocks.length" class="report-document">
        <div class="report-metadata">
          <span>STRUCTURED REPORT / {{ blocks.length }} BLOCKS</span>
          <time :datetime="generatedAt">生成于 {{ formattedGeneratedAt }}</time>
        </div>
        <TransitionGroup name="block-reveal" tag="div" class="report-blocks">
          <ReportBlockRenderer
            v-for="(block, index) in visibleBlocks"
            :key="`${index}-${block.type}`"
            :block="block"
            :section-index="sectionIndexFor(index)"
          />
        </TransitionGroup>
        <div v-if="visibleBlocks.length < blocks.length" class="rendering-line">
          <span></span> 正在编排 {{ visibleBlocks.length }} / {{ blocks.length }}
        </div>
      </article>

      <div v-else class="idle-state">
        打开简报后，将从 <code>/api/reports/latest</code> 读取最近一次能源分析。
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, onUnmounted, ref, watch } from 'vue'
import {
  ReportApiError,
  ReportContractError,
  fetchLatestReport,
} from '../services/latestReport.js'
import ReportBlockRenderer from './report/ReportBlockRenderer.vue'

const props = defineProps({
  active: { type: Boolean, default: false },
})

const emit = defineEmits(['report-loaded'])

const bodyRef = ref(null)
const status = ref('idle')
const blocks = ref([])
const visibleCount = ref(0)
const generatedAt = ref('')
const errorTitle = ref('')
const errorMessage = ref('')

const visibleBlocks = computed(() => blocks.value.slice(0, visibleCount.value))
const statusText = computed(() => ({
  idle: '等待读取',
  loading: '数据同步中',
  success: visibleCount.value < blocks.value.length ? '报告编排中' : '已同步',
  empty: '暂无报告',
  error: '读取失败',
}[status.value]))

const formattedGeneratedAt = computed(() => {
  if (!generatedAt.value) return '—'
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  }).format(new Date(generatedAt.value))
})

let controller = null
let revealTimer = null
let requestVersion = 0

function stopReveal() {
  clearInterval(revealTimer)
  revealTimer = null
}

function stopRequest() {
  controller?.abort()
  controller = null
}

function sectionIndexFor(blockIndex) {
  const headingCount = blocks.value
    .slice(0, blockIndex + 1)
    .filter((block) => block.type === 'heading' && block.data.level > 1)
    .length
  return String(headingCount).padStart(2, '0')
}

function revealReport() {
  stopReveal()
  const reduceMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
  if (reduceMotion) {
    visibleCount.value = blocks.value.length
    return
  }

  visibleCount.value = Math.min(1, blocks.value.length)
  revealTimer = setInterval(() => {
    visibleCount.value += 1
    if (visibleCount.value >= blocks.value.length) {
      stopReveal()
    }
  }, 105)
}

function setErrorState(error) {
  if (error instanceof ReportApiError && error.code === 'not_found') {
    status.value = 'empty'
    errorTitle.value = '还没有可展示的能源简报'
    errorMessage.value = '请先在后端生成并保存一份 EIA 能源市场报告，然后重新读取。'
    return
  }

  status.value = 'error'
  if (error instanceof ReportContractError) {
    errorTitle.value = '报告数据合同不匹配'
    errorMessage.value = `${error.message}。请检查后端 ReportIR 版本。`
  } else {
    errorTitle.value = '无法读取最新能源简报'
    errorMessage.value = error?.message || '请检查后端服务和网络连接。'
  }
}

async function loadReport() {
  const version = ++requestVersion
  stopRequest()
  stopReveal()
  controller = new AbortController()
  status.value = 'loading'
  blocks.value = []
  visibleCount.value = 0
  errorTitle.value = ''
  errorMessage.value = ''

  try {
    const report = await fetchLatestReport({ signal: controller.signal })
    if (version !== requestVersion) return
    blocks.value = report.reportIr.blocks
    generatedAt.value = report.generatedAt
    status.value = 'success'
    emit('report-loaded', report.generatedAt)
    revealReport()
    requestAnimationFrame(() => {
      if (bodyRef.value) bodyRef.value.scrollTop = 0
    })
  } catch (error) {
    if (error?.name === 'AbortError' || version !== requestVersion) return
    setErrorState(error)
  } finally {
    if (version === requestVersion) controller = null
  }
}

watch(() => props.active, (active) => {
  if (active) {
    loadReport()
  } else {
    requestVersion += 1
    stopRequest()
    stopReveal()
  }
}, { immediate: true })

onUnmounted(() => {
  requestVersion += 1
  stopRequest()
  stopReveal()
})
</script>

<style scoped>
.briefing-stream {
  position: relative;
  display: flex;
  height: 100%;
  min-height: 0;
  flex-direction: column;
  overflow: hidden;
  background:
    linear-gradient(rgba(0, 229, 255, 0.025) 1px, transparent 1px),
    linear-gradient(90deg, rgba(0, 229, 255, 0.025) 1px, transparent 1px),
    linear-gradient(145deg, rgba(6, 18, 40, 0.94), rgba(4, 9, 27, 0.82));
  background-size: 26px 26px, 26px 26px, auto;
  border: 1px solid rgba(0, 180, 255, 0.2);
  border-radius: 4px;
  box-shadow: inset 0 0 50px rgba(0, 79, 117, 0.08);
}

.briefing-stream::before,
.briefing-stream::after {
  content: '';
  position: absolute;
  z-index: 2;
  width: 22px;
  height: 22px;
  pointer-events: none;
}

.briefing-stream::before {
  top: -1px;
  left: -1px;
  border-top: 2px solid #00e5ff;
  border-left: 2px solid #00e5ff;
}

.briefing-stream::after {
  right: -1px;
  bottom: -1px;
  border-right: 2px solid #ffab40;
  border-bottom: 2px solid #ffab40;
}

.briefing-header {
  z-index: 1;
  display: flex;
  flex-shrink: 0;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  padding: 15px 20px 13px;
  background: rgba(3, 12, 29, 0.86);
  border-bottom: 1px solid rgba(0, 180, 255, 0.16);
}

.briefing-eyebrow {
  margin-bottom: 3px;
  color: #4c7988;
  font: 9px/1.2 Consolas, monospace;
  letter-spacing: 2px;
}

.briefing-header h2 {
  margin: 0;
  color: #00e5ff;
  font-size: 16px;
  letter-spacing: 4px;
  text-shadow: 0 0 12px rgba(0, 229, 255, 0.3);
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.report-state {
  display: flex;
  align-items: center;
  gap: 7px;
  color: #7796a2;
  font-size: 10px;
  letter-spacing: 1px;
}

.state-light {
  width: 6px;
  height: 6px;
  background: currentColor;
  border-radius: 50%;
  box-shadow: 0 0 7px currentColor;
}

.report-state.loading { color: #ffab40; }
.report-state.success { color: #69f0ae; }
.report-state.error { color: #ff5252; }
.report-state.empty { color: #ffd166; }
.report-state.loading .state-light { animation: state-pulse 0.8s ease-in-out infinite; }

.refresh-button,
.message-state button {
  padding: 5px 10px;
  color: #85ddea;
  background: rgba(0, 180, 255, 0.06);
  border: 1px solid rgba(0, 180, 255, 0.28);
  border-radius: 2px;
  cursor: pointer;
  font: 10px/1.2 inherit;
  letter-spacing: 1px;
}

.refresh-button:hover:not(:disabled),
.message-state button:hover {
  color: #fff;
  border-color: #00e5ff;
  box-shadow: 0 0 12px rgba(0, 229, 255, 0.12);
}

.refresh-button:disabled {
  cursor: wait;
  opacity: 0.45;
}

.briefing-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 18px clamp(18px, 3vw, 42px) 46px;
  scroll-behavior: smooth;
}

.report-document {
  width: min(100%, 1160px);
  margin: 0 auto;
}

.report-metadata {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  margin-bottom: 20px;
  padding-bottom: 9px;
  color: #4d727f;
  border-bottom: 1px dashed rgba(0, 180, 255, 0.16);
  font: 9px/1.3 Consolas, monospace;
  letter-spacing: 1px;
}

.report-blocks {
  display: block;
}

.block-reveal-enter-active {
  transition: opacity 0.32s ease, transform 0.32s ease;
}

.block-reveal-enter-from {
  opacity: 0;
  transform: translateY(8px);
}

.rendering-line {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 20px;
  color: #547380;
  font: 9px/1 Consolas, monospace;
  letter-spacing: 1px;
}

.rendering-line span {
  width: 46px;
  height: 1px;
  overflow: hidden;
  background: linear-gradient(90deg, transparent, #00e5ff, transparent);
  animation: scan 1.2s linear infinite;
}

.loading-state,
.message-state,
.idle-state {
  min-height: 55vh;
  display: flex;
  align-items: center;
  justify-content: center;
}

.loading-state {
  gap: 22px;
}

.loading-state strong,
.message-state h3 {
  color: #cbeaf0;
  font-size: 15px;
  letter-spacing: 1px;
}

.loading-state p,
.message-state p {
  margin: 7px 0 0;
  color: #66808a;
  font-size: 11px;
}

.radar-loader {
  position: relative;
  width: 42px;
  height: 42px;
  overflow: hidden;
  border: 1px solid rgba(0, 229, 255, 0.4);
  border-radius: 50%;
  box-shadow: inset 0 0 14px rgba(0, 229, 255, 0.08);
}

.radar-loader::before,
.radar-loader::after {
  content: '';
  position: absolute;
  background: rgba(0, 229, 255, 0.25);
}

.radar-loader::before { top: 50%; left: 4px; right: 4px; height: 1px; }
.radar-loader::after { top: 4px; bottom: 4px; left: 50%; width: 1px; }

.radar-loader span {
  position: absolute;
  top: 50%;
  left: 50%;
  width: 19px;
  height: 1px;
  background: #00e5ff;
  transform-origin: left;
  animation: radar 1.15s linear infinite;
  box-shadow: 6px 0 8px #00e5ff;
}

.message-state {
  flex-direction: column;
  text-align: center;
}

.message-code {
  margin-bottom: 10px;
  color: #ffab40;
  font: 9px/1 Consolas, monospace;
  letter-spacing: 2px;
}

.message-state h3 { margin: 0; }
.message-state p { max-width: 520px; line-height: 1.7; }
.message-state button { margin-top: 18px; }

.idle-state {
  color: #58727d;
  font-size: 11px;
}

.idle-state code {
  margin: 0 5px;
  color: #70bcca;
  font-family: Consolas, monospace;
}

@keyframes state-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.2; }
}

@keyframes radar {
  to { transform: rotate(360deg); }
}

@keyframes scan {
  0% { opacity: 0.2; transform: translateX(-30%); }
  50% { opacity: 1; }
  100% { opacity: 0.2; transform: translateX(30%); }
}

@media (prefers-reduced-motion: reduce) {
  .report-state.loading .state-light,
  .radar-loader span,
  .rendering-line span {
    animation: none;
  }
  .block-reveal-enter-active { transition: none; }
}

@media (max-width: 700px) {
  .briefing-eyebrow,
  .report-state { display: none; }
  .briefing-header { padding-inline: 14px; }
  .briefing-body { padding-inline: 14px; }
  .report-metadata { align-items: flex-start; flex-direction: column; gap: 5px; }
}
</style>
