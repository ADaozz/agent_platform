<script setup lang="ts">
import PageHeader from '@/components/PageHeader.vue'
import { computed, nextTick, onMounted, reactive, ref } from 'vue'
import {
  approveCertApply,
  listCertApplies,
  listUserCerts,
  rejectCertApply,
  revokeCert,
} from '@/api/cert'
import { useAuthStore } from '@/stores/auth'
import { toast } from '@/composables/toast'
import { tr } from '@/composables/preferences'
import {
  CERT_APPLY_STATUS_TAGS,
  CERT_STATUS_TAGS,
  CERT_TYPE_LABELS,
} from '@/constants'
import { formatDateTime } from '@/utils/format'
import type { CertApplyVO, Id, UserCertVO } from '@/types'
import StatusTag from '@/components/StatusTag.vue'
import PaginationBar from '@/components/PaginationBar.vue'
import BaseModal from '@/components/BaseModal.vue'
import ConfirmModal from '@/components/ConfirmModal.vue'
import AppIcon from '@/components/AppIcon.vue'

interface UserCertGroup {
  userId: Id
  userName: string
  signCert: UserCertVO | null
  encryptCert: UserCertVO | null
}

const auth = useAuthStore()
const canApprove = computed(() => auth.hasPerm('system:cert:approve'))
const canRevoke = computed(() => auth.hasPerm('system:cert:revoke'))

const tab = ref<'cert' | 'apply'>('cert')

const certFilters = reactive({ userName: '', certType: '', status: '' })
const certPageNum = ref(1)
const certPageSize = ref(10)
const certTotal = ref(0)
const certRows = ref<UserCertVO[]>([])
const certLoading = ref(false)
const expandedUserIds = ref<Record<string, boolean>>({})

const applyFilters = reactive({ userName: '', status: 'pending' })
const applyPageNum = ref(1)
const applyPageSize = ref(10)
const applyTotal = ref(0)
const applyRows = ref<CertApplyVO[]>([])
const applyLoading = ref(false)

const certUserGroups = computed(() => {
  const map = new Map<string, UserCertGroup>()
  for (const row of certRows.value) {
    const key = String(row.userId)
    let group = map.get(key)
    if (!group) {
      group = {
        userId: row.userId,
        userName: row.userName || String(row.userId),
        signCert: null,
        encryptCert: null,
      }
      map.set(key, group)
    }
    if (row.certType === 'sign') {
      group.signCert = pickPreferredCert(group.signCert, row)
    } else if (row.certType === 'encrypt') {
      group.encryptCert = pickPreferredCert(group.encryptCert, row)
    }
  }
  return [...map.values()].sort((a, b) => a.userName.localeCompare(b.userName, 'zh-CN'))
})

/** 同一用户同类型多张证时：优先有效证，其次按创建时间取最新 */
function pickPreferredCert(current: UserCertVO | null, candidate: UserCertVO): UserCertVO {
  if (!current) return candidate
  if (current.status !== candidate.status) {
    return candidate.status === '0' ? candidate : current
  }
  const currentTime = current.createTime ? new Date(current.createTime).getTime() : 0
  const candidateTime = candidate.createTime ? new Date(candidate.createTime).getTime() : 0
  return candidateTime >= currentTime ? candidate : current
}

async function loadCerts() {
  certLoading.value = true
  try {
    const data = await listUserCerts({
      userName: certFilters.userName.trim() || undefined,
      certType: certFilters.certType || undefined,
      status: certFilters.status || undefined,
      pageNum: certPageNum.value,
      pageSize: certPageSize.value,
    })
    certRows.value = data.rows
    certTotal.value = data.total
  } finally {
    certLoading.value = false
  }
}

async function loadApplies() {
  applyLoading.value = true
  try {
    const data = await listCertApplies({
      userName: applyFilters.userName.trim() || undefined,
      status: applyFilters.status || undefined,
      pageNum: applyPageNum.value,
      pageSize: applyPageSize.value,
    })
    applyRows.value = data.rows
    applyTotal.value = data.total
  } finally {
    applyLoading.value = false
  }
}

function loadActive() {
  if (tab.value === 'cert') loadCerts()
  else loadApplies()
}

onMounted(loadActive)

