<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import PageHeader from '@/components/PageHeader.vue'
import AppIcon from '@/components/AppIcon.vue'
import { toast } from '@/composables/toast'
import { tr } from '@/composables/preferences'
import type { IconName } from '@/icons'
import { getPlatformCapabilities, savePlatformCapabilities, type PlatformCapabilities } from '@/api/agentRuntime'

const TOOL_META: Record<string, { label: string; desc: string; icon: IconName }> = {
  ls: { label: '列出文件', desc: '列出线程工作区中的目录内容', icon: 'folder' },
  read_file: { label: '读取文件', desc: '按行读取工作区文件', icon: 'menu_book' },
  write_file: { label: '写入文件', desc: '创建或覆盖工作区文件', icon: 'build' },
  edit_file: { label: '编辑文件', desc: '对文件做精确的字符串替换', icon: 'build' },
  delete: { label: '删除文件', desc: '删除工作区中的文件', icon: 'delete' },
  glob: { label: '文件匹配', desc: '按通配符查找文件路径', icon: 'search' },
  grep: { label: '搜索内容', desc: '在文件中按正则搜索文本', icon: 'search' },
  execute: { label: '执行命令', desc: '在 Bubblewrap 沙箱内运行 Shell 命令', icon: 'deployed_code' },
  task: { label: '子 Agent 委派', desc: '派生隔离的子 Agent 并等待其结果', icon: 'lan' },
  start_background_task: { label: '后台子任务', desc: '在后台运行子 Agent，完成后自动回报结果', icon: 'lan' },
  read_subagent_log: { label: '子任务日志', desc: '查看委派任务的执行摘要', icon: 'history' },
  request_human_input: { label: '向用户提问', desc: '暂停执行并请求用户补充信息', icon: 'info' },
  web_search: { label: '联网搜索', desc: '通过搜索引擎检索公开信息', icon: 'search' },
  web_fetch: { label: '抓取网页', desc: '读取指定网址的页面内容', icon: 'lan' },
}

const data = ref<PlatformCapabilities | null>(null)
const draft = ref<{ core: Record<string, boolean>; tools: Record<string, boolean>; skills: Record<string, boolean> }>({ core: {}, tools: {}, skills: {} })
const loading = ref(true)
const saving = ref(false)
const error = ref('')

const editable = computed(() => !!data.value?.editable)

function reset(value: PlatformCapabilities) {
  data.value = value
  draft.value = {
    core: Object.fromEntries(value.core_tools.map((t) => [t.name, t.enabled])),
    tools: Object.fromEntries(value.tools.map((t) => [t.name, t.enabled])),
    skills: Object.fromEntries(value.skills.map((s) => [s.id, s.enabled])),
  }
}

/** 只提交与服务端不同的开关 */
const changes = computed(() => {
  const value = data.value
  if (!value) return null
  const diff = <T extends { enabled: boolean }>(list: T[], key: (item: T) => string, map: Record<string, boolean>) =>
    Object.fromEntries(list.filter((item) => map[key(item)] !== item.enabled).map((item) => [key(item), map[key(item)]!]))
  return {
    core_tools: diff(value.core_tools, (t) => t.name, draft.value.core),
    tools: diff(value.tools, (t) => t.name, draft.value.tools),
    skill_bindings: diff(value.skills, (s) => s.id, draft.value.skills),
  }
})
const changeCount = computed(() =>
  changes.value ? Object.values(changes.value).reduce((n, group) => n + Object.keys(group).length, 0) : 0,
)
const mountedCount = computed(() => {
  const d = draft.value
  const count = (map: Record<string, boolean>) => Object.values(map).filter(Boolean).length
  return { tools: count(d.core) + count(d.tools), skills: count(d.skills) }
})

async function load() {
  loading.value = true
  error.value = ''
  try {
    reset(await getPlatformCapabilities())
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    loading.value = false
  }
}

