<template>
  <component
    :is="`h${block.data.level}`"
    v-if="block.type === 'heading'"
    class="report-heading"
    :class="`level-${block.data.level}`"
  >
    <span v-if="block.data.level > 1" class="heading-index">{{ sectionIndex }}</span>
    {{ block.data.text }}
  </component>

  <section v-else-if="block.type === 'paragraph'" class="report-paragraph">
    <p>{{ block.data.text }}</p>
    <div v-if="block.data.evidence_ids.length" class="evidence-strip" aria-label="关联证据">
      <span class="evidence-label">EVIDENCE</span>
      <span
        v-for="(evidenceId, index) in block.data.evidence_ids"
        :key="evidenceId"
        class="evidence-chip"
        :title="evidenceId"
      >
        {{ index + 1 }}
      </span>
    </div>
  </section>

  <section v-else-if="block.type === 'kpiGrid'" class="kpi-section">
    <h3 v-if="block.data.title" class="block-title">{{ block.data.title }}</h3>
    <div class="kpi-grid">
      <article
        v-for="item in block.data.items"
        :key="`${item.label}-${item.as_of ?? ''}`"
        class="kpi-card"
        :class="`status-${item.status}`"
      >
        <div class="kpi-topline">
          <span class="kpi-label">{{ item.label }}</span>
          <span class="status-tag">{{ statusLabel(item.status) }}</span>
        </div>
        <div class="kpi-reading">
          <strong>{{ formatValue(item.value) }}</strong>
          <span v-if="item.unit" class="kpi-unit">{{ item.unit }}</span>
        </div>
        <div class="kpi-meta">
          <span class="trend" :class="`trend-${item.trend}`">
            {{ trendIcon(item.trend) }} {{ trendLabel(item.trend) }}
          </span>
          <span v-if="item.change !== null && item.change !== undefined" class="change">
            {{ formatChange(item.change) }} / {{ item.change_period || '周期' }}
          </span>
        </div>
        <time v-if="item.as_of" class="as-of" :datetime="item.as_of">
          AS OF {{ formatDate(item.as_of) }}
        </time>
      </article>
    </div>
  </section>

  <aside
    v-else-if="block.type === 'callout'"
    class="report-callout"
    :class="`severity-${block.data.severity}`"
  >
    <div class="callout-marker" aria-hidden="true">{{ severityIcon(block.data.severity) }}</div>
    <div class="callout-copy">
      <div class="callout-title-row">
        <h3>{{ block.data.title }}</h3>
        <span>{{ severityLabel(block.data.severity) }}</span>
      </div>
      <p>{{ block.data.text }}</p>
      <div v-if="block.data.evidence_ids.length" class="callout-evidence">
        关联 {{ block.data.evidence_ids.length }} 条数据证据
      </div>
    </div>
  </aside>

  <section v-else-if="block.type === 'table'" class="report-table-section">
    <div v-if="block.data.title" class="table-title-row">
      <h3>{{ block.data.title }}</h3>
      <span>{{ block.data.rows.length }} ROWS</span>
    </div>
    <div class="table-scroll">
      <table>
        <thead>
          <tr>
            <th v-for="column in block.data.columns" :key="column.key">
              {{ column.label }}
              <small v-if="column.unit">{{ column.unit }}</small>
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="block.data.rows.length === 0">
            <td :colspan="block.data.columns.length" class="empty-cell">当前窗口无明细</td>
          </tr>
          <tr v-for="(row, rowIndex) in block.data.rows" :key="rowIndex">
            <td v-for="column in block.data.columns" :key="column.key">
              <a
                v-if="isHttpUrl(row[column.key])"
                :href="row[column.key]"
                target="_blank"
                rel="noopener noreferrer"
              >来源链接 ↗</a>
              <span v-else>{{ formatCell(row[column.key]) }}</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>

<script setup>
const props = defineProps({
  block: { type: Object, required: true },
  sectionIndex: { type: String, default: '00' },
})

const numberFormatter = new Intl.NumberFormat('zh-CN', { maximumFractionDigits: 4 })

const trendLabels = {
  up: '上行',
  down: '下行',
  flat: '震荡',
  unknown: '待判断',
}

const statusLabels = {
  normal: '正常',
  watch: '关注',
  warning: '预警',
  critical: '严重',
}

