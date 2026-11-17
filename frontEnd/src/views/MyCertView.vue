<script setup lang="ts">
import PageHeader from '@/components/PageHeader.vue'
import { computed, onMounted, ref } from 'vue'
import {
  applyCert,
  downloadCertBundle,
  getMyCertOverview,
  reissueCert,
  revealCertP12Password,
} from '@/api/cert'
import { toast } from '@/composables/toast'
import { tr } from '@/composables/preferences'
import { CERT_APPLY_STATUS_TAGS, CERT_STATUS_TAGS, CERT_TYPE_LABELS } from '@/constants'
import { formatDateTime } from '@/utils/format'
import type { CertApplyVO, MyCertOverviewVO, UserCertVO } from '@/types'
import StatusTag from '@/components/StatusTag.vue'
import ConfirmModal from '@/components/ConfirmModal.vue'
import BaseModal from '@/components/BaseModal.vue'
import AppIcon from '@/components/AppIcon.vue'

const loading = ref(false)
const overview = ref<MyCertOverviewVO | null>(null)
const applying = ref(false)
const downloading = ref(false)
const reissueConfirmOpen = ref(false)
const revealing = ref(false)
const revealedPassword = ref<string | null>(null)
const revealApply = ref<CertApplyVO | null>(null)
/** 本会话已领取过密码的申请（与后端清库双保险） */
const consumedPasswordApplyIds = ref<Set<string>>(new Set())

const downloadableApply = computed(() =>
  overview.value?.applies?.find((apply) => apply.downloadable) ?? null,
)

const pendingPasswordApply = computed(() =>
  overview.value?.applies?.find(
    (apply) =>
      apply.p12PasswordPending && !consumedPasswordApplyIds.value.has(String(apply.applyId)),
  ) ?? null,
)

async function load() {
  loading.value = true
  try {
    overview.value = await getMyCertOverview()
  } finally {
    loading.value = false
  }
}

onMounted(load)

function certCardTitle(cert: UserCertVO | null, type: string) {
  const certType = cert?.certType || type
  return tr(CERT_TYPE_LABELS[certType] || certType)
}

async function handleApply() {
  applying.value = true
  try {
    await applyCert()
    toast.success(tr('申请已提交'))
    await load()
  } finally {
    applying.value = false
  }
}

async function confirmReissue() {
  applying.value = true
  try {
    await reissueCert('申请重发证书')
    toast.success(tr('重发申请已提交'))
    reissueConfirmOpen.value = false
    await load()
  } finally {
    applying.value = false
  }
}

async function handleDownload() {
  const apply = downloadableApply.value
  if (!apply) return
  downloading.value = true
  try {
    await downloadCertBundle(apply.applyId)
    toast.success(tr('证书包已开始下载'))
  } catch {
    toast.error(tr('下载失败'))
  } finally {
    downloading.value = false
  }
}

async function handleRevealPassword() {
  const apply = pendingPasswordApply.value
  if (!apply) return
  revealing.value = true
  try {
    const result = await revealCertP12Password(apply.applyId)
    consumedPasswordApplyIds.value = new Set([
      ...consumedPasswordApplyIds.value,
      String(apply.applyId),
    ])
    revealedPassword.value = result.p12Password
    revealApply.value = apply
    await load()
  } catch {
    // 拦截器已提示
  } finally {
    revealing.value = false
  }
}

function closePasswordModal() {
  revealedPassword.value = null
  revealApply.value = null
}

async function copyPassword() {
  if (!revealedPassword.value) return
  try {
    await navigator.clipboard.writeText(revealedPassword.value)
    toast.success(tr('已复制到剪贴板'))
  } catch {
    toast.error(tr('复制失败，请手动复制'))
  }
}

const hasPending = () => overview.value?.applies?.some((a) => a.status === 'pending')
</script>

