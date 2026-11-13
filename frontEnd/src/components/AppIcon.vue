<script setup lang="ts">
import { computed } from 'vue'
import { lonetrailIcons, lucideIcons, type IconName } from '@/icons'

const props = defineProps<{
  name: IconName
}>()

const lucide = computed(() => (lucideIcons as Record<string, unknown>)[props.name])
const lonetrail = computed(() => (lonetrailIcons as Record<string, string>)[props.name])
</script>

<template>
  <!-- LONETRAIL 工业线条图标：按原稿 1.5px 笔画、方头直角渲染 -->
  <svg
    v-if="lonetrail"
    class="app-icon inline-block shrink-0"
    xmlns="http://www.w3.org/2000/svg"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="1.5"
    stroke-linecap="square"
    stroke-linejoin="miter"
    aria-hidden="true"
  >
    <path :d="lonetrail" />
  </svg>
  <!-- 通用操作图标：lucide 同样使用方头直角；尺寸跟随 font-size -->
  <component :is="lucide" v-else class="app-icon inline-block shrink-0" :stroke-width="1.75" stroke-linecap="square" stroke-linejoin="miter" aria-hidden="true" />
</template>
