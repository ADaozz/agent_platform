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

function render() {
  if (!chart || !props.option) return
  chart.setOption(props.option, true)
}

function resize() {
  chart?.resize()
}

onMounted(() => {
  chart = echarts.init(el.value!)
  render()
  window.addEventListener('resize', resize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', resize)
  chart?.dispose()
  chart = null
})

watch(() => props.option, render, { deep: true })
</script>

<template>
  <div ref="el" class="w-full" :style="{ height: height || '280px' }"></div>
</template>
