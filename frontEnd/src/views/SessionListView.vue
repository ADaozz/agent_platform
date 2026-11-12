<script setup lang="ts">
import PageHeader from '@/components/PageHeader.vue'
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { listSessions, listSessionHistory, kickSession } from '@/api/session'
import { useAuthStore } from '@/stores/auth'
import { toast } from '@/composables/toast'
import { LOGIN_TYPE_TAGS, SESSION_STATUS_TAGS } from '@/constants'
import { formatDateTime } from '@/utils/format'
import type { LoginSessionVO } from '@/types'
import StatusTag from '@/components/StatusTag.vue'
import PaginationBar from '@/components/PaginationBar.vue'
import ConfirmModal from '@/components/ConfirmModal.vue'
import AppIcon from '@/components/AppIcon.vue'

const auth = useAuthStore()
const router = useRouter()
const canKick = computed(() => auth.hasPerm('system:session:kick'))
const canManage = computed(() => auth.hasPerm('system:session:manage'))
const colSpan = computed(() => (canManage.value ? 8 : 7))

const filters = reactive({
  userName: '',
})
const pageNum = ref(1)
const pageSize = ref(10)
const total = ref(0)
const rows = ref<LoginSessionVO[]>([])
const loading = ref(false)

const expandedUserIds = ref<Record<string, boolean>>({})
const historyMap = ref<Record<string, LoginSessionVO[]>>({})
const historyLoading = ref<Record<string, boolean>>({})

