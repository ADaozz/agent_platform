<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { listApps, editApp, type AppEditBody } from '@/api/app'
import { toast } from '@/composables/toast'
import { APP_STATUS_TAGS } from '@/constants'
import type { VmAppVO } from '@/types'
import StatusTag from '@/components/StatusTag.vue'
import PaginationBar from '@/components/PaginationBar.vue'
import BaseModal from '@/components/BaseModal.vue'
import AppIcon from '@/components/AppIcon.vue'

const filters = reactive({
  appName: '',
  vmIp: '',
  appStatus: '',
})
const pageNum = ref(1)
const pageSize = ref(10)
const total = ref(0)
const rows = ref<VmAppVO[]>([])
const loading = ref(false)

async function load() {
  loading.value = true
  try {
    const data = await listApps({
      appName: filters.appName || undefined,
      vmIp: filters.vmIp || undefined,
      appStatus: filters.appStatus || undefined,
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
  filters.appName = ''
  filters.vmIp = ''
  filters.appStatus = ''
  search()
}

function changePage(p: number) {
  pageNum.value = p
  load()
}

onMounted(load)

// ---------- 编辑 ----------
const editOpen = ref(false)
const saving = ref(false)
const form = reactive<AppEditBody>({
  appId: '',
  appName: '',
  deployPath: '',
  appStatus: 'running',
})

function openEdit(app: VmAppVO) {
  Object.assign(form, {
    appId: app.appId,
    appName: app.appName,
    deployPath: app.deployPath,
    appStatus: app.appStatus,
  })
  editOpen.value = true
}

async function saveEdit() {
  if (!form.appName.trim() || !form.deployPath.trim()) {
    toast.error('应用名称和部署路径不能为空')
    return
  }
  saving.value = true
  try {
    await editApp({ ...form })
    toast.success('修改成功')
    editOpen.value = false
    load()
  } catch {
    // 拦截器已提示（非 owner 会返回业务错误）
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="space-y-4">
    <div>
      <h1 class="text-2xl font-semibold tracking-tight text-ink">应用服务</h1>
      <p class="mt-0.5 text-sm text-ink-muted">查看和管理部署在虚拟机上的应用服务</p>
    </div>

    <!-- 筛选 -->
    <div class="card p-4">
      <div class="grid grid-cols-2 gap-3 md:grid-cols-4 xl:grid-cols-5">
        <div>
          <label class="form-label">应用名称</label>
          <input v-model="filters.appName" class="input" placeholder="输入应用名称" @keyup.enter="search" />
        </div>
        <div>
          <label class="form-label">所在虚机 IP</label>
          <input v-model="filters.vmIp" class="input font-mono" placeholder="10.10.x.x" @keyup.enter="search" />
        </div>
        <div>
          <label class="form-label">运行状态</label>
          <select v-model="filters.appStatus" class="select">
            <option value="">全部状态</option>
            <option value="running">运行中</option>
            <option value="stopped">已停止</option>
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
      <div class="border-b border-line px-4 py-3 text-sm text-ink-muted">
        共找到 <span class="font-medium text-ink">{{ total }}</span> 个应用
      </div>
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="bg-gray-50 text-left text-xs font-medium text-ink-muted">
              <th class="px-4 py-2.5">应用 / ID</th>
              <th class="px-4 py-2.5">所在虚机 IP</th>
              <th class="px-4 py-2.5">部署路径</th>
              <th class="px-4 py-2.5">状态</th>
              <th class="px-4 py-2.5">更新时间</th>
              <th class="px-4 py-2.5 text-right">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="app in rows"
              :key="app.appId"
              class="border-b border-line transition-colors last:border-0 hover:bg-gray-50"
            >
              <td class="px-4 py-3">
                <div class="flex items-center gap-2.5">
                  <div class="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-primary-light text-primary">
                    <AppIcon name="deployed_code" class="!text-[18px]" />
                  </div>
                  <div class="min-w-0">
                    <div class="truncate font-medium">{{ app.appName }}</div>
                    <div class="truncate font-mono text-xs text-ink-faint">{{ app.appId }}</div>
                  </div>
                </div>
              </td>
              <td class="px-4 py-3 font-mono text-[13px]">{{ app.vmIp || '-' }}</td>
              <td class="px-4 py-3 font-mono text-[13px] text-ink-secondary">{{ app.deployPath }}</td>
              <td class="px-4 py-3">
                <StatusTag :value="app.appStatus" :map="APP_STATUS_TAGS" />
              </td>
              <td class="px-4 py-3 font-mono text-[13px] text-ink-muted">{{ app.updateTime || '-' }}</td>
              <td class="px-4 py-3 text-right">
                <button class="text-sm font-medium text-primary hover:underline" @click="openEdit(app)">编辑</button>
              </td>
            </tr>
            <tr v-if="!loading && rows.length === 0">
              <td colspan="6" class="px-4 py-16 text-center text-ink-faint">暂无数据</td>
            </tr>
          </tbody>
        </table>
      </div>
      <PaginationBar :total="total" :page-num="pageNum" :page-size="pageSize" @change="changePage" />
    </div>

    <!-- 编辑弹窗 -->
    <BaseModal :open="editOpen" title="编辑应用" width="480px" @close="editOpen = false">
      <div class="space-y-4">
        <div>
          <label class="form-label">应用名称 <span class="text-danger">*</span></label>
          <input v-model="form.appName" class="input" maxlength="128" />
        </div>
        <div>
          <label class="form-label">部署路径 <span class="text-danger">*</span></label>
          <input v-model="form.deployPath" class="input font-mono" placeholder="/opt/apps/xxx" maxlength="256" />
        </div>
        <div>
          <label class="form-label">运行状态 <span class="text-danger">*</span></label>
          <select v-model="form.appStatus" class="select">
            <option value="running">运行中</option>
            <option value="stopped">已停止</option>
          </select>
        </div>
        <p class="text-xs text-ink-faint">仅关联虚机的负责人可修改应用信息。</p>
      </div>
      <template #footer>
        <button class="btn-ghost" @click="editOpen = false">取消</button>
        <button class="btn-primary" :disabled="saving" @click="saveEdit">
          {{ saving ? '保存中…' : '保存' }}
        </button>
      </template>
    </BaseModal>
  </div>
</template>
