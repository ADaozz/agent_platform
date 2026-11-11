<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { TOKEN_KEY } from '@/api/request'
import { toast } from '@/composables/toast'
import { resolveApiBaseUrl } from '@/utils/openApiSamples'
import type { ApiTokenVO, OpenApiOperation, OpenApiTryAuthMode } from '@/types'

const props = defineProps<{
  operation: OpenApiOperation
  queryValues: Record<string, string>
  bodyJson: string
  tokens: ApiTokenVO[]
}>()

const authMode = ref<OpenApiTryAuthMode>('jwt')
const selectedAccessKey = ref('')
const secretKey = ref('')

const trying = ref(false)
const tryResult = ref<{
  status: number
  durationMs: number
  body: string
} | null>(null)

watch(
  () => props.operation.id,
  () => {
    tryResult.value = null
  },
)

watch(authMode, (mode) => {
  if (mode === 'aksk' && !selectedAccessKey.value && activeTokens.value.length > 0) {
    selectedAccessKey.value = activeTokens.value[0]!.accessKey
  }
})

const activeTokens = computed(() => props.tokens.filter((t) => t.status === '0'))

const requestUrl = computed(() => {
  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(props.queryValues)) {
    if (value.trim()) params.set(key, value.trim())
  }
  const qs = params.toString()
  const base = resolveApiBaseUrl()
  return `${base}${props.operation.path}${qs ? `?${qs}` : ''}`
})

const hasBody = computed(() => {
  const m = props.operation.method.toUpperCase()
  return m === 'PUT' || m === 'POST'
})

async function sendRequest() {
  if (authMode.value === 'aksk') {
    if (!selectedAccessKey.value.trim()) {
      toast.error('请选择 AccessKey')
      return
    }
    if (!secretKey.value.trim()) {
      toast.error('请输入 SecretKey')
      return
    }
  }

  trying.value = true
  tryResult.value = null
  const started = performance.now()

  try {
    const headers: Record<string, string> = {}
    if (authMode.value === 'jwt') {
      const token = localStorage.getItem(TOKEN_KEY)
      if (!token) {
        toast.error('未找到登录 token')
        return
      }
      headers.Authorization = `Bearer ${token}`
    } else {
      headers['X-Access-Key'] = selectedAccessKey.value.trim()
      headers['X-Secret-Key'] = secretKey.value.trim()
    }

    let body: string | undefined
    if (hasBody.value) {
      headers['Content-Type'] = 'application/json'
      body = props.bodyJson.trim() || '{}'
      try {
        JSON.parse(body)
      } catch {
        toast.error('请求体不是合法 JSON')
        return
      }
    }

    const res = await fetch(requestUrl.value, {
      method: props.operation.method.toUpperCase(),
      headers,
      body: hasBody.value ? body : undefined,
    })

    const text = await res.text()
    let formatted = text
    try {
      formatted = JSON.stringify(JSON.parse(text), null, 2)
    } catch {
      // keep raw
    }

    tryResult.value = {
      status: res.status,
      durationMs: Math.round(performance.now() - started),
      body: formatted,
    }
  } catch (e) {
    toast.error(e instanceof Error ? e.message : '请求失败')
  } finally {
    trying.value = false
  }
}
</script>

<template>
  <div class="space-y-4 rounded-md border border-line p-4">
    <div class="flex flex-wrap items-center justify-between gap-2">
      <h3 class="text-sm font-semibold text-ink">在线调试</h3>
      <div class="flex items-center gap-4 text-sm">
        <label class="flex cursor-pointer items-center gap-1.5">
          <input v-model="authMode" type="radio" class="accent-primary" value="jwt" />
          登录身份 (JWT)
        </label>
        <label class="flex cursor-pointer items-center gap-1.5">
          <input v-model="authMode" type="radio" class="accent-primary" value="aksk" />
          AK/SK 凭证
        </label>
      </div>
    </div>

    <div v-if="authMode === 'aksk'" class="grid grid-cols-1 gap-3 md:grid-cols-2">
      <div>
        <label class="form-label">AccessKey</label>
        <select v-model="selectedAccessKey" class="input font-mono text-[13px]">
          <option value="">请选择 Token</option>
          <option v-for="t in activeTokens" :key="t.accessKey" :value="t.accessKey">
            {{ t.tokenName }} ({{ t.accessKey }})
          </option>
        </select>
      </div>
      <div>
        <label class="form-label">SecretKey</label>
        <input
          v-model="secretKey"
          class="input font-mono text-[13px]"
          placeholder="创建 Token 时一次性展示的 SK"
          type="password"
          autocomplete="off"
        />
      </div>
    </div>

    <div class="rounded-md bg-gray-50 px-3 py-2 font-mono text-xs text-ink-muted break-all">
      {{ operation.method }} {{ requestUrl }}
    </div>

    <button type="button" class="btn-primary" :disabled="trying" @click="sendRequest">
      {{ trying ? '请求中…' : '发送请求' }}
    </button>

    <div v-if="tryResult" class="space-y-2">
      <div class="flex flex-wrap gap-3 text-sm">
        <span>
          状态码：
          <span
            class="font-mono font-medium"
            :class="tryResult.status >= 200 && tryResult.status < 300 ? 'text-emerald-600' : 'text-danger'"
          >
            {{ tryResult.status }}
          </span>
        </span>
        <span class="text-ink-muted">耗时：{{ tryResult.durationMs }} ms</span>
      </div>
      <pre class="max-h-80 overflow-auto rounded-md border border-line bg-gray-50 p-3 text-xs leading-relaxed text-ink-secondary"><code>{{ tryResult.body }}</code></pre>
    </div>
  </div>
</template>
