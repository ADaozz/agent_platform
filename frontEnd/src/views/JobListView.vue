<script setup lang="ts">
import PageHeader from '@/components/PageHeader.vue'
import { computed, onMounted, reactive, ref } from 'vue'
import { listJobs, editJob, changeJobStatus, runJob } from '@/api/job'
import { useAuthStore } from '@/stores/auth'
import { toast } from '@/composables/toast'
import { JOB_STATUS_DOTS } from '@/constants'
import { formatDateTime } from '@/utils/format'
import type { Id, JobEnabled, SysJobVO } from '@/types'
import PaginationBar from '@/components/PaginationBar.vue'
import BaseModal from '@/components/BaseModal.vue'
import AppIcon from '@/components/AppIcon.vue'

const auth = useAuthStore()
const canEdit = computed(() => auth.hasPerm('monitor:job:edit'))

// ---------- 列表 ----------
const filters = reactive({
  jobName: '',
  enabled: '',
})
const pageNum = ref(1)
const pageSize = ref(10)
const total = ref(0)
const rows = ref<SysJobVO[]>([])
const loading = ref(false)

async function load() {
  loading.value = true
  try {
    const data = await listJobs({
      jobName: filters.jobName || undefined,
      enabled: filters.enabled || undefined,
      pageNum: pageNum.value,
      pageSize: pageSize.value,
    })
    rows.value = data.rows
    total.value = data.total
  } finally {
    loading.value = false
  }
}

function search() {
  pageNum.value = 1
  load()
}

function resetFilters() {
  filters.jobName = ''
  filters.enabled = ''
  search()
}

function changePage(p: number) {
  pageNum.value = p
  load()
}

onMounted(load)

function statusDot(status: string) {
  return JOB_STATUS_DOTS[status] ?? { label: '未知', dotCls: 'bg-gray-300' }
}

// ---------- Switch 启用 / 停用 ----------
const switchingId = ref<Id | null>(null)

async function toggleEnabled(job: SysJobVO) {
  if (!canEdit.value || switchingId.value !== null) return
  const prev = job.enabled
  const next: JobEnabled = prev === '1' ? '0' : '1'
  // 未配置 Cron（空字符串）的任务无法启用，直接引导用户去填写
  if (next === '1' && !job.cronExpression.trim()) {
    toast.error('请先配置 Cron 表达式后再启用')
    openEdit(job)
    return
  }
  job.enabled = next // 乐观更新
  switchingId.value = job.jobId
  try {
    await changeJobStatus(job.jobId, next)
    toast.success(next === '1' ? '已启用' : '已停用')
  } catch {
    job.enabled = prev // 失败回弹（拦截器已提示后端 msg）
  } finally {
    switchingId.value = null
  }
}

// ---------- 编辑 ----------
const formOpen = ref(false)
const saving = ref(false)
const editingJob = ref<SysJobVO | null>(null)
const form = reactive({
  jobName: '',
  cronExpression: '',
  description: '',
})

function openEdit(job: SysJobVO) {
  editingJob.value = job
  Object.assign(form, {
    jobName: job.jobName,
    cronExpression: job.cronExpression,
    description: job.description ?? '',
  })
  formOpen.value = true
}

async function saveForm() {
  if (!editingJob.value) return
  if (!form.jobName.trim()) {
    toast.error('任务名称不能为空')
    return
  }
  if (editingJob.value.enabled === '1' && !form.cronExpression.trim()) {
    toast.error('任务已启用，Cron 表达式不能为空')
    return
  }
  saving.value = true
  try {
    await editJob({
      jobId: editingJob.value.jobId,
      jobName: form.jobName.trim(),
      cronExpression: form.cronExpression.trim(),
      description: form.description.trim() || undefined,
    })
    toast.success('修改成功')
    formOpen.value = false
    load()
  } catch {
    // 拦截器已提示
  } finally {
    saving.value = false
  }
}

// ---------- 手动执行 ----------
const runningId = ref<Id | null>(null)

async function handleRun(job: SysJobVO) {
  if (job.enabled !== '1' || runningId.value !== null) return
  runningId.value = job.jobId
  try {
    await runJob(job.jobId)
    toast.success(`任务「${job.jobName}」已触发执行`)
    load()
  } catch {
    // 拦截器已提示
  } finally {
    runningId.value = null
  }
}
</script>

