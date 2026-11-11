<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { listVms, editVm, type VmEditBody } from '@/api/vm'
import { listApps } from '@/api/app'
import { useAuthStore } from '@/stores/auth'
import { toast } from '@/composables/toast'
import {
  LIFECYCLE_ORDER,
  LIFECYCLE_TAGS,
  ENV_TAGS,
  ENV_OPTIONS,
  ZONE_LABELS,
  ZONE_OPTIONS,
  nextLifecycle,
} from '@/constants'
import type { VmHostVO, VmAppVO } from '@/types'
import StatusTag from '@/components/StatusTag.vue'
import PaginationBar from '@/components/PaginationBar.vue'
import BaseDrawer from '@/components/BaseDrawer.vue'
import BaseModal from '@/components/BaseModal.vue'
import AppIcon from '@/components/AppIcon.vue'
import { APP_STATUS_TAGS } from '@/constants'

const auth = useAuthStore()

// ---------- 列表 ----------
const filters = reactive({
  hostName: '',
  vmIp: '',
  lifecycleStatus: '',
  env: '',
  networkZone: '',
})
const pageNum = ref(1)
const pageSize = ref(10)
const total = ref(0)
const rows = ref<VmHostVO[]>([])
const loading = ref(false)

async function load() {
  loading.value = true
  try {
    const data = await listVms({
      hostName: filters.hostName || undefined,
      vmIp: filters.vmIp || undefined,
      lifecycleStatus: filters.lifecycleStatus || undefined,
      env: filters.env || undefined,
      networkZone: filters.networkZone || undefined,
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
  filters.hostName = ''
  filters.vmIp = ''
  filters.lifecycleStatus = ''
  filters.env = ''
  filters.networkZone = ''
  search()
}

function changePage(p: number) {
  pageNum.value = p
  load()
}

onMounted(load)

function isOwner(vm: VmHostVO) {
  return vm.owner?.id === auth.user?.userId
}

// ---------- 详情抽屉 ----------
const drawerOpen = ref(false)
const current = ref<VmHostVO | null>(null)
const relatedApps = ref<VmAppVO[]>([])
const appsLoading = ref(false)

async function openDetail(vm: VmHostVO) {
  current.value = vm
  drawerOpen.value = true
  relatedApps.value = []
  appsLoading.value = true
  try {
    const data = await listApps({ hostId: vm.hostId, pageNum: 1, pageSize: 50 })
    relatedApps.value = data.rows
  } finally {
    appsLoading.value = false
  }
}

// ---------- 编辑弹窗 ----------
const editOpen = ref(false)
const saving = ref(false)
const form = reactive<VmEditBody>({
  hostId: '',
  hostName: '',
  osType: '',
  osVersion: '',
  vmIp: '',
  cpuCores: null,
  memoryGb: null,
  diskGb: null,
  physicalHostIp: '',
  lifecycleStatus: undefined,
  networkZone: 'idc',
  env: 'dev',
  remark: '',
})

const editingVm = ref<VmHostVO | null>(null)

const lifecycleChoices = computed(() => {
  if (!editingVm.value) return []
  const cur = editingVm.value.lifecycleStatus
  const choices = [{ value: cur, label: `${LIFECYCLE_TAGS[cur]?.label ?? cur}（保持不变）` }]
  const next = nextLifecycle(cur)
  if (next) {
    choices.push({ value: next, label: `${LIFECYCLE_TAGS[next]?.label ?? next}（推进）` })
  }
  return choices
})

function openEdit(vm: VmHostVO) {
  editingVm.value = vm
  Object.assign(form, {
    hostId: vm.hostId,
    hostName: vm.hostName,
    osType: vm.osType,
    osVersion: vm.osVersion ?? '',
    vmIp: vm.vmIp ?? '',
    cpuCores: vm.cpuCores,
    memoryGb: vm.memoryGb,
    diskGb: vm.diskGb,
    physicalHostIp: vm.physicalHostIp ?? '',
    lifecycleStatus: vm.lifecycleStatus,
    networkZone: vm.networkZone,
    env: vm.env,
    remark: vm.remark ?? '',
  })
  editOpen.value = true
}

async function saveEdit() {
  if (!form.hostName.trim() || !form.osType.trim()) {
    toast.error('主机名和操作系统不能为空')
    return
  }
  saving.value = true
  try {
    const body: VmEditBody = { ...form }
    // 生命周期未变化则不传，避免后端做无谓校验
    if (editingVm.value && body.lifecycleStatus === editingVm.value.lifecycleStatus) {
      delete body.lifecycleStatus
    }
    await editVm(body)
    toast.success('修改成功')
    editOpen.value = false
    drawerOpen.value = false
    load()
  } catch {
    // 拦截器已提示
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="space-y-4">
    <div>
      <h1 class="text-2xl font-semibold tracking-tight text-ink">虚拟机列表</h1>
      <p class="mt-0.5 text-sm text-ink-muted">管理和配置全局虚拟化基础设施资产</p>
    </div>

    <!-- 筛选 -->
    <div class="card p-4">
      <div class="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
        <div>
          <label class="form-label">主机名</label>
          <input v-model="filters.hostName" class="input" placeholder="输入主机名" @keyup.enter="search" />
        </div>
        <div>
          <label class="form-label">IP 地址</label>
          <input v-model="filters.vmIp" class="input font-mono" placeholder="192.168.x.x" @keyup.enter="search" />
        </div>
        <div>
          <label class="form-label">运行状态</label>
          <select v-model="filters.lifecycleStatus" class="select">
            <option value="">全部状态</option>
            <option v-for="s in LIFECYCLE_ORDER" :key="s" :value="s">{{ LIFECYCLE_TAGS[s]?.label }}</option>
          </select>
        </div>
        <div>
          <label class="form-label">部署环境</label>
          <select v-model="filters.env" class="select">
            <option value="">所有环境</option>
            <option v-for="o in ENV_OPTIONS" :key="o.value" :value="o.value">{{ o.label }}</option>
          </select>
        </div>
        <div>
          <label class="form-label">网络区域</label>
          <select v-model="filters.networkZone" class="select">
            <option value="">全部区域</option>
            <option v-for="o in ZONE_OPTIONS" :key="o.value" :value="o.value">{{ o.label }}</option>
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
        共找到 <span class="font-medium text-ink">{{ total }}</span> 台主机
      </div>
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="bg-gray-50 text-left text-xs font-medium text-ink-muted">
              <th class="px-4 py-2.5">主机 / ID</th>
              <th class="px-4 py-2.5">IP 地址</th>
              <th class="px-4 py-2.5">环境</th>
              <th class="px-4 py-2.5">网络区域</th>
              <th class="px-4 py-2.5 text-right">配置</th>
              <th class="px-4 py-2.5">状态</th>
              <th class="px-4 py-2.5">负责人</th>
              <th class="px-4 py-2.5 text-right">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="vm in rows"
              :key="vm.hostId"
              class="cursor-pointer border-b border-line transition-colors last:border-0 hover:bg-gray-50"
              @click="openDetail(vm)"
            >
              <td class="px-4 py-3">
                <div class="font-medium text-primary">{{ vm.hostName }}</div>
                <div class="mt-0.5 font-mono text-xs text-ink-faint">{{ vm.hostId }}</div>
              </td>
              <td class="px-4 py-3 font-mono text-[13px]">{{ vm.vmIp || '-' }}</td>
              <td class="px-4 py-3">
                <StatusTag :value="vm.env" :map="ENV_TAGS" :dot="false" />
              </td>
              <td class="px-4 py-3 text-ink-secondary">{{ ZONE_LABELS[vm.networkZone] || vm.networkZone }}</td>
              <td class="px-4 py-3 text-right font-mono text-[13px] text-ink-secondary">
                {{ vm.cpuCores ?? '-' }}C / {{ vm.memoryGb ?? '-' }}G / {{ vm.diskGb ?? '-' }}G
              </td>
              <td class="px-4 py-3">
                <StatusTag :value="vm.lifecycleStatus" :map="LIFECYCLE_TAGS" />
              </td>
              <td class="px-4 py-3 text-ink-secondary">{{ vm.owner?.label || '-' }}</td>
              <td class="px-4 py-3 text-right" @click.stop>
                <button class="text-sm font-medium text-primary hover:underline" @click="openDetail(vm)">详情</button>
                <button
                  v-if="isOwner(vm) && vm.lifecycleStatus !== 'destroyed'"
                  class="ml-3 text-sm font-medium text-primary hover:underline"
                  @click="openEdit(vm)"
                >
                  编辑
                </button>
              </td>
            </tr>
            <tr v-if="!loading && rows.length === 0">
              <td colspan="8" class="px-4 py-16 text-center text-ink-faint">暂无数据</td>
            </tr>
          </tbody>
        </table>
      </div>
      <PaginationBar :total="total" :page-num="pageNum" :page-size="pageSize" @change="changePage" />
    </div>

    <!-- 详情抽屉 -->
    <BaseDrawer :open="drawerOpen" width="460px" @close="drawerOpen = false">
      <template v-if="current">
        <div class="border-b border-line bg-gray-50/60 px-6 py-5">
          <div class="flex items-start justify-between">
            <div class="flex items-center gap-2.5">
              <h2 class="text-lg font-semibold text-ink">{{ current.hostName }}</h2>
              <StatusTag :value="current.lifecycleStatus" :map="LIFECYCLE_TAGS" />
            </div>
            <button
              class="flex h-7 w-7 items-center justify-center rounded text-ink-muted hover:bg-gray-100"
              @click="drawerOpen = false"
            >
              <AppIcon name="close" />
            </button>
          </div>
          <div class="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 font-mono text-xs text-ink-muted">
            <span class="inline-flex items-center gap-1">
              <AppIcon name="tag" class="!text-[14px]" />{{ current.hostId }}
            </span>
            <span class="inline-flex items-center gap-1">
              <AppIcon name="lan" class="!text-[14px]" />{{ current.vmIp || '-' }}
            </span>
          </div>
        </div>

        <div class="flex-1 space-y-6 overflow-y-auto px-6 py-5">
          <!-- 基本配置 -->
          <section>
            <h3 class="mb-3 flex items-center gap-1.5 text-sm font-semibold text-ink">
              <AppIcon name="info" class="!text-[18px] text-primary" />基本配置
            </h3>
            <div class="grid grid-cols-2 gap-px overflow-hidden rounded-lg border border-line bg-line">
              <div class="bg-white p-3">
                <div class="text-xs text-ink-faint">操作系统</div>
                <div class="mt-1 text-sm font-medium">{{ current.osType }} {{ current.osVersion || '' }}</div>
              </div>
              <div class="bg-white p-3">
                <div class="text-xs text-ink-faint">实例规格</div>
                <div class="mt-1 font-mono text-sm font-medium">
                  {{ current.cpuCores ?? '-' }}C / {{ current.memoryGb ?? '-' }}G / 磁盘 {{ current.diskGb ?? '-' }}G
                </div>
              </div>
              <div class="bg-white p-3">
                <div class="text-xs text-ink-faint">宿主机 IP</div>
                <div class="mt-1 font-mono text-sm font-medium">{{ current.physicalHostIp || '-' }}</div>
              </div>
              <div class="bg-white p-3">
                <div class="text-xs text-ink-faint">网络区域 / 环境</div>
                <div class="mt-1 text-sm font-medium">
                  {{ ZONE_LABELS[current.networkZone] || current.networkZone }} ·
                  {{ ENV_TAGS[current.env]?.label || current.env }}
                </div>
              </div>
              <div class="bg-white p-3">
                <div class="text-xs text-ink-faint">负责人</div>
                <div class="mt-1 text-sm font-medium">{{ current.owner?.label || '-' }}</div>
              </div>
              <div class="bg-white p-3">
                <div class="text-xs text-ink-faint">创建时间</div>
                <div class="mt-1 font-mono text-[13px] font-medium">{{ current.createTime || '-' }}</div>
              </div>
            </div>
            <div v-if="current.remark" class="mt-3 rounded-lg border border-line bg-gray-50 p-3 text-sm text-ink-secondary">
              <span class="text-xs text-ink-faint">备注：</span>{{ current.remark }}
            </div>
          </section>

          <!-- 关联应用 -->
          <section>
            <h3 class="mb-3 flex items-center gap-1.5 text-sm font-semibold text-ink">
              <AppIcon name="apps" class="!text-[18px] text-primary" />关联应用服务
              <span class="text-xs font-normal text-ink-faint">({{ relatedApps.length }})</span>
            </h3>
            <div v-if="appsLoading" class="py-6 text-center text-sm text-ink-faint">加载中…</div>
            <div v-else-if="relatedApps.length === 0" class="rounded-lg border border-dashed border-line py-6 text-center text-sm text-ink-faint">
              暂无关联应用
            </div>
            <div v-else class="space-y-2">
              <div
                v-for="app in relatedApps"
                :key="app.appId"
                class="flex items-center gap-3 rounded-lg border border-line p-3"
              >
                <div class="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-primary-light text-primary">
                  <AppIcon name="deployed_code" />
                </div>
                <div class="min-w-0 flex-1">
                  <div class="truncate text-sm font-medium">{{ app.appName }}</div>
                  <div class="truncate font-mono text-xs text-ink-faint">{{ app.deployPath }}</div>
                </div>
                <StatusTag :value="app.appStatus" :map="APP_STATUS_TAGS" />
              </div>
            </div>
          </section>
        </div>

        <div class="flex items-center justify-end gap-2 border-t border-line px-6 py-4">
          <button class="btn-ghost" @click="drawerOpen = false">关闭</button>
          <button
            v-if="isOwner(current) && current.lifecycleStatus !== 'destroyed'"
            class="btn-primary"
            @click="openEdit(current)"
          >
            编辑配置
          </button>
        </div>
      </template>
    </BaseDrawer>

    <!-- 编辑弹窗 -->
    <BaseModal :open="editOpen" title="编辑虚拟机" width="560px" @close="editOpen = false">
      <div class="grid grid-cols-2 gap-4">
        <div class="col-span-2">
          <label class="form-label">主机名 <span class="text-danger">*</span></label>
          <input v-model="form.hostName" class="input" maxlength="128" />
        </div>
        <div>
          <label class="form-label">操作系统 <span class="text-danger">*</span></label>
          <input v-model="form.osType" class="input" placeholder="CentOS" />
        </div>
        <div>
          <label class="form-label">系统版本</label>
          <input v-model="form.osVersion" class="input" placeholder="7.9" />
        </div>
        <div>
          <label class="form-label">虚机 IP</label>
          <input v-model="form.vmIp" class="input font-mono" placeholder="10.10.1.101" />
        </div>
        <div>
          <label class="form-label">宿主机 IP</label>
          <input v-model="form.physicalHostIp" class="input font-mono" placeholder="192.168.1.10" />
        </div>
        <div>
          <label class="form-label">CPU（核）</label>
          <input v-model.number="form.cpuCores" class="input font-mono" type="number" min="1" />
        </div>
        <div>
          <label class="form-label">内存（GB）</label>
          <input v-model.number="form.memoryGb" class="input font-mono" type="number" min="1" />
        </div>
        <div>
          <label class="form-label">磁盘（GB）</label>
          <input v-model.number="form.diskGb" class="input font-mono" type="number" min="1" />
        </div>
        <div>
          <label class="form-label">生命周期</label>
          <select v-model="form.lifecycleStatus" class="select">
            <option v-for="c in lifecycleChoices" :key="c.value" :value="c.value">{{ c.label }}</option>
          </select>
        </div>
        <div>
          <label class="form-label">网络区域 <span class="text-danger">*</span></label>
          <select v-model="form.networkZone" class="select">
            <option v-for="o in ZONE_OPTIONS" :key="o.value" :value="o.value">{{ o.label }}</option>
          </select>
        </div>
        <div>
          <label class="form-label">环境 <span class="text-danger">*</span></label>
          <select v-model="form.env" class="select">
            <option v-for="o in ENV_OPTIONS" :key="o.value" :value="o.value">{{ o.label }}</option>
          </select>
        </div>
        <div class="col-span-2">
          <label class="form-label">备注</label>
          <textarea
            v-model="form.remark"
            class="input h-20 resize-none py-2"
            maxlength="500"
            placeholder="选填"
          ></textarea>
        </div>
      </div>
      <p class="mt-3 text-xs text-ink-faint">
        生命周期只能按 创建中 → 运行中 → 已停止 → 待删除 → 已销毁 逐步推进，不可跳步或回退。修改虚机 IP 会同步更新其下所有应用的 IP。
      </p>
      <template #footer>
        <button class="btn-ghost" @click="editOpen = false">取消</button>
        <button class="btn-primary" :disabled="saving" @click="saveEdit">
          {{ saving ? '保存中…' : '保存' }}
        </button>
      </template>
    </BaseModal>
  </div>
</template>
