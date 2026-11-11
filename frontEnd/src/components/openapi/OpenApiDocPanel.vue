<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { getOpenApiDoc } from '@/api/openDoc'
import { listTokens } from '@/api/token'
import { TOKEN_ASSET_LABELS } from '@/constants'
import { defaultBodyJson, defaultQueryValues, resolveApiBaseUrl } from '@/utils/openApiSamples'
import type { ApiTokenVO, OpenApiDoc, OpenApiOperation } from '@/types'
import OpenApiCodeExamples from '@/components/openapi/OpenApiCodeExamples.vue'
import OpenApiTryPanel from '@/components/openapi/OpenApiTryPanel.vue'
import AppIcon from '@/components/AppIcon.vue'

const loading = ref(false)
const doc = ref<OpenApiDoc | null>(null)
const selectedId = ref<string | null>(null)
const queryValues = ref<Record<string, string>>({})
const bodyJson = ref('{}')
const sampleAccessKey = ref('YOUR_ACCESS_KEY')
const sampleSecretKey = ref('YOUR_SECRET_KEY')
const tokens = ref<ApiTokenVO[]>([])

const baseUrl = computed(() => resolveApiBaseUrl())

const groupedOperations = computed(() => {
  const groups = new Map<string, { name: string; items: OpenApiOperation[] }>()
  for (const op of doc.value?.operations ?? []) {
    if (!groups.has(op.groupKey)) {
      groups.set(op.groupKey, { name: op.groupName, items: [] })
    }
    groups.get(op.groupKey)!.items.push(op)
  }
  return [...groups.entries()].map(([key, val]) => ({ key, ...val }))
})

const selectedOp = computed(() =>
  doc.value?.operations.find((o) => o.id === selectedId.value) ?? null,
)

function methodClass(method: string) {
  const m = method.toUpperCase()
  if (m === 'GET') return 'bg-emerald-50 text-emerald-700'
  if (m === 'PUT') return 'bg-amber-50 text-amber-700'
  if (m === 'POST') return 'bg-blue-50 text-blue-700'
  if (m === 'DELETE') return 'bg-red-50 text-red-700'
  return 'bg-gray-100 text-gray-600'
}

function selectOperation(op: OpenApiOperation) {
  selectedId.value = op.id
  queryValues.value = defaultQueryValues(op)
  bodyJson.value = defaultBodyJson(op)
}

watch(selectedOp, (op) => {
  if (!op) return
  queryValues.value = defaultQueryValues(op)
  bodyJson.value = defaultBodyJson(op)
})

async function loadDoc() {
  loading.value = true
  try {
    doc.value = await getOpenApiDoc()
    const first = doc.value.operations[0]
    if (first) selectOperation(first)
    else selectedId.value = null
  } catch {
    doc.value = null
  } finally {
    loading.value = false
  }
}

async function loadTokens() {
  try {
    const data = await listTokens({ pageNum: 1, pageSize: 50 })
    tokens.value = data.rows
    const active = data.rows.find((t) => t.status === '0')
    if (active) sampleAccessKey.value = active.accessKey
  } catch {
    tokens.value = []
  }
}

onMounted(() => {
  loadDoc()
  loadTokens()
})
</script>