function switchTab(next: 'cert' | 'apply') {
  if (tab.value === next) return
  tab.value = next
  loadActive()
}

const certTab = ref<HTMLButtonElement>()
const applyTab = ref<HTMLButtonElement>()

/** 键盘切换时把焦点移到新选中的页签，保持 roving tabindex 语义 */
async function focusTab(next: 'cert' | 'apply') {
  switchTab(next)
  await nextTick()
  ;(next === 'cert' ? certTab : applyTab).value?.focus()
}

function userKey(userId: Id) {
  return String(userId)
}

function isExpanded(userId: Id) {
  return !!expandedUserIds.value[userKey(userId)]
}

function toggleExpand(userId: Id) {
  const key = userKey(userId)
  if (isExpanded(userId)) {
    expandedUserIds.value = Object.fromEntries(
      Object.entries(expandedUserIds.value).filter(([id]) => id !== key),
    )
    return
  }
  expandedUserIds.value = { ...expandedUserIds.value, [key]: true }
}

function searchCerts() {
  certPageNum.value = 1
  expandedUserIds.value = {}
  loadCerts()
}

function changeCertPage(p: number) {
  certPageNum.value = p
  expandedUserIds.value = {}
  loadCerts()
}

function groupStatusSummary(group: UserCertGroup) {
  const certs = [group.signCert, group.encryptCert].filter(Boolean) as UserCertVO[]
  if (certs.length === 0) return '-'
  if (certs.every((c) => c.status === '0')) return tr('全部有效')
  if (certs.every((c) => c.status === '1')) return tr('全部吊销')
  return tr('部分有效')
}

function latestNotAfter(group: UserCertGroup) {
  const dates = [group.signCert?.notAfter, group.encryptCert?.notAfter].filter(Boolean) as string[]
  if (dates.length === 0) return null
  return dates.sort((a, b) => new Date(b).getTime() - new Date(a).getTime())[0]
}

const approveTarget = ref<CertApplyVO | null>(null)
const approveForm = reactive({
  subjectCn: '',
  subjectO: 'personalDemo',
  subjectOu: '',
  validDays: 365,
})
const approving = ref(false)

function openApprove(row: CertApplyVO) {
  approveTarget.value = row
  approveForm.subjectCn = row.userName || ''
  approveForm.subjectO = 'personalDemo'
  approveForm.subjectOu = `user-${row.userId}`
  approveForm.validDays = 365
}

async function confirmApprove() {
  if (!approveTarget.value) return
  approving.value = true
  try {
    const result = await approveCertApply(approveTarget.value.applyId, { ...approveForm })
    approveTarget.value = null
    toast.success(result.message || tr('签发成功，请通知用户在「我的证书」查看 P12 密码'))
    await loadApplies()
    await loadCerts()
    expandedUserIds.value = {}
  } finally {
    approving.value = false
  }
}

function closeApproveModal() {
  approveTarget.value = null
}

const rejectTarget = ref<CertApplyVO | null>(null)
const rejecting = ref(false)

async function confirmReject() {
  if (!rejectTarget.value) return
  rejecting.value = true
  try {
    await rejectCertApply(rejectTarget.value.applyId, '管理员拒绝')
    toast.success(tr('已拒绝'))
    rejectTarget.value = null
    await loadApplies()
  } finally {
    rejecting.value = false
  }
}

const revokeTarget = ref<UserCertVO | null>(null)
const revoking = ref(false)

async function confirmRevoke() {
  if (!revokeTarget.value) return
  revoking.value = true
  try {
    await revokeCert(revokeTarget.value.certId)
    toast.success(tr('证书已吊销'))
    revokeTarget.value = null
    await loadCerts()
  } finally {
    revoking.value = false
  }
}
</script>

