<script setup lang="ts">
defineProps<{ size?: number }>()
</script>

<template>
  <!-- 标识：切角暖白牌 + 碳黑 D + 橙色指令符 + 三色底条 -->
  <svg
    xmlns="http://www.w3.org/2000/svg"
    viewBox="0 0 48 48"
    :width="size ?? 32"
    :height="size ?? 32"
    fill="none"
    role="img"
    aria-label="Deep Agent"
  >
    <path d="M0 0H38L48 10V48H0Z" style="fill: var(--mark-tile, #f5eddc)" />
    <path d="M15 11H24C32 11 37 16.5 37 23.5C37 30.5 32 36 24 36H15Z" stroke-width="4.5" style="stroke: var(--mark-ink, #181818)" />
    <path d="M20.5 18.5L25.5 23.5L20.5 28.5" stroke="#D0713C" stroke-width="3.6" stroke-linecap="square" />
    <path d="M0 43H16V48H0Z" fill="#C84940" />
    <path d="M16 43H32V48H16Z" fill="#DFA93C" />
    <path d="M32 43H48V48H32Z" fill="#83A695" />
  </svg>
</template>