<template>
  <div class="space-y-4">
    <PageHeader :title="tr('我的证书')" />
    <div class="filter-toolbar cert-mine-toolbar">
      <button class="btn-ghost" :disabled="loading" @click="load">
        <AppIcon name="refresh" class="!text-[18px]" />
        {{ tr('刷新') }}
      </button>
      <button
        v-if="pendingPasswordApply"
        class="btn-primary"
        :disabled="revealing"
        @click="handleRevealPassword"
      >
        {{ tr('查看 P12 密码') }}
      </button>
      <button
        v-if="downloadableApply"
        class="btn-ghost"
        :disabled="downloading"
        @click="handleDownload"
      >
        {{ tr('保存证书') }}
      </button>
      <button
        v-if="!hasPending()"
        class="btn-primary"
        :disabled="applying"
        @click="overview?.signCert ? (reissueConfirmOpen = true) : handleApply()"
      >
        {{ overview?.signCert ? tr('申请重发') : tr('申请证书') }}
      </button>
    </div>

    <div class="grid gap-4 md:grid-cols-2">
      <div class="card cert-detail-card p-4">
        <h2 class="mb-3 text-sm font-medium text-ink">{{ certCardTitle(overview?.signCert ?? null, 'sign') }}</h2>
        <template v-if="overview?.signCert">
          <dl class="cert-detail-list">
            <div class="cert-detail-row">
              <dt>{{ tr('序列号') }}</dt>
              <dd class="font-mono" :title="overview.signCert.certSerial">{{ overview.signCert.certSerial }}</dd>
            </div>
            <div class="cert-detail-row">
              <dt>{{ tr('主体') }}</dt>
              <dd :title="overview.signCert.subjectDn">{{ overview.signCert.subjectDn }}</dd>
            </div>
            <div class="cert-detail-row">
              <dt>{{ tr('有效期至') }}</dt>
              <dd>{{ overview.signCert.notAfter ? formatDateTime(overview.signCert.notAfter) : '-' }}</dd>
            </div>
            <div class="cert-detail-row">
              <dt>{{ tr('状态') }}</dt>
              <dd><StatusTag :value="overview.signCert.status" :map="CERT_STATUS_TAGS" /></dd>
            </div>
          </dl>
        </template>
        <p v-else class="text-sm text-ink-faint">{{ tr('暂无签名证书') }}</p>
      </div>
      <div class="card cert-detail-card p-4">
        <h2 class="mb-3 text-sm font-medium text-ink">{{ certCardTitle(overview?.encryptCert ?? null, 'encrypt') }}</h2>
        <template v-if="overview?.encryptCert">
          <dl class="cert-detail-list">
            <div class="cert-detail-row">
              <dt>{{ tr('序列号') }}</dt>
              <dd class="font-mono" :title="overview.encryptCert.certSerial">{{ overview.encryptCert.certSerial }}</dd>
            </div>
            <div class="cert-detail-row">
              <dt>{{ tr('主体') }}</dt>
              <dd :title="overview.encryptCert.subjectDn">{{ overview.encryptCert.subjectDn }}</dd>
            </div>
            <div class="cert-detail-row">
              <dt>{{ tr('有效期至') }}</dt>
              <dd>{{ overview.encryptCert.notAfter ? formatDateTime(overview.encryptCert.notAfter) : '-' }}</dd>
            </div>
            <div class="cert-detail-row">
              <dt>{{ tr('状态') }}</dt>
              <dd><StatusTag :value="overview.encryptCert.status" :map="CERT_STATUS_TAGS" /></dd>
            </div>
          </dl>
        </template>
        <p v-else class="text-sm text-ink-faint">{{ tr('暂无加密证书') }}</p>
      </div>
    </div>

    <div class="card p-4">
      <h2 class="mb-3 text-sm font-medium text-ink">{{ tr('安装说明') }}</h2>
      <ol class="list-decimal space-y-1 pl-5 text-sm text-ink-secondary">
        <li>{{ tr('下载证书包，将 root-ca.crt 导入「受信任的根证书颁发机构」') }}</li>
        <li>{{ tr('将 intermediate-ca.crt 导入「中间证书颁发机构」') }}</li>
        <li>{{ tr('导入 sign.p12 与 encrypt.p12 到「个人」证书存储（同一 P12 密码；密码仅本页展示一次）') }}</li>
        <li><strong>{{ tr('证书登录只用 sign.p12') }}</strong>{{ tr('（用途含客户端身份验证）。选错 encrypt 会导致登录失败或浏览器报 SSL 错误') }}</li>
        <li>{{ tr('使用 HTTPS 访问本站点，在登录页选择「证书登录」（使用签名证书）') }}</li>
      </ol>
    </div>

    <div class="card overflow-hidden">
      <div class="border-b border-line px-4 py-3 text-sm font-medium text-ink">{{ tr('申请记录') }}</div>
      <div class="table-scroll">
        <table>
          <thead>
            <tr>
              <th>{{ tr('类型') }}</th>
              <th>{{ tr('状态') }}</th>
              <th>{{ tr('申请时间') }}</th>
              <th>{{ tr('说明') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="row in overview?.applies ?? []"
              :key="row.applyId"
              class="border-b border-line last:border-0"
            >
              <td>{{ row.applyType === 'reissue' ? tr('重发') : tr('新申请') }}</td>
              <td><StatusTag :value="row.status" :map="CERT_APPLY_STATUS_TAGS" /></td>
              <td class="font-mono text-[13px]">{{ row.createTime ? formatDateTime(row.createTime) : '-' }}</td>
              <td>{{ row.rejectReason || row.applyReason || '-' }}</td>
            </tr>
            <tr v-if="!loading && !(overview?.applies?.length)">
              <td colspan="4" class="px-4 py-12 text-center text-ink-faint">{{ tr('暂无申请记录') }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>

  <ConfirmModal
    :open="reissueConfirmOpen"
    :title="tr('申请重发证书')"
    :message="tr('提交后需等待管理员审批。若审批通过，当前已签发的签名证与加密证将被吊销，证书登录将立即失效；请下载新证书包并重新导入 sign.p12、encrypt.p12 后再使用证书登录。')"
    :loading="applying"
    @close="reissueConfirmOpen = false"
    @confirm="confirmReissue"
  />

  <BaseModal
    :open="!!revealedPassword"
    :title="tr('P12 密码')"
    width="480px"
    @close="closePasswordModal"
  >
    <div class="space-y-4">
      <div class="flex items-start gap-2 rounded-md border border-amber-200 bg-amber-50 px-3 py-2.5 text-sm text-amber-800">
        <AppIcon name="warning" class="!text-[18px] shrink-0" />
        {{ tr('P12 密码仅本次展示，关闭后无法再次查看。导入 sign.p12、encrypt.p12 时使用同一密码。') }}
      </div>
      <div>
        <label class="form-label">{{ tr('P12 密码') }}</label>
        <div class="flex items-center gap-2">
          <input class="input flex-1 font-mono text-[13px]" :value="revealedPassword ?? ''" readonly />
          <button class="btn-ghost shrink-0" type="button" @click="copyPassword">{{ tr('复制') }}</button>
        </div>
      </div>
      <p v-if="revealApply" class="text-xs text-ink-faint">
        {{ tr('申请 #{id}', { id: revealApply.applyId }) }} · {{ revealApply.applyType === 'reissue' ? tr('重发') : tr('新申请') }}
      </p>
    </div>
    <template #footer>
      <button class="btn-primary" type="button" @click="closePasswordModal">{{ tr('我已保存') }}</button>
    </template>
  </BaseModal>
</template>

<style scoped>
.cert-mine-toolbar {
  justify-content: flex-end;
  flex-wrap: wrap;
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
