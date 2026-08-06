import { onMounted, onUnmounted, ref } from 'vue'
import * as echarts from 'echarts'

export function useChart(initOnMount = true) {
  const chartRef = ref(null)
  let chart = null

  function init() {
    if (!chartRef.value) return
    chart = echarts.init(chartRef.value)
    return chart
  }

  function setOption(option, notMerge) {
    chart?.setOption(option, notMerge)
  }

  function resize() {
    chart?.resize()
  }

  let _resizeHandler

  onMounted(() => {
    if (initOnMount) init()
    _resizeHandler = () => resize()
    window.addEventListener('resize', _resizeHandler)
  })

  onUnmounted(() => {
    window.removeEventListener('resize', _resizeHandler)
    chart?.dispose()
    chart = null
  })

  return { chartRef, chart, init, setOption, resize }
}
