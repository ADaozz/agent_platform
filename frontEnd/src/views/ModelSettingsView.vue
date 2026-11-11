<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { toast } from '@/composables/toast'
import AppIcon from '@/components/AppIcon.vue'
import {
  getGlobalModels, getModelOptions, getPersonalModels, saveGlobalModels, savePersonalModels, type ModelProfile,
} from '@/api/agentRuntime'
import { emptySource, modelIds, toForm, toLlm, validateForm, type ConfigForm } from '@/utils/modelConfigForm'

const auth = useAuthStore()
const isAdmin = computed(() => auth.isAdmin)
const tab = ref<'personal' | 'global'>('personal')
const loading = ref(true)
const saving = ref(false)
const error = ref('')

const personalForm = ref<ConfigForm>(toForm({}))
const personalRevision = ref(0)
const globalForm = ref<ConfigForm>(toForm({}))
const globalRevision = ref(0)
const platformModels = ref<ModelProfile[]>([])

const personal = computed(() => tab.value === 'personal')
const form = computed(() => (personal.value ? personalForm.value : globalForm.value))
const defaultOptions = computed(() => modelIds(form.value))

// 默认模型失效（来源或模型被改名/删除）时自动落到第一个可选项
watch(defaultOptions, (ids) => {
  if (!ids.includes(form.value.defaultModel)) form.value.defaultModel = ids[0] ?? ''
})

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [mine, options, shared] = await Promise.all([
      getPersonalModels(),
      getModelOptions(),
      isAdmin.value ? getGlobalModels() : Promise.resolve(null),
    ])
    personalForm.value = toForm(mine.llm)
    personalRevision.value = mine.revision
    platformModels.value = options.profiles.filter((p) => p.scope === 'global')
    if (shared) {
      globalForm.value = toForm(shared.llm)
      globalRevision.value = shared.revision
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    loading.value = false
  }
}

function switchTab(next: 'personal' | 'global') {
  tab.value = next
  error.value = ''
}

function addSource() {
  form.value.sources.push(emptySource())
}

async function save() {
  error.value = validateForm(form.value, personal.value) || ''
  if (error.value) return
  saving.value = true
  try {
    const llm = toLlm(form.value, personal.value)
    if (personal.value) await savePersonalModels(llm, personalRevision.value)
    else await saveGlobalModels(llm, globalRevision.value)
    toast(personal.value ? '个人模型已保存' : '全局模型已保存', 'success')
    await load()
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="mx-auto max-w-4xl space-y-4">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h1 class="text-lg font-semibold text-ink">模型配置</h1>
      </div>
      <div v-if="isAdmin" class="flex gap-2">
        <button :class="personal ? 'btn-primary' : 'btn-ghost'" @click="switchTab('personal')">我的模型</button>
        <button :class="!personal ? 'btn-primary' : 'btn-ghost'" @click="switchTab('global')">全局模型</button>
      </div>
    </div>

    <div v-if="loading" class="card p-8 text-center text-sm text-ink-muted">正在加载模型配置…</div>
    <template v-else>
      <div v-if="personal" class="card p-4">
        <h2 class="text-sm font-medium text-ink">平台提供的模型</h2>
        <div v-if="platformModels.length" class="mt-3 flex flex-wrap gap-2">
          <span v-for="m in platformModels" :key="m.id" class="rounded border border-line bg-page px-2 py-1 text-xs text-ink-secondary">
            {{ m.model }} <span class="text-ink-faint">· {{ m.id }}</span>
          </span>
        </div>
        <p v-else class="mt-3 text-xs text-ink-faint">暂无全局模型</p>
      </div>

      <div class="card space-y-4 p-4">
        <div class="flex items-center justify-between">
          <h2 class="text-sm font-medium text-ink">{{ personal ? '我的私人模型' : '全局模型' }}</h2>
          <button class="btn-ghost" @click="addSource"><AppIcon name="add" /> 添加模型来源</button>
        </div>

        <p v-if="!form.sources.length" class="rounded border border-dashed border-line p-6 text-center text-sm text-ink-faint">
          暂无模型来源
        </p>

        <div v-for="(source, si) in form.sources" :key="si" class="space-y-3 rounded-lg border border-line p-4">
          <div class="flex items-center justify-between">
            <span class="text-sm font-medium text-ink">来源 {{ si + 1 }}</span>
            <button class="text-xs text-danger hover:underline" @click="form.sources.splice(si, 1)">删除来源</button>
          </div>
          <div class="grid gap-3 sm:grid-cols-2">
            <label>
              <span class="form-label">来源名称</span>
              <input v-model="source.name" class="input" placeholder="如 deepseek" />
            </label>
            <label>
              <span class="form-label">接口地址</span>
              <input v-model="source.baseUrl" class="input" placeholder="https://api.deepseek.com/v1" />
            </label>
            <label>
              <span class="form-label">API Key</span>
              <input
                v-model="source.apiKey"
                class="input"
                :type="!personal && source.apiKey.startsWith('${') ? 'text' : 'password'"
                autocomplete="new-password"
                :placeholder="source.savedKeyAt ? '已保存，留空则不修改' : personal ? 'sk-...' : 'sk-... 或 ${ENV_NAME}'"
              />
            </label>
            <label>
              <span class="form-label">接口协议</span>
              <select v-model="source.api" class="select">
                <option value="chat_completions">Chat Completions</option>
                <option value="responses">Responses</option>
              </select>
            </label>
            <label>
              <span class="form-label">思考强度</span>
              <input v-model="source.efforts" class="input" placeholder="如 high, low, max" />
            </label>
            <label class="flex items-center gap-2 self-end pb-2 text-sm text-ink-secondary">
              <input v-model="source.image" type="checkbox" /> 支持图片输入
            </label>
          </div>
          <div>
            <span class="form-label">模型</span>
            <div v-for="(row, mi) in source.models" :key="mi" class="mb-2 flex items-center gap-2">
              <input v-model="row.key" class="input flex-1" placeholder="模型 ID，如 deepseek-chat" />
              <input v-model.number="row.contextWindow" class="input !w-44" type="number" min="0" placeholder="上下文窗口（可选）" />
              <button class="btn-ghost !px-2" title="删除模型" :disabled="source.models.length === 1" @click="source.models.splice(mi, 1)">
                <AppIcon name="delete" />
              </button>
            </div>
            <button class="text-xs text-primary hover:underline" @click="source.models.push({ key: '', contextWindow: null, extra: {} })">+ 添加模型</button>
          </div>
        </div>

        <div class="grid gap-3 sm:grid-cols-2">
          <label v-if="form.sources.length">
            <span class="form-label">默认模型</span>
            <select v-model="form.defaultModel" class="select">
              <option v-for="id in defaultOptions" :key="id" :value="id">{{ id }}</option>
            </select>
          </label>
          <label v-if="!personal">
            <span class="form-label">请求超时（秒）</span>
            <input v-model.number="form.timeout" class="input" type="number" min="1" placeholder="60" />
          </label>
        </div>

        <p v-if="error" role="alert" class="text-sm text-danger">{{ error }}</p>
        <div class="flex justify-end gap-2">
          <button class="btn-ghost" :disabled="saving" @click="load">重置</button>
          <button class="btn-primary" :disabled="saving" @click="save">{{ saving ? '保存中…' : '保存配置' }}</button>
        </div>
      </div>
    </template>
  </div>
</template>