<template>
  <div class="space-y-4">
    <div class="flex items-start gap-2 rounded-md border border-blue-200 bg-blue-50 px-3 py-2.5 text-sm text-blue-800">
      <AppIcon name="info" class="!text-[18px] shrink-0" />
      <div>
        <p>以下接口仅展示当前账号 Shiro 权限范围内可调用的开放能力。</p>
        <p v-if="doc?.auth" class="mt-1 text-blue-700/90">{{ doc.auth.note }}</p>
      </div>
    </div>

    <div v-if="loading" class="card px-4 py-16 text-center text-sm text-ink-faint">加载接口文档…</div>

    <div v-else-if="!doc?.operations.length" class="card px-4 py-16 text-center text-sm text-ink-faint">
      暂无可查看的开放接口（需 asset:vm:list / asset:app:list 等权限）
    </div>

    <div v-else class="grid grid-cols-1 gap-4 lg:grid-cols-[280px_minmax(0,1fr)]">
      <!-- 左栏接口列表 -->
      <div class="card overflow-hidden">
        <div class="border-b border-line px-3 py-2 text-xs font-medium text-ink-muted">接口列表</div>
        <div class="max-h-[70vh] overflow-y-auto p-2">
          <div v-for="group in groupedOperations" :key="group.key" class="mb-3 last:mb-0">
            <div class="px-2 py-1 text-xs font-semibold text-ink-faint">{{ group.name }}</div>
            <button
              v-for="op in group.items"
              :key="op.id"
              type="button"
              class="mb-1 flex w-full items-start gap-2 rounded-md px-2 py-2 text-left text-sm transition-colors last:mb-0"
              :class="selectedId === op.id ? 'bg-primary-light text-primary' : 'hover:bg-gray-50 text-ink-secondary'"
              @click="selectOperation(op)"
            >
              <span class="mt-0.5 shrink-0 rounded px-1.5 py-0.5 font-mono text-[11px] font-semibold" :class="methodClass(op.method)">
                {{ op.method }}
              </span>
              <span class="min-w-0 break-all font-mono text-[12px]">{{ op.path }}</span>
            </button>
          </div>
        </div>
      </div>

      <!-- 右栏详情 -->
      <div v-if="selectedOp" class="space-y-4">
        <div class="card p-4">
          <div class="flex flex-wrap items-center gap-2">
            <span class="rounded px-2 py-0.5 font-mono text-xs font-semibold" :class="methodClass(selectedOp.method)">
              {{ selectedOp.method }}
            </span>
            <span class="font-mono text-sm text-ink">{{ selectedOp.path }}</span>
          </div>
          <h2 class="mt-2 text-lg font-semibold text-ink">{{ selectedOp.summary }}</h2>
          <p class="mt-1 text-sm text-ink-muted">{{ selectedOp.description }}</p>
          <div class="mt-3 flex flex-wrap gap-2 text-xs">
            <span class="rounded border border-line bg-gray-50 px-2 py-1 text-ink-secondary">
              Token 授权：{{ TOKEN_ASSET_LABELS[selectedOp.grant] ?? selectedOp.grant }}
            </span>
            <span class="rounded border border-line bg-gray-50 px-2 py-1 text-ink-secondary">
              平台权限：{{ selectedOp.requiredPermission }}
            </span>
          </div>
        </div>

        <!-- Query 参数 -->
        <div v-if="selectedOp.queryParams.length" class="card overflow-hidden">
          <div class="border-b border-line px-4 py-2 text-sm font-medium text-ink">Query 参数</div>
          <div class="overflow-x-auto">
            <table class="w-full text-sm">
              <thead>
                <tr class="bg-gray-50 text-left text-xs text-ink-muted">
                  <th class="px-4 py-2">参数</th>
                  <th class="px-4 py-2">类型</th>
                  <th class="px-4 py-2">必填</th>
                  <th class="px-4 py-2">说明</th>
                  <th class="px-4 py-2">调试值</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="p in selectedOp.queryParams" :key="p.name" class="border-t border-line">
                  <td class="px-4 py-2 font-mono text-[13px]">{{ p.name }}</td>
                  <td class="px-4 py-2 text-ink-muted">{{ p.type }}</td>
                  <td class="px-4 py-2">{{ p.required ? '是' : '否' }}</td>
                  <td class="px-4 py-2 text-ink-muted">{{ p.description }}</td>
                  <td class="px-4 py-2">
                    <input v-model="queryValues[p.name]" class="input py-1 font-mono text-[13px]" :placeholder="p.example ?? ''" />
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- Body 参数 -->
        <div v-if="selectedOp.bodyParams.length" class="card p-4 space-y-3">
          <div class="text-sm font-medium text-ink">Request Body</div>
          <div class="overflow-x-auto">
            <table class="w-full text-sm">
              <thead>
                <tr class="bg-gray-50 text-left text-xs text-ink-muted">
                  <th class="px-3 py-2">字段</th>
                  <th class="px-3 py-2">类型</th>
                  <th class="px-3 py-2">必填</th>
                  <th class="px-3 py-2">说明</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="p in selectedOp.bodyParams" :key="p.name" class="border-t border-line">
                  <td class="px-3 py-2 font-mono text-[13px]">{{ p.name }}</td>
                  <td class="px-3 py-2 text-ink-muted">{{ p.type }}</td>
                  <td class="px-3 py-2">{{ p.required ? '是' : '否' }}</td>
                  <td class="px-3 py-2 text-ink-muted">{{ p.description }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div>
            <label class="form-label">JSON 请求体（调试 / 示例）</label>
            <textarea v-model="bodyJson" class="input min-h-[160px] resize-y font-mono text-[13px]" spellcheck="false" />
          </div>
        </div>

        <!-- 响应示例 -->
        <div v-if="selectedOp.responseExample" class="card p-4">
          <div class="mb-2 text-sm font-medium text-ink">响应示例</div>
          <pre class="overflow-x-auto rounded-md bg-gray-50 p-3 text-xs leading-relaxed text-ink-secondary"><code>{{ JSON.stringify(selectedOp.responseExample, null, 2) }}</code></pre>
        </div>

        <!-- 鉴权说明 -->
        <div v-if="doc?.auth" class="card p-4">
          <div class="mb-2 text-sm font-medium text-ink">鉴权方式</div>
          <p class="text-sm text-ink-muted">外部系统请求时在 Header 中携带：</p>
          <ul class="mt-2 space-y-1 text-sm font-mono text-ink-secondary">
            <li v-for="h in doc.auth.headers" :key="h.name">
              {{ h.name }}: {{ h.required ? '(必填)' : '(可选)' }}
            </li>
          </ul>
          <div class="mt-3 grid grid-cols-1 gap-3 md:grid-cols-2">
            <div>
              <label class="form-label">示例 AccessKey</label>
              <input v-model="sampleAccessKey" class="input font-mono text-[13px]" />
            </div>
            <div>
              <label class="form-label">示例 SecretKey</label>
              <input v-model="sampleSecretKey" class="input font-mono text-[13px]" placeholder="YOUR_SECRET_KEY" />
            </div>
          </div>
        </div>

        <!-- 代码示例 -->
        <div class="card p-4">
          <div class="mb-3 text-sm font-medium text-ink">调用示例</div>
          <OpenApiCodeExamples
            :operation="selectedOp"
            :base-url="baseUrl"
            :query-values="queryValues"
            :body-json="bodyJson"
            :access-key="sampleAccessKey"
            :secret-key="sampleSecretKey"
          />
        </div>

        <!-- 在线调试 -->
        <OpenApiTryPanel
          :operation="selectedOp"
          :query-values="queryValues"
          :body-json="bodyJson"
          :tokens="tokens"
        />
      </div>
    </div>
  </div>
</template>