async function save() {
  if (!data.value || !changes.value || !changeCount.value) return
  saving.value = true
  error.value = ''
  try {
    reset(await savePlatformCapabilities({ revision: data.value.revision, ...changes.value }))
    toast(tr('平台能力已更新，新建对话生效'), 'success')
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
    <PageHeader :title="tr('平台能力')">
      <span v-if="data" class="cap-summary">
        {{ tr('工具') }} <b>{{ mountedCount.tools }}</b> · Skill <b>{{ mountedCount.skills }}</b>
      </span>
    </PageHeader>

    <div v-if="loading" class="card p-8 text-center text-sm text-ink-muted">{{ tr('正在加载平台能力…') }}</div>
    <p v-else-if="!data" role="alert" class="card p-6 text-sm text-danger">{{ error }}</p>
    <template v-else>
      <p v-if="!editable" class="cap-readonly" role="note">
        <AppIcon name="lock" class="!text-[15px]" />
        {{ tr('只读视图：仅管理员可以调整挂载') }}
      </p>

      <section class="card p-4">
        <header class="cap-head">
          <h2>{{ tr('内核工具') }}</h2>
          <span>{{ tr('平台内置，具有副作用的操作仍按会话权限请求审批') }}</span>
        </header>
        <div class="cap-grid">
          <label
            v-for="tool in data.core_tools"
            :key="tool.name"
            class="cap-item"
            :class="{ 'cap-off': !draft.core[tool.name], 'cap-locked': !editable }"
          >
            <span class="cap-icon"><AppIcon :name="TOOL_META[tool.name]?.icon || 'build'" class="!text-[16px]" /></span>
            <span class="cap-text">
              <strong>{{ tr(TOOL_META[tool.name]?.label || tool.name) }}</strong>
              <code>{{ tool.name }}</code>
              <small>{{ tr(TOOL_META[tool.name]?.desc || '') }}</small>
              <small v-if="tool.name === 'start_background_task' && !draft.core.task" class="cap-warn">{{ tr('需同时挂载「子 Agent 委派」才会生效') }}</small>
            </span>
            <input v-model="draft.core[tool.name]" type="checkbox" :disabled="!editable" :aria-label="tr(TOOL_META[tool.name]?.label || tool.name)" />
          </label>
        </div>
      </section>

      <section v-if="data.tools.length" class="card p-4">
        <header class="cap-head">
          <h2>{{ tr('扩展工具') }}</h2>
          <span>{{ tr('平台注册的结构化工具') }}</span>
        </header>
        <div class="cap-grid">
          <label v-for="tool in data.tools" :key="tool.name" class="cap-item" :class="{ 'cap-off': !draft.tools[tool.name], 'cap-locked': !editable }">
            <span class="cap-icon"><AppIcon name="extension" class="!text-[16px]" /></span>
            <span class="cap-text"><strong>{{ tool.name }}</strong><small>{{ tool.description }}</small></span>
            <input v-model="draft.tools[tool.name]" type="checkbox" :disabled="!editable" :aria-label="tool.name" />
          </label>
        </div>
      </section>

      <section class="card p-4">
        <header class="cap-head">
          <h2>Skill</h2>
          <span>{{ tr('Agent 按需加载的能力包，例如 Word 与 PPT 文档生成') }}</span>
        </header>
        <p v-if="!data.skills.length" class="rounded border border-dashed border-line p-6 text-center text-sm text-ink-faint">{{ tr('暂无已安装的 Skill') }}</p>
        <div class="cap-grid cap-grid-wide">
          <label
            v-for="skill in data.skills"
            :key="skill.id"
            class="cap-item"
            :class="{ 'cap-off': !draft.skills[skill.id], 'cap-locked': !editable || !skill.available }"
          >
            <span class="cap-icon cap-icon-skill" :data-kind="skill.feature_id || 'skill'">{{ (skill.feature_id || skill.name).slice(0, 4).toUpperCase() }}</span>
            <span class="cap-text">
              <strong>{{ skill.name }}<em>{{ tr(skill.source === 'feature' ? '内置扩展' : '已安装') }}</em></strong>
              <code>{{ skill.id }}</code>
              <small class="cap-desc">{{ skill.description }}</small>
              <small v-if="!skill.available" class="cap-warn">{{ tr('所属扩展功能已停用') }}</small>
            </span>
            <input v-model="draft.skills[skill.id]" type="checkbox" :disabled="!editable || !skill.available" :aria-label="skill.name" />
          </label>
        </div>
      </section>

      <p v-if="error" role="alert" class="text-sm text-danger">{{ error }}</p>
      <div v-if="editable" class="cap-actions">
        <span>{{ changeCount ? tr('{n} 项未保存的变更').replace('{n}', String(changeCount)) : tr('变更仅对新建对话生效，进行中的对话保留创建时的配置') }}</span>
        <button class="btn-ghost" :disabled="saving || !changeCount" @click="reset(data)">{{ tr('重置') }}</button>
        <button class="btn-primary" :disabled="saving || !changeCount" @click="save">{{ tr(saving ? '保存中…' : '保存挂载') }}</button>
      </div>
    </template>
  </div>
</template>

<style scoped>
.cap-summary {
  font-size: 12px;
  color: var(--color-ink-muted);
}
.cap-summary b {
  font-weight: 600;
  color: var(--color-ink);
  font-variant-numeric: tabular-nums;
}
.cap-readonly {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.625rem 0.875rem;
  border: 1px solid var(--color-line);
  border-radius: 10px;
  font-size: 12.5px;
  color: var(--color-ink-muted);
}
.cap-head {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 0.25rem 0.75rem;
  margin-bottom: 0.875rem;
}
.cap-head h2 {
  font-size: 14px;
  font-weight: 500;
  color: var(--color-ink);
}
.cap-head span {
  font-size: 12px;
  color: var(--color-ink-faint);
}
.cap-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: 0.625rem;
}
.cap-grid-wide {
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
}
.cap-item {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  padding: 0.75rem;
  border: 1px solid var(--color-line);
  border-radius: 10px;
  cursor: pointer;
  transition:
    border-color 0.16s,
    background-color 0.16s,
    opacity 0.16s;
}
.cap-item:hover:not(.cap-locked) {
  border-color: color-mix(in srgb, var(--color-signal) 45%, var(--color-line));
}
.cap-item:has(input:focus-visible) {
  outline: 2px solid var(--color-signal);
  outline-offset: 2px;
}
.cap-locked {
  cursor: default;
}
.cap-off {
  opacity: 0.55;
  border-style: dashed;
}
.cap-icon {
  display: inline-flex;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  width: 2rem;
  height: 2rem;
  border-radius: 8px;
  background: color-mix(in srgb, var(--color-signal) 12%, transparent);
  color: var(--color-signal);
}
.cap-icon-skill {
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.04em;
}
.cap-icon-skill[data-kind='docx'] {
  background: color-mix(in srgb, #2b579a 18%, transparent);
  color: #5b8bd6;
}
.cap-icon-skill[data-kind='pptx'] {
  background: color-mix(in srgb, #c43e1c 18%, transparent);
  color: #e0714d;
}
.cap-text {
  display: flex;
  min-width: 0;
  flex: 1;
  flex-direction: column;
  gap: 0.15rem;
}
.cap-text strong {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 13px;
  font-weight: 500;
  color: var(--color-ink);
}
.cap-text em {
  padding: 0 0.4rem;
  border-radius: 999px;
  border: 1px solid var(--color-line);
  font-size: 10.5px;
  font-style: normal;
  font-weight: 400;
  color: var(--color-ink-muted);
}
.cap-text code {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--color-ink-faint);
}
.cap-text small {
  font-size: 12px;
  line-height: 1.5;
  color: var(--color-ink-muted);
}
.cap-desc {
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.cap-warn {
  color: var(--color-warning) !important;
}
.cap-item input {
  margin-top: 0.2rem;
  flex-shrink: 0;
}
.cap-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 0.5rem;
  padding: 0.75rem 0;
}
.cap-actions span {
  margin-right: auto;
  font-size: 12px;
  color: var(--color-ink-faint);
}
@media (max-width: 480px) {
  .cap-grid,
  .cap-grid-wide {
    grid-template-columns: 1fr;
  }
  .cap-actions {
    flex-wrap: wrap;
    padding-bottom: calc(0.75rem + env(safe-area-inset-bottom));
  }
  .cap-actions span {
    flex-basis: 100%;
  }
  .cap-actions button {
    flex: 1;
  }
}
</style>