<template>
  <div class="space-y-4">
    <PageHeader :title="tr('证书管理')" />
    <div class="filter-toolbar cert-toolbar">
      <div class="segmented" role="tablist" :aria-label="tr('证书管理范围')">
        <button
          id="cert-tab-list"
          ref="certTab"
          type="button"
          role="tab"
          aria-controls="cert-panel-list"
          :aria-selected="tab === 'cert'"
          :tabindex="tab === 'cert' ? 0 : -1"
          @click="switchTab('cert')"
          @keydown.right.prevent="focusTab('apply')"
          @keydown.home.prevent="focusTab('cert')"
        >
          {{ tr('证书列表') }}
        </button>
        <button
          id="cert-tab-apply"
          ref="applyTab"
          type="button"
          role="tab"
          aria-controls="cert-panel-apply"
          :aria-selected="tab === 'apply'"
          :tabindex="tab === 'apply' ? 0 : -1"
          @click="switchTab('apply')"
          @keydown.left.prevent="focusTab('cert')"
          @keydown.end.prevent="focusTab('apply')"
        >
          {{ tr('申请审批') }}
        </button>
      </div>
      <button class="btn-ghost" @click="loadActive">
        <AppIcon name="refresh" class="!text-[18px]" />
        {{ tr('刷新') }}
      </button>
    </div>

    <div
      v-show="tab === 'cert'"
      id="cert-panel-list"
      role="tabpanel"
      aria-labelledby="cert-tab-list"
      class="space-y-4"
    >
      <div class="card p-4">
        <div class="grid grid-cols-2 gap-3 md:grid-cols-5">
          <div>
            <label class="form-label" for="cert-filter-name">{{ tr('用户名') }}</label>
            <input
              id="cert-filter-name"
              v-model="certFilters.userName"
              class="input"
              @keyup.enter="searchCerts"
            />
          </div>
          <div>
            <label class="form-label" for="cert-filter-type">{{ tr('类型') }}</label>
            <select id="cert-filter-type" v-model="certFilters.certType" class="select">
              <option value="">{{ tr('全部') }}</option>
              <option value="sign">{{ tr('签名') }}</option>
              <option value="encrypt">{{ tr('加密') }}</option>
            </select>
          </div>
          <div>
            <label class="form-label" for="cert-filter-status">{{ tr('状态') }}</label>
            <select id="cert-filter-status" v-model="certFilters.status" class="select">
              <option value="">{{ tr('全部') }}</option>
              <option value="0">{{ tr('有效') }}</option>
              <option value="1">{{ tr('已吊销') }}</option>
            </select>
          </div>
          <div class="flex items-end">
            <button class="btn-primary" @click="searchCerts">{{ tr('查询') }}</button>
          </div>
        </div>
      </div>
      <div class="card overflow-hidden">
        <div class="table-scroll">
          <table>
            <thead>
              <tr>
                <th class="w-10"><span class="sr-only">{{ tr('展开证书详情') }}</span></th>
                <th>{{ tr('用户名') }}</th>
                <th>{{ tr('签名证') }}</th>
                <th>{{ tr('加密证') }}</th>
                <th>{{ tr('整体状态') }}</th>
                <th>{{ tr('最近有效期至') }}</th>
              </tr>
            </thead>
            <tbody>
              <template v-for="group in certUserGroups" :key="group.userId">
                <tr>
                  <td class="text-center">
                    <button
                      type="button"
                      class="inline-flex h-7 w-7 items-center justify-center rounded-md text-ink-muted transition-colors hover:bg-gray-100 hover:text-ink"
                      :title="isExpanded(group.userId) ? tr('收起证书详情') : tr('展开证书详情')"
                      @click.stop="toggleExpand(group.userId)"
                    >
                      <AppIcon
                        name="chevron_right"
                        class="!text-[18px] transition-transform"
                        :class="{ 'rotate-90': isExpanded(group.userId) }"
                      />
                    </button>
                  </td>
                  <td>{{ group.userName }}</td>
                  <td>
                    <StatusTag
                      v-if="group.signCert"
                      :value="group.signCert.status"
                      :map="CERT_STATUS_TAGS"
                    />
                    <span v-else class="text-xs text-ink-faint">{{ tr('无') }}</span>
                  </td>
                  <td>
                    <StatusTag
                      v-if="group.encryptCert"
                      :value="group.encryptCert.status"
                      :map="CERT_STATUS_TAGS"
                    />
                    <span v-else class="text-xs text-ink-faint">{{ tr('无') }}</span>
                  </td>
                  <td class="text-ink-secondary">{{ groupStatusSummary(group) }}</td>
                  <td class="font-mono text-[13px]">
                    {{ latestNotAfter(group) ? formatDateTime(latestNotAfter(group)!) : '-' }}
                  </td>
                </tr>
                <tr v-if="isExpanded(group.userId)" class="session-history-row border-b border-line">
                  <td></td>
                  <td colspan="5" class="cert-expand-cell">
                    <div class="cert-expand-grid">
                      <div
                        v-for="slot in [
                          { type: 'sign', cert: group.signCert },
                          { type: 'encrypt', cert: group.encryptCert },
                        ]"
                        :key="slot.type"
                        class="card cert-detail-card p-4"
                      >
                        <div class="mb-3 flex min-w-0 items-center justify-between gap-2">
                          <h3 class="truncate text-sm font-medium text-ink">
                            {{ tr(CERT_TYPE_LABELS[slot.type] || slot.type) }}
                          </h3>
                          <button
                            v-if="canRevoke && slot.cert && slot.cert.status === '0'"
                            class="shrink-0 text-xs font-medium text-danger hover:underline"
                            @click="revokeTarget = slot.cert"
                          >
                            {{ tr('吊销') }}
                          </button>
                        </div>
                        <template v-if="slot.cert">
                          <dl class="cert-detail-list">
                            <div class="cert-detail-row">
                              <dt>{{ tr('序列号') }}</dt>
                              <dd class="font-mono" :title="slot.cert.certSerial">{{ slot.cert.certSerial }}</dd>
                            </div>
                            <div class="cert-detail-row">
                              <dt>{{ tr('主体') }}</dt>
                              <dd :title="slot.cert.subjectDn">{{ slot.cert.subjectDn }}</dd>
                            </div>
                            <div class="cert-detail-row">
                              <dt>{{ tr('有效期至') }}</dt>
                              <dd>{{ slot.cert.notAfter ? formatDateTime(slot.cert.notAfter) : '-' }}</dd>
                            </div>
                            <div class="cert-detail-row">
                              <dt>{{ tr('状态') }}</dt>
                              <dd><StatusTag :value="slot.cert.status" :map="CERT_STATUS_TAGS" /></dd>
                            </div>
                          </dl>
                        </template>
                        <p v-else class="text-sm text-ink-faint">{{ tr('暂无{name}', { name: tr(CERT_TYPE_LABELS[slot.type] || slot.type) }) }}</p>
                      </div>
                    </div>
                  </td>
                </tr>
              </template>
              <tr v-if="!certLoading && certUserGroups.length === 0">
                <td colspan="6" class="table-empty">{{ tr('暂无证书记录') }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <PaginationBar
          :total="certTotal"
          :page-num="certPageNum"
          :page-size="certPageSize"
          @change="changeCertPage"
        />
      </div>
    </div>

    <div
      v-show="tab === 'apply'"
      id="cert-panel-apply"
      role="tabpanel"
      aria-labelledby="cert-tab-apply"
      class="space-y-4"
    >
      <div class="card p-4">
        <div class="grid grid-cols-2 gap-3 md:grid-cols-4">
          <div>
            <label class="form-label" for="apply-filter-name">{{ tr('用户名') }}</label>
            <input
              id="apply-filter-name"
              v-model="applyFilters.userName"
              class="input"
              :placeholder="tr('搜索…')"
              @keyup.enter="applyPageNum = 1; loadApplies()"
            />
          </div>
          <div>
            <label class="form-label" for="apply-filter-status">{{ tr('状态') }}</label>
            <select id="apply-filter-status" v-model="applyFilters.status" class="select">
              <option value="">{{ tr('全部') }}</option>
              <option value="pending">{{ tr('待审批') }}</option>
              <option value="approved">{{ tr('已通过') }}</option>
              <option value="rejected">{{ tr('已拒绝') }}</option>
            </select>
          </div>
          <div class="flex items-end">
            <button class="btn-primary" @click="applyPageNum = 1; loadApplies()">{{ tr('查询') }}</button>
          </div>
        </div>
      </div>
      <div class="card overflow-hidden">
        <table>
          <thead>
            <tr>
              <th>{{ tr('用户') }}</th>
              <th>{{ tr('类型') }}</th>
              <th>{{ tr('状态') }}</th>
              <th>{{ tr('申请时间') }}</th>
              <th class="col-end">{{ tr('操作') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in applyRows" :key="row.applyId" class="border-b border-line last:border-0">
              <td>{{ row.userName }}</td>
              <td>{{ row.applyType === 'reissue' ? tr('重发') : tr('新申请') }}</td>
              <td><StatusTag :value="row.status" :map="CERT_APPLY_STATUS_TAGS" /></td>
              <td class="font-mono text-[13px]">{{ row.createTime ? formatDateTime(row.createTime) : '-' }}</td>
              <td class="col-end space-x-2">
                <template v-if="canApprove && row.status === 'pending'">
                  <button class="text-sm font-medium text-primary hover:underline" @click="openApprove(row)">{{ tr('审批') }}</button>
                  <button class="text-sm font-medium text-danger hover:underline" @click="rejectTarget = row">{{ tr('拒绝') }}</button>
                </template>
                <span v-else class="text-xs text-ink-faint">-</span>
              </td>
            </tr>
          </tbody>
        </table>
        <PaginationBar :total="applyTotal" :page-num="applyPageNum" :page-size="applyPageSize" @change="(p) => { applyPageNum = p; loadApplies() }" />
      </div>
    </div>

    <BaseModal :open="!!approveTarget" :title="tr('审批并签发证书')" @close="closeApproveModal">
      <form class="space-y-3" @submit.prevent="confirmApprove">
        <div>
          <label class="form-label">{{ tr('主体 CN') }}</label>
          <input v-model="approveForm.subjectCn" class="input" required />
        </div>
        <div>
          <label class="form-label">{{ tr('组织 O') }}</label>
          <input v-model="approveForm.subjectO" class="input" />
        </div>
        <div>
          <label class="form-label">{{ tr('部门 OU') }}</label>
          <input v-model="approveForm.subjectOu" class="input" />
        </div>
        <div>
          <label class="form-label">{{ tr('有效期（天）') }}</label>
          <input v-model.number="approveForm.validDays" class="input" type="number" min="1" max="3650" required />
        </div>
        <p class="text-xs text-ink-faint">{{ tr('签发后 P12 密码仅申请人可在「我的证书」查看一次，管理员不可见。') }}</p>
        <div class="flex justify-end gap-2 pt-2">
          <button type="button" class="btn-ghost" @click="closeApproveModal">{{ tr('取消') }}</button>
          <button type="submit" class="btn-primary" :disabled="approving">{{ tr('签发') }}</button>
        </div>
      </form>
    </BaseModal>

    <ConfirmModal
      :open="!!rejectTarget"
      :title="tr('拒绝申请')"
      :message="tr('确定拒绝该证书申请吗？')"
      :loading="rejecting"
      danger
      @close="rejectTarget = null"
      @confirm="confirmReject"
    />

    <ConfirmModal
      :open="!!revokeTarget"
      :title="tr('吊销证书')"
      :message="tr('确定吊销「{name}」的{type}吗？', { name: revokeTarget?.userName || '', type: tr(CERT_TYPE_LABELS[revokeTarget?.certType || ''] || revokeTarget?.certType || '') })"
      :loading="revoking"
      danger
      @close="revokeTarget = null"
      @confirm="confirmRevoke"
    />
  </div>
</template>

<style scoped>
.cert-toolbar {
  justify-content: space-between;
  padding: 0;
  border-bottom: 0;
}
.cert-toolbar .segmented {
  flex: 0 1 auto;
  min-width: 0;
}
/* 展开区不受表格 nowrap 影响，手机端与「我的证书」同一套详情卡 */
.cert-expand-cell {
  white-space: normal !important;
  min-width: 0;
  max-width: 0; /* 强制吃掉表格列宽算法，让内容按视口收缩 */
  width: 100%;
  padding: 14px 16px;
  vertical-align: top;
}
.cert-expand-grid {
  display: grid;
  gap: 1rem;
  min-width: 0;
}
@media (min-width: 768px) {
  .cert-expand-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .cert-expand-cell {
    max-width: none;
  }
}
.cert-detail-card {
  min-width: 0;
  overflow: hidden;
}
.cert-detail-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  font-size: 0.875rem;
}
.cert-detail-row {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 1rem;
  min-width: 0;
}
.cert-detail-row dt {
  flex: 0 0 auto;
  color: var(--color-ink-muted);
}
.cert-detail-row dd {
  flex: 1 1 auto;
  min-width: 0;
  text-align: right;
  font-size: 0.75rem;
  color: var(--color-ink-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
