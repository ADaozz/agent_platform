<script setup lang="ts">
import PageHeader from '@/components/PageHeader.vue'
import { computed, onMounted, reactive, ref } from 'vue'
import {
  approveCertApply,
  listCertApplies,
  listUserCerts,
  rejectCertApply,
  revokeCert,
} from '@/api/cert'
import { useAuthStore } from '@/stores/auth'
import { toast } from '@/composables/toast'
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
  tab.value = next
  loadActive()
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
  if (certs.every((c) => c.status === '0')) return '全部有效'
  if (certs.every((c) => c.status === '1')) return '全部吊销'
  return '部分有效'
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
const approveResultPassword = ref('')

function openApprove(row: CertApplyVO) {
  approveTarget.value = row
  approveForm.subjectCn = row.userName || ''
  approveForm.subjectO = 'personalDemo'
  approveForm.subjectOu = `user-${row.userId}`
  approveForm.validDays = 365
  approveResultPassword.value = ''
}

async function confirmApprove() {
  if (!approveTarget.value) return
  approving.value = true
  try {
    const result = await approveCertApply(approveTarget.value.applyId, { ...approveForm })
    approveResultPassword.value = result.p12Password
    toast.success(result.message)
    await loadApplies()
    await loadCerts()
    expandedUserIds.value = {}
  } finally {
    approving.value = false
  }
}

async function copyApprovePassword() {
  if (!approveResultPassword.value) return
  try {
    await navigator.clipboard.writeText(approveResultPassword.value)
    toast.success('已复制到剪贴板')
  } catch {
    toast.error('复制失败，请手动复制')
  }
}

function closeApproveModal() {
  approveTarget.value = null
  approveResultPassword.value = ''
}

function closeApproveSuccess() {
  approveResultPassword.value = ''
  approveTarget.value = null
}

const rejectTarget = ref<CertApplyVO | null>(null)
const rejecting = ref(false)

async function confirmReject() {
  if (!rejectTarget.value) return
  rejecting.value = true
  try {
    await rejectCertApply(rejectTarget.value.applyId, '管理员拒绝')
    toast.success('已拒绝')
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
    toast.success('证书已吊销')
    revokeTarget.value = null
    await loadCerts()
  } finally {
    revoking.value = false
  }
}
</script>

