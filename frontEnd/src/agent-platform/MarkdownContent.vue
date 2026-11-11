<script setup>
import { computed } from 'vue'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
const props = defineProps({ content: String })
// Historical answers do not change when the composer or task clock updates.
const html = computed(() => DOMPurify.sanitize(marked.parse(props.content || '')))
</script>
<template><div v-html="html" class="markdown"></div></template>
