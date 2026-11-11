<script setup lang="ts">
import { computed } from 'vue'
import { icons, type IconName } from '@/icons'

const props = defineProps<{
  name: IconName
}>()

const paths = computed(() => {
  const icon = icons[props.name]
  return Array.isArray(icon) ? icon : [icon]
})
</script>

<template>
  <svg
    class="app-icon inline-block shrink-0 fill-current"
    xmlns="http://www.w3.org/2000/svg"
    viewBox="0 0 24 24"
    aria-hidden="true"
  >
    <path v-for="(d, i) in paths" :key="i" :d="d" />
  </svg>
</template>
