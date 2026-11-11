<script setup lang="ts">
import { computed, ref } from 'vue'
import { toast } from '@/composables/toast'
import { generateOpenApiSample, type SampleContext } from '@/utils/openApiSamples'
import type { OpenApiOperation, OpenApiSampleLang } from '@/types'

const props = defineProps<{
  operation: OpenApiOperation
  baseUrl: string
  queryValues: Record<string, string>
  bodyJson: string
  accessKey: string
  secretKey: string
}>()

const langs: { key: OpenApiSampleLang; label: string }[] = [
  { key: 'python', label: 'Python3' },
  { key: 'java', label: 'Java' },
  { key: 'curl', label: 'curl' },
  { key: 'c', label: 'C' },
]

const activeLang = ref<OpenApiSampleLang>('python')

const sampleContext = computed<SampleContext>(() => ({
  baseUrl: props.baseUrl,
  operation: props.operation,
  queryValues: props.queryValues,
  bodyJson: props.bodyJson,
  accessKey: props.accessKey,
  secretKey: props.secretKey,
}))

const code = computed(() => generateOpenApiSample(activeLang.value, sampleContext.value))

async function copyCode() {
  try {
    await navigator.clipboard.writeText(code.value)
    toast.success('已复制到剪贴板')
  } catch {
    toast.error('复制失败，请手动复制')
  }
}
</script>

<template>
  <div class="space-y-2">
    <div class="flex flex-wrap items-center justify-between gap-2">
      <div class="flex flex-wrap gap-1">
        <button
          v-for="lang in langs"
          :key="lang.key"
          type="button"
          class="rounded-md px-3 py-1.5 text-sm transition-colors"
          :class="
            activeLang === lang.key
              ? 'bg-primary-light font-medium text-primary'
              : 'text-ink-muted hover:bg-gray-100'
          "
          @click="activeLang = lang.key"
        >
          {{ lang.label }}
        </button>
      </div>
      <button type="button" class="btn-ghost text-sm" @click="copyCode">复制代码</button>
    </div>
    <pre class="overflow-x-auto rounded-md border border-line bg-gray-50 p-4 text-xs leading-relaxed text-ink-secondary"><code>{{ code }}</code></pre>
  </div>
</template>