const severityLabels = {
  info: '信息',
  watch: '关注',
  warning: '预警',
  critical: '严重',
}

function formatValue(value) {
  return typeof value === 'number' ? numberFormatter.format(value) : value
}

function formatCell(value) {
  if (value === null || value === undefined || value === '') return '—'
  if (typeof value === 'boolean') return value ? '是' : '否'
  return formatValue(value)
}

function formatChange(value) {
  const numeric = Number(value)
  const prefix = numeric > 0 ? '+' : ''
  return `${prefix}${numberFormatter.format(numeric)}%`
}

function formatDate(value) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(date)
}

function trendLabel(value) {
  return trendLabels[value] ?? trendLabels.unknown
}

function trendIcon(value) {
  return { up: '↗', down: '↘', flat: '→', unknown: '·' }[value] ?? '·'
}

function statusLabel(value) {
  return statusLabels[value] ?? value
}

function severityLabel(value) {
  return severityLabels[value] ?? value
}

function severityIcon(value) {
  return { info: 'i', watch: '!', warning: '!', critical: '×' }[value] ?? '!'
}

function isHttpUrl(value) {
  return typeof value === 'string' && /^https?:\/\//i.test(value)
}
</script>

<style scoped>
.report-heading {
  color: #d9f7ff;
  font-family: "Arial Narrow", "Microsoft YaHei", sans-serif;
  font-weight: 700;
}

.report-heading.level-1 {
  max-width: 880px;
  margin: 4px 0 32px;
  font-size: clamp(25px, 2.25vw, 38px);
  line-height: 1.2;
  letter-spacing: 2px;
  text-shadow: 0 0 24px rgba(0, 229, 255, 0.25);
}

.report-heading.level-1::after {
  content: '';
  display: block;
  width: 88px;
  height: 3px;
  margin-top: 16px;
  background: linear-gradient(90deg, #00e5ff, #ffab40);
  box-shadow: 0 0 12px rgba(0, 229, 255, 0.45);
}

.report-heading.level-2,
.report-heading.level-3 {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 34px 0 14px;
  font-size: 17px;
  letter-spacing: 2px;
}

.report-heading.level-3 {
  font-size: 14px;
  color: #9edbe8;
}

.heading-index {
  color: #ffab40;
  font: 600 10px/1.2 Consolas, monospace;
  letter-spacing: 1px;
}

.heading-index::after {
  content: '/';
  margin-left: 5px;
  color: rgba(0, 229, 255, 0.45);
}

.report-paragraph {
  max-width: 960px;
  margin: 0 0 20px;
  padding-left: 18px;
  border-left: 1px solid rgba(0, 229, 255, 0.35);
}

.report-paragraph p {
  margin: 0;
  color: #b9ced8;
  font-size: 14px;
  line-height: 1.9;
  letter-spacing: 0.4px;
}

.evidence-strip {
  display: flex;
  align-items: center;
  gap: 5px;
  margin-top: 10px;
}

.evidence-label {
  margin-right: 3px;
  color: #557886;
  font: 9px/1 Consolas, monospace;
  letter-spacing: 1.5px;
}

.evidence-chip {
  min-width: 18px;
  height: 18px;
  padding: 0 4px;
  border: 1px solid rgba(0, 229, 255, 0.25);
  border-radius: 2px;
  color: #71dce9;
  font: 10px/16px Consolas, monospace;
  text-align: center;
}

.block-title,
.table-title-row h3 {
  margin: 0;
  color: #d5edf4;
  font-size: 13px;
  letter-spacing: 1px;
}

.kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
  gap: 10px;
}

.kpi-card {
  --status-color: #69f0ae;
  position: relative;
  min-width: 0;
  padding: 14px;
  overflow: hidden;
  background: linear-gradient(145deg, rgba(10, 28, 52, 0.78), rgba(5, 13, 31, 0.62));
  border: 1px solid rgba(104, 164, 184, 0.2);
  border-top-color: var(--status-color);
}

.kpi-card::after {
  content: '';
  position: absolute;
  right: -18px;
  bottom: -18px;
  width: 48px;
  height: 48px;
  border: 1px solid color-mix(in srgb, var(--status-color) 35%, transparent);
  transform: rotate(45deg);
}