async function load() {
  loading.value = true
  try {
    const data = await listSessions({
      userName: canManage.value && filters.userName.trim() ? filters.userName.trim() : undefined,
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
  expandedUserIds.value = {}
  historyMap.value = {}
  load()
}

function resetFilters() {
  filters.userName = ''
  search()
}

function changePage(p: number) {
  pageNum.value = p
  expandedUserIds.value = {}
  historyMap.value = {}
  load()
}

function userKey(userId: LoginSessionVO['userId']) {
  return String(userId)
}

function isExpanded(userId: LoginSessionVO['userId']) {
  return !!expandedUserIds.value[userKey(userId)]
}

function expandedHistory(row: LoginSessionVO): LoginSessionVO[] {
  const items = historyMap.value[userKey(row.userId)] ?? []
  return items.filter((item) => !item.current && item.sessionId !== row.sessionId)
}

async function toggleHistory(row: LoginSessionVO) {
  const key = userKey(row.userId)
  if (isExpanded(row.userId)) {
    expandedUserIds.value = Object.fromEntries(
      Object.entries(expandedUserIds.value).filter(([id]) => id !== key),
    )
    return
  }
  expandedUserIds.value = { ...expandedUserIds.value, [key]: true }
  if (historyMap.value[key]) {
    return
  }
  historyLoading.value = { ...historyLoading.value, [key]: true }
  try {
    historyMap.value = { ...historyMap.value, [key]: await listSessionHistory(row.userId) }
  } finally {
    historyLoading.value = { ...historyLoading.value, [key]: false }
  }
}

async function refreshHistory(userId: LoginSessionVO['userId']) {
  const key = userKey(userId)
  historyLoading.value = { ...historyLoading.value, [key]: true }
  try {
    historyMap.value = { ...historyMap.value, [key]: await listSessionHistory(userId) }
  } finally {
    historyLoading.value = { ...historyLoading.value, [key]: false }
  }
}

onMounted(load)

const kickTarget = ref<LoginSessionVO | null>(null)
const kicking = ref(false)

async function confirmKick() {
  if (!kickTarget.value) return
  const kickedUserId = kickTarget.value.userId
  kicking.value = true
  try {
    await kickSession(kickTarget.value.sessionId)
    toast.success('已踢出该设备')
    if (kickTarget.value.current) {
      kickTarget.value = null
      await auth.logout()
      router.push('/login')
      return
    }
    kickTarget.value = null
    await load()
    if (expandedUserIds.value[userKey(kickedUserId)]) {
      await refreshHistory(kickedUserId)
    }
  } catch {
    // 拦截器已提示
  } finally {
    kicking.value = false
  }
}
</script>

<template>
  <div class="space-y-4">
    <PageHeader title="登录设备管理" desc="所有账号仅允许单点登录，新登录会自动下线其他设备；列表按用户汇总，展开可查看历史登录记录">
      <button class="btn-ghost" :disabled="loading" @click="load">
        <AppIcon name="refresh" class="!text-[18px]" />
        刷新
      </button>
    </PageHeader>

    <div v-if="canManage" class="card p-4">
      <div class="grid grid-cols-2 gap-3 md:grid-cols-4 xl:grid-cols-5">
        <div>
          <label class="form-label">用户名</label>
          <input
            v-model="filters.userName"
            class="input"
            placeholder="搜索用户名…"
            @keyup.enter="search"
          />
        </div>
        <div class="flex items-end gap-2">
          <button class="btn-primary" @click="search">查询</button>
          <button class="btn-ghost" @click="resetFilters">重置</button>
        </div>
      </div>
    </div>

    <div class="card overflow-hidden">
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="bg-gray-50 text-left text-xs font-medium text-ink-muted">
              <th class="w-10 px-2 py-2.5"></th>
              <th v-if="canManage" class="px-4 py-2.5">用户名</th>
              <th class="px-4 py-2.5">设备名称</th>
              <th class="px-4 py-2.5">IP</th>
              <th class="px-4 py-2.5">登录时间</th>
              <th class="px-4 py-2.5">登录方式</th>
              <th class="px-4 py-2.5">状态</th>
              <th class="px-4 py-2.5 text-right">操作</th>
            </tr>
          </thead>
          <tbody>
            <template v-for="row in rows" :key="row.userId">
              <tr class="border-b border-line transition-colors hover:bg-gray-50">
                <td class="px-2 py-3 text-center">
                  <button
                    type="button"
                    class="inline-flex h-7 w-7 items-center justify-center rounded-md text-ink-muted transition-colors hover:bg-gray-100 hover:text-ink"
                    :title="isExpanded(row.userId) ? '收起历史记录' : '展开历史记录'"
                    @click.stop="toggleHistory(row)"
                  >
                    <AppIcon
                      name="chevron_right"
                      class="!text-[18px] transition-transform"
                      :class="{ 'rotate-90': isExpanded(row.userId) }"
                    />
                  </button>
                </td>
                <td v-if="canManage" class="px-4 py-3 font-medium">{{ row.userName || row.userId }}</td>
                <td class="px-4 py-3">
                  <div class="flex items-center gap-2">
                    <span>{{ row.deviceName || '-' }}</span>
                    <span
                      v-if="row.current"
                      class="rounded border border-primary/30 bg-primary-light px-1.5 py-0.5 text-[11px] font-medium text-primary"
                    >
                      本机
                    </span>
                  </div>
                </td>
                <td class="px-4 py-3 font-mono text-[13px] text-ink-muted">{{ row.loginIp || '-' }}</td>
                <td class="px-4 py-3 font-mono text-[13px] text-ink-muted">
                  {{ row.loginTime ? formatDateTime(row.loginTime) : '-' }}
                </td>
                <td class="px-4 py-3">
                  <StatusTag :value="row.loginType ?? '0'" :map="LOGIN_TYPE_TAGS" />
                </td>
                <td class="px-4 py-3">
                  <StatusTag :value="row.status" :map="SESSION_STATUS_TAGS" />
                </td>
                <td class="px-4 py-3 text-right">
                  <button
                    v-if="canKick && row.status === '0' && !row.current"
                    class="text-sm font-medium text-danger hover:underline"
                    @click="kickTarget = row"
                  >
                    踢出
                  </button>
                  <span v-else-if="row.current" class="text-xs text-ink-faint">当前设备</span>
                  <span v-else class="text-xs text-ink-faint">-</span>
                </td>
              </tr>
              <tr v-if="isExpanded(row.userId) && historyLoading[userKey(row.userId)]" class="session-history-row border-b border-line">
                <td class="px-2 py-3"></td>
                <td :colspan="colSpan - 1" class="px-4 py-3 text-sm text-ink-faint">加载中…</td>
              </tr>
              <template v-if="isExpanded(row.userId)">
                <tr
                  v-for="item in expandedHistory(row)"
                  :key="item.sessionId"
                  class="session-history-row border-b border-line transition-colors"
                >
                  <td class="px-2 py-3"></td>
                  <td v-if="canManage" class="px-4 py-3"></td>
                  <td class="px-4 py-3">
                    <span>{{ item.deviceName || '-' }}</span>
                  </td>
                  <td class="px-4 py-3 font-mono text-[13px] text-ink-muted">{{ item.loginIp || '-' }}</td>
                  <td class="px-4 py-3 font-mono text-[13px] text-ink-muted">
                    {{ item.loginTime ? formatDateTime(item.loginTime) : '-' }}
                  </td>
                  <td class="px-4 py-3">
                    <StatusTag :value="item.loginType ?? '0'" :map="LOGIN_TYPE_TAGS" />
                  </td>
                  <td class="px-4 py-3">
                    <StatusTag :value="item.status" :map="SESSION_STATUS_TAGS" />
                  </td>
                  <td class="px-4 py-3 text-right">
                    <button
                      v-if="canKick && item.status === '0'"
                      class="text-sm font-medium text-danger hover:underline"
                      @click="kickTarget = item"
                    >
                      踢出
                    </button>
                    <span v-else class="text-xs text-ink-faint">-</span>
                  </td>
                </tr>
              </template>
              <tr
                v-if="isExpanded(row.userId) && !historyLoading[userKey(row.userId)] && expandedHistory(row).length === 0"
                class="session-history-row border-b border-line"
              >
                <td class="px-2 py-3"></td>
                <td :colspan="colSpan - 1" class="px-4 py-3 text-sm text-ink-faint">暂无历史登录记录</td>
              </tr>
            </template>
            <tr v-if="!loading && rows.length === 0">
              <td :colspan="colSpan" class="px-4 py-16 text-center text-ink-faint">
                暂无登录设备记录
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <PaginationBar :total="total" :page-num="pageNum" :page-size="pageSize" @change="changePage" />
    </div>

    <ConfirmModal
      :open="!!kickTarget"
      title="踢出登录设备"
      :message="`确定要踢出设备「${kickTarget?.deviceName || kickTarget?.loginIp}」吗？该设备上的会话将立即失效。`"
      :loading="kicking"
      danger
      @close="kickTarget = null"
      @confirm="confirmKick"
    />
  </div>
</template>
