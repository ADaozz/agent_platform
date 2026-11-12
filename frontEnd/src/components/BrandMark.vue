<script setup lang="ts">
defineProps<{ size?: number }>()
</script>

<template>
  <!-- 工业铭牌：碳黑方形、暖白双框、几何 A 与指令箭头；三色仅用于侧栏字标下方 -->
  <svg
    xmlns="http://www.w3.org/2000/svg"
    viewBox="0 0 48 48"
    :width="size ?? 32"
    :height="size ?? 32"
    fill="none"
    role="img"
    aria-label="Deep Agent"
  >
    <rect x="1" y="1" width="46" height="46" fill="#181818" stroke="#F5EDDC" stroke-width="2" />
    <rect x="5" y="5" width="38" height="38" stroke="#F5EDDC" stroke-width="1.5" />
    <path d="M9 33L17 12H22L30 33H24.5L22.8 28H16.2L14.5 33ZM17.6 24H21.4L19.5 18.5Z" fill="#F36B18" fill-rule="evenodd" />
    <path d="M29 13L37 21L29 29" stroke="#F36B18" stroke-width="3.2" stroke-linecap="square" stroke-linejoin="miter" />
    <path d="M32 34H38M27 38H38" stroke="#F5EDDC" stroke-width="2.4" stroke-linecap="butt" />
  </svg>
</template>
