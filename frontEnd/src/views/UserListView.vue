<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { listUsers, addUser, editUser, authRole, deleteUser } from '@/api/user'
import { getRoleOptions } from '@/api/role'
import { useAuthStore } from '@/stores/auth'
import { toast } from '@/composables/toast'
import { USER_STATUS_TAGS } from '@/constants'
import { formatDateTime } from '@/utils/format'
import type { Id, OptionVO, SysUserVO } from '@/types'
import StatusTag from '@/components/StatusTag.vue'
import PaginationBar from '@/components/PaginationBar.vue'
import BaseModal from '@/components/BaseModal.vue'
import ConfirmModal from '@/components/ConfirmModal.vue'
import AppIcon from '@/components/AppIcon.vue'

const auth = useAuthStore()
const canAdd = computed(() => auth.hasPerm('system:user:add'))
const canEdit = computed(() => auth.hasPerm('system:user:edit'))
const canDelete = computed(() => auth.hasPerm('system:user:delete'))

// ---------- 列表 ----------
const filters = reactive({
  userName: '',
  status: '',
  roleId: '' as string | number,
})
const pageNum = ref(1)
const pageSize = ref(10)
const total = ref(0)
const rows = ref<SysUserVO[]>([])
const loading = ref(false)
const roleOptions = ref<OptionVO[]>([])

