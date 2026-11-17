<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts'
import type { EChartsOption } from 'echarts'

const props = defineProps<{
  option: EChartsOption | null
  height?: string
}>()

const el = ref<HTMLDivElement>()
let chart: echarts.ECharts | null = null
let observer: ResizeObserver | null = null

function render() {
  if (!chart || !props.option) return
  chart.setOption(props.option, true)
}

function resize() {
  hideTooltip()
  chart?.resize()
}

function hideTooltip() { chart?.dispatchAction({ type: 'hideTip' }) }
function hideOutside(event: Event) {
  if (!el.value?.contains(event.target as Node)) hideTooltip()
}

onMounted(() => {
  chart = echarts.init(el.value!)
  render()
  observer = new ResizeObserver(resize)
  observer.observe(el.value!)
  chart.getZr().on('globalout', hideTooltip)
  document.addEventListener('pointerdown', hideOutside, true)
  document.addEventListener('focusin', hideOutside, true)
  window.addEventListener('scroll', hideTooltip, true)
  window.addEventListener('touchmove', hideTooltip, { passive: true })
  window.addEventListener('blur', hideTooltip)
})

onBeforeUnmount(() => {
  document.removeEventListener('pointerdown', hideOutside, true)
  document.removeEventListener('focusin', hideOutside, true)
  window.removeEventListener('scroll', hideTooltip, true)
  window.removeEventListener('touchmove', hideTooltip)
  window.removeEventListener('blur', hideTooltip)
  observer?.disconnect()
  observer = null
  chart?.dispose()
  chart = null
})

watch(() => props.option, render, { deep: true })
</script>

<template>
  <div ref="el" class="echart-host w-full" @mouseleave="hideTooltip" :style="{ height: height || '280px' }"></div>
</template>

<style scoped>
.echart-host { isolation: isolate; }
</style>