.kpi-card.status-watch { --status-color: #ffd166; }
.kpi-card.status-warning { --status-color: #ff8c42; }
.kpi-card.status-critical { --status-color: #ff5252; }

.kpi-topline,
.kpi-meta,
.callout-title-row,
.table-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.kpi-label {
  overflow: hidden;
  color: #9bb8c4;
  font-size: 11px;
  letter-spacing: 0.5px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.status-tag {
  padding: 2px 5px;
  color: var(--status-color);
  border: 1px solid color-mix(in srgb, var(--status-color) 42%, transparent);
  font-size: 9px;
  letter-spacing: 1px;
}

.kpi-reading {
  display: flex;
  align-items: baseline;
  gap: 7px;
  margin: 13px 0 9px;
}

.kpi-reading strong {
  color: #f0fbff;
  font: 600 25px/1 Consolas, "Microsoft YaHei", monospace;
}

.kpi-unit {
  overflow: hidden;
  color: #648896;
  font-size: 9px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.kpi-meta {
  justify-content: flex-start;
  color: #6f8e99;
  font-size: 10px;
}

.trend-up { color: #ff8c68; }
.trend-down { color: #69f0ae; }
.trend-flat { color: #71dce9; }

.as-of {
  display: block;
  margin-top: 9px;
  color: #415f6a;
  font: 9px/1.2 Consolas, monospace;
  letter-spacing: 0.5px;
}

.report-callout {
  --severity-color: #00e5ff;
  display: grid;
  grid-template-columns: 34px 1fr;
  gap: 12px;
  margin: 10px 0;
  padding: 14px;
  background: color-mix(in srgb, var(--severity-color) 6%, rgba(5, 13, 31, 0.78));
  border: 1px solid color-mix(in srgb, var(--severity-color) 30%, transparent);
  border-left: 3px solid var(--severity-color);
}

.report-callout.severity-watch { --severity-color: #ffd166; }
.report-callout.severity-warning { --severity-color: #ff8c42; }
.report-callout.severity-critical { --severity-color: #ff5252; }

.callout-marker {
  width: 28px;
  height: 28px;
  color: var(--severity-color);
  border: 1px solid var(--severity-color);
  font: 700 16px/26px Consolas, monospace;
  text-align: center;
}

.callout-title-row h3 {
  margin: 0;
  color: #e1f4f8;
  font-size: 13px;
}

.callout-title-row span {
  color: var(--severity-color);
  font-size: 9px;
  letter-spacing: 2px;
}

.callout-copy p {
  margin: 7px 0 0;
  color: #a9c0ca;
  font-size: 12px;
  line-height: 1.75;
}

.callout-evidence {
  margin-top: 7px;
  color: #607c87;
  font-size: 9px;
}

.report-table-section {
  margin: 12px 0 22px;
}

.table-title-row {
  margin-bottom: 8px;
}

.table-title-row span {
  color: #52707c;
  font: 9px/1 Consolas, monospace;
  letter-spacing: 1px;
}

.table-scroll {
  overflow-x: auto;
  border: 1px solid rgba(0, 180, 255, 0.16);
}

table {
  width: 100%;
  min-width: 680px;
  border-collapse: collapse;
  font-size: 11px;
}

th {
  padding: 10px 12px;
  color: #79d7e5;
  background: rgba(0, 180, 255, 0.08);
  border-bottom: 1px solid rgba(0, 180, 255, 0.2);
  font-weight: 600;
  letter-spacing: 0.7px;
  text-align: left;
  white-space: nowrap;
}

th small {
  display: block;
  margin-top: 2px;
  color: #506f7b;
  font: 8px/1 Consolas, monospace;
}

td {
  max-width: 360px;
  padding: 9px 12px;
  color: #afc4cc;
  border-bottom: 1px solid rgba(255, 255, 255, 0.045);
  line-height: 1.5;
  vertical-align: top;
}

tbody tr:hover td {
  background: rgba(0, 229, 255, 0.035);
}

td a {
  color: #00c9e5;
  text-decoration: none;
}

.empty-cell {
  color: #607681;
  text-align: center;
}

@media (max-width: 900px) {
  .kpi-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}

@media (max-width: 620px) {
  .kpi-grid { grid-template-columns: 1fr; }
  .report-heading.level-1 { font-size: 24px; }
}
</style>