async function load() {
  loading.value = true
  try {
    const data = await listUsers({
      userName: filters.userName || undefined,
      status: filters.status || undefined,
      roleId: filters.roleId ? Number(filters.roleId) : undefined,
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
  filters.userName = ''
  filters.status = ''
  filters.roleId = ''
  search()
}

function changePage(p: number) {
  pageNum.value = p
  load()
}

onMounted(async () => {
  load()
  try {
    roleOptions.value = await getRoleOptions()
  } catch {
    // 无角色查询权限时静默失败
  }
})

// ---------- 新增 / 编辑 ----------
const formOpen = ref(false)
const saving = ref(false)
const editingUserId = ref<Id | null>(null)
const form = reactive({
  userName: '',
  passWord: '',
  status: '0',
  roleIds: [] as Id[],
})

const isEdit = computed(() => editingUserId.value !== null)

function openAdd() {
  editingUserId.value = null
  Object.assign(form, { userName: '', passWord: '', status: '0', roleIds: [] })
  formOpen.value = true
}

function openEdit(user: SysUserVO) {
  editingUserId.value = user.userId
  Object.assign(form, {
    userName: user.userName,
    passWord: '',
    status: user.status,
    roleIds: user.roles.map((r) => r.id),
  })
  formOpen.value = true
}

function toggleRole(id: Id) {
  const idx = form.roleIds.indexOf(id)
  if (idx >= 0) form.roleIds.splice(idx, 1)
  else form.roleIds.push(id)
}

async function saveForm() {
  if (!form.userName.trim()) {
    toast.error('用户名不能为空')
    return
  }
  if (!isEdit.value && (form.passWord.length < 6 || form.passWord.length > 32)) {
    toast.error('密码长度需为 6–32 位')
    return
  }
  if (isEdit.value && form.passWord && (form.passWord.length < 6 || form.passWord.length > 32)) {
    toast.error('密码长度需为 6–32 位')
    return
  }
  saving.value = true
  try {
    if (isEdit.value) {
      await editUser({
        userId: editingUserId.value!,
        userName: form.userName.trim(),
        passWord: form.passWord || undefined,
        status: form.status,
      })
      // 编辑时同步覆盖角色
      await authRole(editingUserId.value!, form.roleIds)
      toast.success('修改成功')
    } else {
      await addUser({
        userName: form.userName.trim(),
        passWord: form.passWord,
        status: form.status,
        roleIds: form.roleIds,
      })
      toast.success('新增成功')
    }
    formOpen.value = false
    load()
  } catch {
    // 拦截器已提示
  } finally {
    saving.value = false
  }
}

// ---------- 删除 ----------
const deleteTarget = ref<SysUserVO | null>(null)
const deleting = ref(false)

async function confirmDelete() {
  if (!deleteTarget.value) return
  deleting.value = true
  try {
    await deleteUser(deleteTarget.value.userId)
    toast.success('删除成功')
    deleteTarget.value = null
    load()
  } catch {
    // 拦截器已提示
  } finally {
    deleting.value = false
  }
}
</script>

<template>
  <div class="space-y-4">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h1 class="text-2xl font-semibold tracking-tight text-ink">用户管理</h1>
        <p class="mt-0.5 text-sm text-ink-muted">管理系统登录用户，分配角色权限及账户状态控制</p>
      </div>
      <button v-if="canAdd" class="btn-primary" @click="openAdd">
        <AppIcon name="person_add" class="!text-[18px]" />
        添加用户
      </button>
    </div>

    <!-- 筛选 -->
    <div class="card p-4">
      <div class="grid grid-cols-2 gap-3 md:grid-cols-4 xl:grid-cols-5">
        <div>
          <label class="form-label">用户名</label>
          <input v-model="filters.userName" class="input" placeholder="搜索用户名…" @keyup.enter="search" />
        </div>
        <div>
          <label class="form-label">状态</label>
          <select v-model="filters.status" class="select">
            <option value="">全部状态</option>
            <option value="0">已启用</option>
            <option value="1">已停用</option>
          </select>
        </div>
        <div>
          <label class="form-label">角色</label>
          <select v-model="filters.roleId" class="select">
            <option value="">全部角色</option>
            <option v-for="r in roleOptions" :key="r.id" :value="r.id">{{ r.label }}</option>
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
              <th class="px-4 py-2.5">用户信息</th>
              <th class="px-4 py-2.5">角色</th>
              <th class="px-4 py-2.5">状态</th>
              <th class="px-4 py-2.5">创建时间</th>
              <th class="px-4 py-2.5">最后登录</th>
              <th class="px-4 py-2.5 text-right">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="user in rows"
              :key="user.userId"
              class="border-b border-line transition-colors last:border-0 hover:bg-gray-50"
            >
              <td class="px-4 py-3">
                <div class="flex items-center gap-3">
                  <div class="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-primary-light text-sm font-semibold text-primary">
                    {{ user.userName.charAt(0).toUpperCase() }}
                  </div>
                  <div>
                    <div class="font-medium">{{ user.userName }}</div>
                    <div class="font-mono text-xs text-ink-faint">ID: {{ user.userId }}</div>
                  </div>
                </div>
              </td>
              <td class="px-4 py-3">
                <div class="flex flex-wrap gap-1.5">
                  <span
                    v-for="role in user.roles"
                    :key="role.id"
                    class="rounded border border-line bg-gray-50 px-2 py-0.5 text-xs text-ink-secondary"
                  >
                    {{ role.label }}
                  </span>
                  <span v-if="user.roles.length === 0" class="text-xs text-ink-faint">-</span>
                </div>
              </td>
              <td class="px-4 py-3">
                <StatusTag :value="user.status" :map="USER_STATUS_TAGS" />
              </td>
              <td class="px-4 py-3 font-mono text-[13px] text-ink-muted">{{ formatDateTime(user.createTime) }}</td>
              <td class="px-4 py-3 font-mono text-[13px] text-ink-muted">{{ user.lastLoginTime ? formatDateTime(user.lastLoginTime) : '从未登录' }}</td>
              <td class="px-4 py-3 text-right whitespace-nowrap">
                <button
                  v-if="canEdit"
                  class="text-sm font-medium text-primary hover:underline"
                  @click="openEdit(user)"
                >
                  编辑
                </button>
                <button
                  v-if="canDelete"
                  class="ml-3 text-sm font-medium text-danger hover:underline"
                  :disabled="user.userId === auth.user?.userId"
                  :class="{ 'cursor-not-allowed opacity-40': user.userId === auth.user?.userId }"
                  @click="deleteTarget = user"
                >
                  删除
                </button>
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

    <!-- 新增 / 编辑弹窗 -->
    <BaseModal :open="formOpen" :title="isEdit ? '编辑用户' : '添加用户'" width="440px" @close="formOpen = false">
      <div class="space-y-4">
        <div>
          <label class="form-label">用户名 <span class="text-danger">*</span></label>
          <input v-model="form.userName" class="input" maxlength="64" placeholder="请输入用户名" />
        </div>
        <div>
          <label class="form-label">
            {{ isEdit ? '密码（留空则不修改）' : '密码' }}<span v-if="!isEdit" class="text-danger"> *</span>
          </label>
          <input
            v-model="form.passWord"
            class="input"
            type="password"
            maxlength="32"
            placeholder="6–32 位"
            autocomplete="new-password"
          />
        </div>
        <div>
          <label class="form-label">状态</label>
          <select v-model="form.status" class="select">
            <option value="0">已启用</option>
            <option value="1">已停用</option>
          </select>
        </div>
        <div>
          <label class="form-label">角色</label>
          <div class="flex flex-wrap gap-2">
            <button
              v-for="r in roleOptions"
              :key="r.id"
              type="button"
              class="rounded-md border px-3 py-1.5 text-sm transition-colors"
              :class="form.roleIds.includes(r.id)
                ? 'border-primary bg-primary-light font-medium text-primary'
                : 'border-line text-ink-secondary hover:bg-gray-50'"
              @click="toggleRole(r.id)"
            >
              {{ r.label }}
            </button>
            <span v-if="roleOptions.length === 0" class="text-xs text-ink-faint">暂无可选角色</span>
          </div>
        </div>
      </div>
      <template #footer>
        <button class="btn-ghost" @click="formOpen = false">取消</button>
        <button class="btn-primary" :disabled="saving" @click="saveForm">
          {{ saving ? '保存中…' : '保存' }}
        </button>
      </template>
    </BaseModal>

    <!-- 删除确认 -->
    <ConfirmModal
      :open="!!deleteTarget"
      title="删除用户"
      :message="`确定要删除用户「${deleteTarget?.userName}」吗？该操作不可恢复。`"
      :loading="deleting"
      danger
      @close="deleteTarget = null"
      @confirm="confirmDelete"
    />
  </div>
</template>
