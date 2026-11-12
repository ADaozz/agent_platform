<script setup lang="ts">
import PageHeader from '@/components/PageHeader.vue'
import { computed, onMounted, reactive, ref } from 'vue'
import { listTokens, addToken, deleteToken, getGrantOptions } from '@/api/token'
import { useAuthStore } from '@/stores/auth'
import { toast } from '@/composables/toast'
import { TOKEN_STATUS_TAGS, TOKEN_ASSET_LABELS } from '@/constants'
import type { ApiTokenGrantGroup, ApiTokenGrantOption, ApiTokenVO, TokenAsset } from '@/types'
import StatusTag from '@/components/StatusTag.vue'
import PaginationBar from '@/components/PaginationBar.vue'
import BaseModal from '@/components/BaseModal.vue'
import ConfirmModal from '@/components/ConfirmModal.vue'
import AppIcon from '@/components/AppIcon.vue'
import OpenApiDocPanel from '@/components/openapi/OpenApiDocPanel.vue'

const auth = useAuthStore()
const tab = ref<'token' | 'doc'>('token')
const canAdd = computed(() => auth.hasPerm('api:token:add'))
const canDelete = computed(() => auth.hasPerm('api:token:delete'))

const grantGroups = ref<ApiTokenGrantGroup[]>([])
const grantLoading = ref(false)

const hasAnyGrantOption = computed(() => grantGroups.value.some((g) => g.options.length > 0))

async function loadGrantOptions() {
  grantLoading.value = true
  try {
    grantGroups.value = await getGrantOptions()
  } catch {
    grantGroups.value = []
  } finally {
    grantLoading.value = false
  }
}

// ---------- 列表 ----------
const filters = reactive({ tokenName: '', accessKey: '' })
const pageNum = ref(1)
const pageSize = ref(10)
const total = ref(0)
const rows = ref<ApiTokenVO[]>([])
const loading = ref(false)