<template>
  <div class="space-y-4">
    <PageHeader title="定时任务" desc="任务由后端代码扫描自动注册，可修改 Cron 表达式、启停调度及手动执行">
      <button class="btn-ghost" :disabled="loading" @click="load">
        <AppIcon name="refresh" class="!text-[18px]" />
        刷新
      </button>
    </PageHeader>

    <!-- 筛选 -->
    <div class="card p-4">
      <div class="grid grid-cols-2 gap-3 md:grid-cols-4 xl:grid-cols-5">
        <div>
          <label class="form-label">任务名称</label>
          <input v-model="filters.jobName" class="input" placeholder="搜索任务名称…" @keyup.enter="search" />
        </div>
        <div>
          <label class="form-label">启用状态</label>
          <select v-model="filters.enabled" class="select">
            <option value="">全部</option>
            <option value="1">启用</option>
            <option value="0">停用</option>
          </select>
        </div>
        <div class="flex items-end gap-2">
          <button class="btn-primary" @click="search">查询</button>
          <button class="btn-ghost" @click="resetFilters">重置</button>
        </div>
      </div>
    </div>

    <!-- 表格 -->
    <div class="card overflow-hidden">
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="bg-gray-50 text-left text-xs font-medium text-ink-muted">
              <th class="px-4 py-2.5">任务</th>
              <th class="px-4 py-2.5">Cron 表达式</th>
              <th class="px-4 py-2.5">描述</th>
              <th class="px-4 py-2.5">执行状态</th>
              <th class="px-4 py-2.5">启用</th>
              <th class="px-4 py-2.5">更新时间</th>
              <th class="px-4 py-2.5 text-right">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="job in rows"
              :key="job.jobId"
              class="border-b border-line transition-colors last:border-0 hover:bg-gray-50"
            >
              <td class="px-4 py-3">
                <div class="flex items-center gap-3">
                  <div class="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-primary-light text-primary">
                    <AppIcon name="schedule" />
                  </div>
                  <div>
                    <div class="font-medium">{{ job.jobName }}</div>
                    <div class="font-mono text-xs text-ink-faint">{{ job.beanName }}</div>
                  </div>
                </div>
              </td>
              <td class="px-4 py-3">
                <code
                  v-if="job.cronExpression"
                  class="rounded bg-gray-100 px-2 py-0.5 font-mono text-[13px] text-ink-secondary"
                >
                  {{ job.cronExpression }}
                </code>
                <span v-else class="text-xs text-ink-faint">未配置</span>
              </td>
              <td class="px-4 py-3 max-w-56 truncate text-ink-secondary" :title="job.description ?? ''">
                {{ job.description || '-' }}
              </td>
              <td class="px-4 py-3">
                <span class="inline-flex items-center gap-1.5 whitespace-nowrap text-xs text-ink-secondary">
                  <span class="h-2 w-2 rounded-full" :class="statusDot(job.status).dotCls"></span>
                  {{ statusDot(job.status).label }}
                </span>
              </td>
              <td class="px-4 py-3">
                <button
                  type="button"
                  role="switch"
                  :aria-checked="job.enabled === '1'"
                  class="relative inline-flex h-5 w-9 shrink-0 items-center rounded-full transition-colors"
                  :class="[
                    job.enabled === '1' ? 'bg-primary' : 'bg-gray-300',
                    !canEdit || switchingId !== null ? 'cursor-not-allowed opacity-50' : 'cursor-pointer',
                  ]"
                  :disabled="!canEdit"
                  :title="canEdit ? (job.enabled === '1' ? '点击停用' : '点击启用') : '无操作权限'"
                  @click="toggleEnabled(job)"
                >
                  <span
                    class="inline-block h-3.5 w-3.5 rounded-full bg-white shadow transition-transform"
                    :class="job.enabled === '1' ? 'translate-x-[18px]' : 'translate-x-[3px]'"
                  ></span>
                </button>
              </td>
              <td class="px-4 py-3 font-mono text-[13px] text-ink-muted">{{ formatDateTime(job.updateTime) }}</td>
              <td class="px-4 py-3 text-right whitespace-nowrap">
                <button
                  v-if="canEdit"
                  class="text-sm font-medium text-primary hover:underline"
                  @click="openEdit(job)"
                >
                  编辑
                </button>
                <button
                  v-if="canEdit"
                  class="ml-3 text-sm font-medium text-success hover:underline"
                  :disabled="job.enabled !== '1' || runningId !== null"
                  :class="{ 'cursor-not-allowed opacity-40': job.enabled !== '1' || runningId !== null }"
                  :title="job.enabled === '1' ? '手动执行一次' : '任务停用中，启用后才能执行'"
                  @click="handleRun(job)"
                >
                  {{ runningId === job.jobId ? '执行中…' : '执行' }}
                </button>
              </td>
            </tr>
            <tr v-if="!loading && rows.length === 0">
              <td colspan="7" class="px-4 py-16 text-center text-ink-faint">暂无数据</td>
            </tr>
          </tbody>
        </table>
      </div>
      <PaginationBar :total="total" :page-num="pageNum" :page-size="pageSize" @change="changePage" />
    </div>

    <!-- 编辑弹窗 -->
    <BaseModal :open="formOpen" title="编辑任务" width="440px" @close="formOpen = false">
      <div class="space-y-4">
        <div>
          <label class="form-label">Bean 名称（由代码扫描决定，不可修改）</label>
          <input :value="editingJob?.beanName" class="input bg-gray-50 text-ink-muted" disabled />
        </div>
        <div>
          <label class="form-label">任务名称 <span class="text-danger">*</span></label>
          <input v-model="form.jobName" class="input" maxlength="64" placeholder="请输入任务名称" />
        </div>
        <div>
          <label class="form-label">Cron 表达式</label>
          <input v-model="form.cronExpression" class="input font-mono" placeholder="如 0 */5 * * * ?（每 5 分钟）" />
          <p v-if="!form.cronExpression.trim()" class="mt-1 text-xs text-warning">
            尚未配置，填写合法表达式后任务才能启用
          </p>
        </div>
        <div>
          <label class="form-label">描述</label>
          <input v-model="form.description" class="input" maxlength="255" placeholder="任务描述（可选）" />
        </div>
      </div>
      <template #footer>
        <button class="btn-ghost" @click="formOpen = false">取消</button>
        <button class="btn-primary" :disabled="saving" @click="saveForm">
          {{ saving ? '保存中…' : '保存' }}
        </button>
      </template>
    </BaseModal>
  </div>
</template>