<template>
  <div class="space-y-4">
    <PageHeader title="证书管理" desc="审批证书申请、查询与吊销已签发证书">
      <button class="btn-ghost" @click="loadActive">
        <AppIcon name="refresh" class="!text-[18px]" />
        刷新
      </button>
    </PageHeader>

    <div class="flex gap-2 border-b border-line">
      <button
        class="border-b-2 px-4 py-2 text-sm font-medium transition-colors"
        :class="tab === 'cert' ? 'border-primary text-primary' : 'border-transparent text-ink-muted'"
        @click="switchTab('cert')"
      >
        证书列表
      </button>
      <button
        class="border-b-2 px-4 py-2 text-sm font-medium transition-colors"
        :class="tab === 'apply' ? 'border-primary text-primary' : 'border-transparent text-ink-muted'"
        @click="switchTab('apply')"
      >
        申请审批
      </button>
    </div>

    <div v-show="tab === 'cert'" class="space-y-4">
      <div class="card p-4">
        <div class="grid grid-cols-2 gap-3 md:grid-cols-5">
          <div>
            <label class="form-label">用户名</label>
            <input v-model="certFilters.userName" class="input" @keyup.enter="searchCerts" />
          </div>
          <div>
            <label class="form-label">类型</label>
            <select v-model="certFilters.certType" class="select">
              <option value="">全部</option>
              <option value="sign">签名</option>
              <option value="encrypt">加密</option>
            </select>
          </div>
          <div>
            <label class="form-label">状态</label>
            <select v-model="certFilters.status" class="select">
              <option value="">全部</option>
              <option value="0">有效</option>
              <option value="1">已吊销</option>
            </select>
          </div>
          <div class="flex items-end">
            <button class="btn-primary" @click="searchCerts">查询</button>
          </div>
        </div>
      </div>
      <div class="card overflow-hidden">
        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="bg-gray-50 text-left text-xs font-medium text-ink-muted">
                <th class="w-10 px-2 py-2.5"></th>
                <th class="px-4 py-2.5">用户名</th>
                <th class="px-4 py-2.5">签名证</th>
                <th class="px-4 py-2.5">加密证</th>
                <th class="px-4 py-2.5">整体状态</th>
                <th class="px-4 py-2.5">最近有效期至</th>
              </tr>
            </thead>
            <tbody>
              <template v-for="group in certUserGroups" :key="group.userId">
                <tr class="border-b border-line transition-colors hover:bg-gray-50">
                  <td class="px-2 py-3 text-center">
                    <button
                      type="button"
                      class="inline-flex h-7 w-7 items-center justify-center rounded-md text-ink-muted transition-colors hover:bg-gray-100 hover:text-ink"
                      :title="isExpanded(group.userId) ? '收起证书详情' : '展开证书详情'"
                      @click.stop="toggleExpand(group.userId)"
                    >
                      <AppIcon
                        name="chevron_right"
                        class="!text-[18px] transition-transform"
                        :class="{ 'rotate-90': isExpanded(group.userId) }"
                      />
                    </button>
                  </td>
                  <td class="px-4 py-3 font-medium">{{ group.userName }}</td>
                  <td class="px-4 py-3">
                    <StatusTag
                      v-if="group.signCert"
                      :value="group.signCert.status"
                      :map="CERT_STATUS_TAGS"
                    />
                    <span v-else class="text-xs text-ink-faint">无</span>
                  </td>
                  <td class="px-4 py-3">
                    <StatusTag
                      v-if="group.encryptCert"
                      :value="group.encryptCert.status"
                      :map="CERT_STATUS_TAGS"
                    />
                    <span v-else class="text-xs text-ink-faint">无</span>
                  </td>
                  <td class="px-4 py-3 text-ink-secondary">{{ groupStatusSummary(group) }}</td>
                  <td class="px-4 py-3 font-mono text-[13px] text-ink-muted">
                    {{ latestNotAfter(group) ? formatDateTime(latestNotAfter(group)!) : '-' }}
                  </td>
                </tr>
                <tr v-if="isExpanded(group.userId)" class="session-history-row border-b border-line">
                  <td class="px-2 py-3"></td>
                  <td colspan="5" class="px-4 py-4">
                    <div class="grid gap-4 md:grid-cols-2">
                      <div
                        v-for="slot in [
                          { type: 'sign', cert: group.signCert },
                          { type: 'encrypt', cert: group.encryptCert },
                        ]"
                        :key="slot.type"
                        class="rounded-lg border border-line bg-white p-4"
                      >
                        <div class="mb-3 flex items-center justify-between gap-2">
                          <h3 class="text-sm font-medium text-ink">
                            {{ CERT_TYPE_LABELS[slot.type] }}
                          </h3>
                          <button
                            v-if="canRevoke && slot.cert && slot.cert.status === '0'"
                            class="text-xs font-medium text-danger hover:underline"
                            @click="revokeTarget = slot.cert"
                          >
                            吊销
                          </button>
                        </div>
                        <template v-if="slot.cert">
                          <dl class="space-y-2 text-sm">
                            <div class="flex justify-between gap-4">
                              <dt class="text-ink-muted">序列号</dt>
                              <dd class="font-mono text-xs">{{ slot.cert.certSerial }}</dd>
                            </div>
                            <div class="flex justify-between gap-4">
                              <dt class="text-ink-muted">主体</dt>
                              <dd class="max-w-[60%] text-right text-xs">{{ slot.cert.subjectDn }}</dd>
                            </div>
                            <div class="flex justify-between gap-4">
                              <dt class="text-ink-muted">有效期至</dt>
                              <dd>{{ slot.cert.notAfter ? formatDateTime(slot.cert.notAfter) : '-' }}</dd>
                            </div>
                            <div class="flex justify-between gap-4">
                              <dt class="text-ink-muted">状态</dt>
                              <dd><StatusTag :value="slot.cert.status" :map="CERT_STATUS_TAGS" /></dd>
                            </div>
                          </dl>
                        </template>
                        <p v-else class="text-sm text-ink-faint">暂无{{ CERT_TYPE_LABELS[slot.type] }}</p>
                      </div>
                    </div>
                  </td>
                </tr>
              </template>
              <tr v-if="!certLoading && certUserGroups.length === 0">
                <td colspan="6" class="px-4 py-16 text-center text-ink-faint">暂无证书记录</td>
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

    <div v-show="tab === 'apply'" class="space-y-4">
      <div class="card p-4">
        <div class="grid grid-cols-2 gap-3 md:grid-cols-4">
          <div>
            <label class="form-label">用户名</label>
            <input v-model="applyFilters.userName" class="input" placeholder="搜索…" @keyup.enter="applyPageNum = 1; loadApplies()" />
          </div>
          <div>
            <label class="form-label">状态</label>
            <select v-model="applyFilters.status" class="select">
              <option value="">全部</option>
              <option value="pending">待审批</option>
              <option value="approved">已通过</option>
              <option value="rejected">已拒绝</option>
            </select>
          </div>
          <div class="flex items-end">
            <button class="btn-primary" @click="applyPageNum = 1; loadApplies()">查询</button>
          </div>
        </div>
      </div>
      <div class="card overflow-hidden">
        <table class="w-full text-sm">
          <thead>
            <tr class="bg-gray-50 text-left text-xs font-medium text-ink-muted">
              <th class="px-4 py-2.5">用户</th>
              <th class="px-4 py-2.5">类型</th>
              <th class="px-4 py-2.5">状态</th>
              <th class="px-4 py-2.5">申请时间</th>
              <th class="px-4 py-2.5 text-right">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in applyRows" :key="row.applyId" class="border-b border-line last:border-0">
              <td class="px-4 py-3 font-medium">{{ row.userName }}</td>
              <td class="px-4 py-3">{{ row.applyType === 'reissue' ? '重发' : '新申请' }}</td>
              <td class="px-4 py-3"><StatusTag :value="row.status" :map="CERT_APPLY_STATUS_TAGS" /></td>
              <td class="px-4 py-3 font-mono text-[13px]">{{ row.createTime ? formatDateTime(row.createTime) : '-' }}</td>
              <td class="px-4 py-3 text-right space-x-2">
                <template v-if="canApprove && row.status === 'pending'">
                  <button class="text-sm font-medium text-primary hover:underline" @click="openApprove(row)">审批</button>
                  <button class="text-sm font-medium text-danger hover:underline" @click="rejectTarget = row">拒绝</button>
                </template>
                <span v-else class="text-xs text-ink-faint">-</span>
              </td>
            </tr>
          </tbody>
        </table>
        <PaginationBar :total="applyTotal" :page-num="applyPageNum" :page-size="applyPageSize" @change="(p) => { applyPageNum = p; loadApplies() }" />
      </div>
    </div>

    <BaseModal :open="!!approveTarget && !approveResultPassword" title="审批并签发证书" @close="closeApproveModal">
      <form class="space-y-3" @submit.prevent="confirmApprove">
        <div>
          <label class="form-label">主体 CN</label>
          <input v-model="approveForm.subjectCn" class="input" required />
        </div>
        <div>
          <label class="form-label">组织 O</label>
          <input v-model="approveForm.subjectO" class="input" />
        </div>
        <div>
          <label class="form-label">部门 OU</label>
          <input v-model="approveForm.subjectOu" class="input" />
        </div>
        <div>
          <label class="form-label">有效期（天）</label>
          <input v-model.number="approveForm.validDays" class="input" type="number" min="1" max="3650" required />
        </div>
        <div class="flex justify-end gap-2 pt-2">
          <button type="button" class="btn-ghost" @click="closeApproveModal">取消</button>
          <button type="submit" class="btn-primary" :disabled="approving">签发</button>
        </div>
      </form>
    </BaseModal>

    <BaseModal
      :open="!!approveResultPassword"
      title="签发成功"
      width="480px"
      @close="closeApproveSuccess"
    >
      <div class="space-y-4">
        <div class="flex items-start gap-2 rounded-md border border-amber-200 bg-amber-50 px-3 py-2.5 text-sm text-amber-800">
          <AppIcon name="warning" class="!text-[18px] shrink-0" />
          P12 密码仅本次展示，关闭后无法再次查看。证书包内不含密码，请转告用户在本平台「我的证书」页查看。
        </div>
        <div>
          <label class="form-label">P12 密码</label>
          <div class="flex items-center gap-2">
            <input class="input flex-1 font-mono text-[13px]" :value="approveResultPassword" readonly />
            <button class="btn-ghost shrink-0" type="button" @click="copyApprovePassword">复制</button>
          </div>
        </div>
      </div>
      <template #footer>
        <button class="btn-primary" type="button" @click="closeApproveSuccess">我已保存</button>
      </template>
    </BaseModal>

    <ConfirmModal
      :open="!!rejectTarget"
      title="拒绝申请"
      message="确定拒绝该证书申请吗？"
      :loading="rejecting"
      danger
      @close="rejectTarget = null"
      @confirm="confirmReject"
    />

    <ConfirmModal
      :open="!!revokeTarget"
      title="吊销证书"
      :message="`确定吊销「${revokeTarget?.userName}」的${CERT_TYPE_LABELS[revokeTarget?.certType || ''] || ''}吗？`"
      :loading="revoking"
      danger
      @close="revokeTarget = null"
      @confirm="confirmRevoke"
    />
  </div>
</template>