async function load() {
  loading.value = true
  try {
    const data = await listTokens({
      tokenName: filters.tokenName || undefined,
      accessKey: filters.accessKey || undefined,
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
  filters.tokenName = ''
  filters.accessKey = ''
  search()
}

function changePage(p: number) {
  pageNum.value = p
  load()
}

onMounted(load)

async function copyText(text: string) {
  try {
    await navigator.clipboard.writeText(text)
    toast.success('已复制到剪贴板')
  } catch {
    toast.error('复制失败，请手动复制')
  }
}

// ---------- 新建 ----------
const addOpen = ref(false)
const saving = ref(false)
const form = reactive({
  tokenName: '',
  detail: '',
  asset: [] as TokenAsset[],
})

async function openAdd() {
  Object.assign(form, { tokenName: '', detail: '', asset: [] })
  addOpen.value = true
  await loadGrantOptions()
}

function toggleAsset(opt: ApiTokenGrantOption) {
  const idx = form.asset.indexOf(opt.value)
  if (idx >= 0) form.asset.splice(idx, 1)
  else form.asset.push(opt.value)
}

/** 创建成功后一次性展示 AK/SK */
const createdToken = ref<ApiTokenVO | null>(null)

async function saveAdd() {
  if (!form.tokenName.trim()) {
    toast.error('请输入 Token 名称')
    return
  }
  if (!form.detail.trim()) {
    toast.error('请输入用途说明')
    return
  }
  if (form.asset.length === 0) {
    toast.error('请至少选择一个授权资源')
    return
  }
  saving.value = true
  try {
    const data = await addToken({
      tokenName: form.tokenName.trim(),
      detail: form.detail.trim(),
      asset: [...form.asset],
    })
    addOpen.value = false
    createdToken.value = data
    load()
  } catch {
    // 拦截器已提示（如超过 3 个有效 Token）
  } finally {
    saving.value = false
  }
}

// ---------- 吊销 ----------
const revokeTarget = ref<ApiTokenVO | null>(null)
const revoking = ref(false)

async function confirmRevoke() {
  if (!revokeTarget.value) return
  revoking.value = true
  try {
    await deleteToken(revokeTarget.value.accessKey)
    toast.success('吊销成功')
    revokeTarget.value = null
    load()
  } catch {
    // 拦截器已提示
  } finally {
    revoking.value = false
  }
}
</script>

<template>
  <div class="space-y-4">
    <PageHeader title="API 开放接口" desc="管理外部系统调用凭证（AK/SK），按授权资源与操作（查询/新增/修改/删除）访问开放接口">
      <button v-if="canAdd && tab === 'token'" class="btn-primary" @click="openAdd">
        <AppIcon name="add" class="!text-[18px]" />
        新建 Token
      </button>
    </PageHeader>

    <div class="flex gap-1 border-b border-line">
      <button
        type="button"
        class="border-b-2 px-4 py-2 text-sm font-medium transition-colors"
        :class="tab === 'token' ? 'border-primary text-primary' : 'border-transparent text-ink-muted hover:text-ink'"
        @click="tab = 'token'"
      >
        Token 管理
      </button>
      <button
        type="button"
        class="border-b-2 px-4 py-2 text-sm font-medium transition-colors"
        :class="tab === 'doc' ? 'border-primary text-primary' : 'border-transparent text-ink-muted hover:text-ink'"
        @click="tab = 'doc'"
      >
        接口文档
      </button>
    </div>

    <OpenApiDocPanel v-show="tab === 'doc'" />

    <div v-show="tab === 'token'" class="space-y-4">
    <!-- 筛选 -->
    <div class="card p-4">
      <div class="grid grid-cols-2 gap-3 md:grid-cols-4 xl:grid-cols-5">
        <div>
          <label class="form-label">名称</label>
          <input v-model="filters.tokenName" class="input" placeholder="搜索 Token 名称…" @keyup.enter="search" />
        </div>
        <div>
          <label class="form-label">AccessKey</label>
          <input v-model="filters.accessKey" class="input font-mono" placeholder="ak-…" @keyup.enter="search" />
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
              <th class="px-4 py-2.5">名称 / 用途</th>
              <th class="px-4 py-2.5">AccessKey</th>
              <th class="px-4 py-2.5">授权资源</th>
              <th class="px-4 py-2.5">状态</th>
              <th class="px-4 py-2.5">创建时间</th>
              <th class="px-4 py-2.5">过期时间</th>
              <th class="px-4 py-2.5 text-right">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="t in rows"
              :key="t.accessKey"
              class="border-b border-line transition-colors last:border-0 hover:bg-gray-50"
            >
              <td class="px-4 py-3">
                <div class="font-medium">{{ t.tokenName }}</div>
                <div class="max-w-52 truncate text-xs text-ink-faint" :title="t.detail || ''">{{ t.detail || '-' }}</div>
              </td>
              <td class="px-4 py-3">
                <div class="flex items-center gap-1.5">
                  <span class="max-w-44 truncate font-mono text-[13px] text-ink-muted" :title="t.accessKey">{{ t.accessKey }}</span>
                  <button
                    class="flex h-6 w-6 shrink-0 items-center justify-center rounded text-ink-faint transition-colors hover:bg-gray-100 hover:text-primary"
                    title="复制 AccessKey"
                    @click="copyText(t.accessKey)"
                  >
                    <AppIcon name="content_copy" class="!text-[15px]" />
                  </button>
                </div>
              </td>
              <td class="px-4 py-3">
                <div class="flex flex-wrap gap-1.5">
                  <span
                    v-for="a in t.asset ?? []"
                    :key="a"
                    class="rounded border border-line bg-gray-50 px-2 py-0.5 text-xs text-ink-secondary"
                  >
                    {{ TOKEN_ASSET_LABELS[a] ?? a }}
                  </span>
                  <span v-if="!t.asset?.length" class="text-xs text-ink-faint">-</span>
                </div>
              </td>
              <td class="px-4 py-3">
                <StatusTag :value="t.status" :map="TOKEN_STATUS_TAGS" />
              </td>
              <td class="px-4 py-3 font-mono text-[13px] text-ink-muted">{{ t.createTime || '-' }}</td>
              <td class="px-4 py-3 font-mono text-[13px] text-ink-muted">{{ t.expireTime || '-' }}</td>
              <td class="px-4 py-3 text-right">
                <button
                  v-if="canDelete && t.status === '0'"
                  class="text-sm font-medium text-danger hover:underline"
                  @click="revokeTarget = t"
                >
                  吊销
                </button>
              </td>
            </tr>
            <tr v-if="!loading && rows.length === 0">
              <td colspan="7" class="px-4 py-16 text-center text-ink-faint">暂无 Token 数据</td>
            </tr>
          </tbody>
        </table>
      </div>
      <PaginationBar :total="total" :page-num="pageNum" :page-size="pageSize" @change="changePage" />
    </div>

    <!-- 新建弹窗 -->
    <BaseModal :open="addOpen" title="新建 API Token" width="560px" @close="addOpen = false">
      <div class="space-y-4">
        <div>
          <label class="form-label">Token 名称 <span class="text-danger">*</span></label>
          <input v-model="form.tokenName" class="input" placeholder="如 Jenkins CI/CD" maxlength="128" />
        </div>
        <div>
          <label class="form-label">用途说明 <span class="text-danger">*</span></label>
          <input v-model="form.detail" class="input" placeholder="如 部署流水线读取资产信息" maxlength="255" />
        </div>
        <div>
          <label class="form-label">授权资源 <span class="text-danger">*</span></label>
          <p class="mb-2 text-xs text-ink-faint">
            勾选 Token 可调用的开放接口能力；通过 AK/SK 删改资产时，仅能操作 owner 为 Token 所属用户的数据。
          </p>
          <div v-if="grantLoading" class="rounded-md border border-line px-3 py-8 text-center text-sm text-ink-faint">
            加载授权项…
          </div>
          <div v-else-if="!hasAnyGrantOption" class="rounded-md border border-line px-3 py-6 text-center text-sm text-ink-faint">
            暂无可配置开放能力。
          </div>
          <div v-else class="space-y-3">
            <div v-for="group in grantGroups" :key="group.key" class="rounded-md border border-line p-3">
              <div class="mb-2 text-sm font-medium text-ink">{{ group.name }}</div>
              <div class="grid grid-cols-1 gap-2 sm:grid-cols-2">
                <label
                  v-for="opt in group.options"
                  :key="opt.value"
                  class="flex items-center gap-2.5 rounded-md border px-3 py-2 text-sm transition-colors"
                  :class="[
                    form.asset.includes(opt.value)
                      ? 'cursor-pointer border-primary bg-primary-light font-medium text-primary'
                      : 'cursor-pointer border-line text-ink-secondary hover:bg-gray-50',
                  ]"
                  :title="opt.label"
                >
                  <input
                    type="checkbox"
                    class="accent-primary"
                    :checked="form.asset.includes(opt.value)"
                    @change="toggleAsset(opt)"
                  />
                  <span class="min-w-0 flex-1">{{ opt.label }}</span>
                </label>
              </div>
            </div>
          </div>
        </div>
        <p class="text-xs text-ink-faint">同一用户最多持有 3 个有效 Token；SecretKey 仅在创建成功后展示一次。</p>
      </div>
      <template #footer>
        <button class="btn-ghost" @click="addOpen = false">取消</button>
        <button class="btn-primary" :disabled="saving || grantLoading || !hasAnyGrantOption" @click="saveAdd">
          {{ saving ? '创建中…' : '创建' }}
        </button>
      </template>
    </BaseModal>

    <!-- 创建成功：一次性展示 AK/SK -->
    <BaseModal
      :open="!!createdToken"
      title="Token 创建成功"
      width="560px"
      @close="createdToken = null"
    >
      <div class="space-y-4">
        <div class="flex items-start gap-2 rounded-md border border-amber-200 bg-amber-50 px-3 py-2.5 text-sm text-amber-800">
          <AppIcon name="warning" class="!text-[18px]" />
          SecretKey 仅在本次展示，关闭后无法再次查看，请立即妥善保存。
        </div>
        <div>
          <label class="form-label">AccessKey（X-Access-Key）</label>
          <div class="flex items-center gap-2">
            <input class="input flex-1 font-mono text-[13px]" :value="createdToken?.accessKey" readonly />
            <button class="btn-ghost shrink-0" @click="copyText(createdToken?.accessKey || '')">复制</button>
          </div>
        </div>
        <div>
          <label class="form-label">SecretKey（X-Secret-Key）</label>
          <div class="flex items-start gap-2">
            <textarea
              class="input flex-1 resize-none font-mono text-[13px]"
              rows="4"
              :value="createdToken?.secretKey ?? ''"
              readonly
            ></textarea>
            <button class="btn-ghost shrink-0" @click="copyText(createdToken?.secretKey || '')">复制</button>
          </div>
        </div>
        <div class="text-xs text-ink-faint">
          过期时间：<span class="font-mono">{{ createdToken?.expireTime || '-' }}</span>
        </div>
      </div>
      <template #footer>
        <button class="btn-primary" @click="createdToken = null">我已保存</button>
      </template>
    </BaseModal>

    <!-- 吊销确认 -->
    <ConfirmModal
      :open="!!revokeTarget"
      title="吊销 Token"
      :message="`确定要吊销 Token「${revokeTarget?.tokenName}」吗？吊销后使用该凭证的调用将立即失效。`"
      :loading="revoking"
      danger
      @close="revokeTarget = null"
      @confirm="confirmRevoke"
    />
    </div>
  </div>
</template>
