<template>
  <div class="panel briefing-panel">
    <div class="panel-title">态势简报</div>
    <div class="briefing-table">
      <div class="table-header">
        <span class="col-time">时间</span>
        <span class="col-level">级别</span>
        <span class="col-text">内容摘要</span>
      </div>
      <div class="table-body" ref="scrollRef">
        <div class="table-row" v-for="(item, i) in briefings" :key="i">
          <span class="col-time">{{ item.time }}</span>
          <span class="col-level">
            <span class="briefing-tag" :class="'tag-' + item.level">{{ item.level }}</span>
          </span>
          <span class="col-text">{{ item.text }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

const scrollRef = ref(null)

const briefings = ref([
  { time: '07-27 14:30', level: '预警', text: '中央气象台发布暴雨橙色预警，长江中下游地区需加强防洪物资储备' },
  { time: '07-27 12:15', level: '调拨', text: '成都储备库向甘孜地震灾区调拨帐篷2000顶、食品50吨，运输中队已出发' },
  { time: '07-27 10:08', level: '事件', text: '广东湛江台风"海鸥"登陆，风力12级，应急响应提升至Ⅱ级' },
  { time: '07-27 08:42', level: '信息', text: '武汉储备库完成月度盘点，库存物资充足率97.2%，物资状态良好' },
  { time: '07-26 22:10', level: '调拨', text: '昆明储备库向昭通滑坡灾区追加医疗物资15吨，预计明日08:00抵达' },
  { time: '07-26 18:35', level: '预警', text: '江西鄱阳湖水位超警戒1.8米，沿线5市启动防汛Ⅲ级应急响应' },
  { time: '07-26 15:00', level: '事件', text: '新疆喀什余震持续，救灾物资已覆盖全部安置点，灾民基本生活得到保障' },
  { time: '07-26 09:20', level: '信息', text: '广州储备库新增冲锋舟50艘、发电机80台入库，华南区域防汛能力进一步提升' },
])

let scrollTimer
onMounted(() => {
  const el = scrollRef.value
  if (!el) return
  scrollTimer = setInterval(() => {
    if (el.scrollTop >= el.scrollHeight - el.clientHeight) {
      el.scrollTop = 0
    } else {
      el.scrollTop += 1
    }
  }, 60)
})

onUnmounted(() => {
  clearInterval(scrollTimer)
})
</script>

<style scoped>
.briefing-panel { grid-area: briefing; width: 100%; height: 100%; display: flex; flex-direction: column; }
.briefing-table { flex: 1; display: flex; flex-direction: column; overflow: hidden; }

.table-header {
  display: flex;
  align-items: center;
  padding: 4px 12px;
  background: rgba(0,180,255,0.08);
  border-bottom: 1px solid rgba(0,180,255,0.2);
  font-size: 12px;
  color: #a0b8cc;
  letter-spacing: 1px;
  flex-shrink: 0;
}
.table-body {
  flex: 1;
  overflow-y: auto;
  padding: 2px 12px;
}
.table-row {
  display: flex;
  align-items: flex-start;
  padding: 5px 0;
  border-bottom: 1px solid rgba(255,255,255,0.04);
  font-size: 11px;
  line-height: 1.5;
  transition: background 0.2s;
  border-radius: 2px;
}
.table-row:hover {
  background: rgba(0, 180, 255, 0.06);
}
.table-row:last-child { border-bottom: none; }

.col-time  { width: 72px; flex-shrink: 0; color: #90a4ae; font-size: 11px; }
.col-level { width: 44px; flex-shrink: 0; text-align: center; }
.col-text  { flex: 1; color: #c0d0e0; }

.briefing-tag {
  display: inline-block;
  font-size: 9px;
  padding: 0 5px;
  border-radius: 2px;
  line-height: 1.6;
}
.tag-预警 { background: rgba(255,82,82,0.2); color: #ff5252; }
.tag-调拨 { background: rgba(255,171,64,0.2); color: #ffab40; }
.tag-事件 { background: rgba(0,229,255,0.15); color: #00e5ff; }
.tag-信息 { background: rgba(0,230,118,0.12); color: #00e676; }
</style>
