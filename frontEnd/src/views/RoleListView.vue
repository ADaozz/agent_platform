<script setup lang="ts">
import PageHeader from '@/components/PageHeader.vue'
import { computed, onMounted, reactive, ref } from 'vue'
import { listRoles, addRole, editRole, authPerm, deleteRole, getPermTree } from '@/api/role'
import { useAuthStore } from '@/stores/auth'
import { toast } from '@/composables/toast'
import type { Id, PermTreeNode, SysRoleVO } from '@/types'
import PaginationBar from '@/components/PaginationBar.vue'
import BaseModal from '@/components/BaseModal.vue'
import ConfirmModal from '@/components/ConfirmModal.vue'
import AppIcon from '@/components/AppIcon.vue'

const auth = useAuthStore()
const canAdd = computed(() => auth.hasPerm('system:role:add'))
const canEdit = computed(() => auth.hasPerm('system:role:edit'))
const canDelete = computed(() => auth.hasPerm('system:role:delete'))

// ---------- 列表 ----------
const filters = reactive({ sysRole: '' })
const pageNum = ref(1)
const pageSize = ref(10)
const total = ref(0)
const rows = ref<SysRoleVO[]>([])
const loading = ref(false)

async function load() {
  loading.value = true
  try {
    const data = await listRoles({
      sysRole: filters.sysRole || undefined,
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
  filters.sysRole = ''
  search()
}

function changePage(p: number) {
  pageNum.value = p
  load()
}

onMounted(load)

// ---------- 权限树 ----------
/** 把任意层级的菜单摊平成「分组 + 权限项」，避免为多级目录再引入递归组件 */
interface PermGroup {
  key: string
  name: string
  perms: PermTreeNode[]
}

function toGroups(nodes: PermTreeNode[], prefix = ''): PermGroup[] {
  return nodes.flatMap((node) => {
    if (node.type !== 'MENU') return []
    const name = prefix ? `${prefix} / ${node.name}` : node.name
    const children = node.children ?? []
    return [
      { key: node.nodeKey, name, perms: children.filter((c) => c.type === 'PERMISSION') },
      ...toGroups(children, name),
    ]
  })
}

const permTree = ref<PermTreeNode[]>([])
const permTreeLoading = ref(false)
const permGroups = computed(() => toGroups(permTree.value))
const allPermIds = computed(() => permGroups.value.flatMap((g) => g.perms.map((p) => p.id)))

async function loadPermTree(roleId?: Id) {
  permTree.value = []
  permTreeLoading.value = true
  try {
    permTree.value = await getPermTree(roleId)
    // 勾选状态以树返回的 checked 为准，而不是角色列表里的已绑定权限
    form.permissionIds = permGroups.value
      .flatMap((g) => g.perms)
      .filter((p) => p.checked)
      .map((p) => p.id)
  } catch {
    // 拦截器已提示
  } finally {
    permTreeLoading.value = false
  }
}

function isMutatingPerm(perm: PermTreeNode) {
  const key = perm.permission ?? ''
  return key.endsWith(':add') || key.endsWith(':edit') || key.endsWith(':delete')
}

function listPermInGroup(group: PermGroup) {
  return group.perms.find((p) => p.permission?.endsWith(':list'))
}

function findPermGroup(id: Id) {
  return permGroups.value.find((g) => g.perms.some((p) => p.id === id))
}

function isPermChecked(id: Id) {
  return form.permissionIds.includes(id)
}

function setPerm(id: Id, checked: boolean) {
  const idx = form.permissionIds.indexOf(id)
  if (checked && idx < 0) form.permissionIds.push(id)
  if (!checked && idx >= 0) form.permissionIds.splice(idx, 1)

  const group = findPermGroup(id)
  if (!group) return
  const perm = group.perms.find((p) => p.id === id)
  if (!perm) return

  if (checked && isMutatingPerm(perm)) {
    const listPerm = listPermInGroup(group)
    if (listPerm && !isPermChecked(listPerm.id)) {
      form.permissionIds.push(listPerm.id)
    }
    return
  }

  if (!checked && perm.permission?.endsWith(':list')) {
    group.perms
      .filter((p) => isMutatingPerm(p) && isPermChecked(p.id))
      .forEach((p) => {
        const mutIdx = form.permissionIds.indexOf(p.id)
        if (mutIdx >= 0) form.permissionIds.splice(mutIdx, 1)
      })
  }
}

function selectedCount(group: PermGroup) {
  return group.perms.filter((p) => isPermChecked(p.id)).length
}

function groupChecked(group: PermGroup) {
  return group.perms.length > 0 && selectedCount(group) === group.perms.length
}

function groupIndeterminate(group: PermGroup) {
  const n = selectedCount(group)
  return n > 0 && n < group.perms.length
}

function toggleGroup(group: PermGroup, checked: boolean) {
  group.perms.forEach((p) => setPerm(p.id, checked))
}

function selectAllPerms() {
  form.permissionIds = [...allPermIds.value]
}

function clearPerms() {
  form.permissionIds = []
}

// ---------- 新增 / 编辑（编辑时同步覆盖权限） ----------
const formOpen = ref(false)
const saving = ref(false)
const editingRoleId = ref<Id | null>(null)
/** admin 角色后端强制全量授权，改了也会被覆盖回去，这里直接置灰 */
const editingAdminRole = ref(false)
const form = reactive({
  sysRole: '',
  permissionIds: [] as Id[],
})

const isEdit = computed(() => editingRoleId.value !== null)

function openAdd() {
  editingRoleId.value = null
  editingAdminRole.value = false
  Object.assign(form, { sysRole: '', permissionIds: [] })
  formOpen.value = true
  loadPermTree()
}

function openEdit(role: SysRoleVO) {
  editingRoleId.value = role.roleId
  editingAdminRole.value = role.sysRole === 'admin'
  Object.assign(form, { sysRole: role.sysRole, permissionIds: [] })
  formOpen.value = true
  loadPermTree(role.roleId)
}

async function saveForm() {
  if (!form.sysRole.trim()) {
    toast.error('角色标识不能为空')
    return
  }
  saving.value = true
  try {
    if (isEdit.value) {
      await editRole({ roleId: editingRoleId.value!, sysRole: form.sysRole.trim() })
      // 编辑时同步覆盖权限（空数组表示清空）
      await authPerm(editingRoleId.value!, form.permissionIds)
      toast.success('修改成功')
    } else {
      await addRole({
        sysRole: form.sysRole.trim(),
        permissionIds: form.permissionIds,
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
const deleteTarget = ref<SysRoleVO | null>(null)
const deleting = ref(false)

async function confirmDelete() {
  if (!deleteTarget.value) return
  deleting.value = true
  try {
    await deleteRole(deleteTarget.value.roleId)
    toast.success('删除成功')
    deleteTarget.value = null
    load()
  } catch {
    // 拦截器已提示（如角色仍绑定用户）
  } finally {
    deleting.value = false
  }
}
</script>

<template>
  <div class="space-y-4">
    <PageHeader title="角色管理" desc="维护系统角色并进行角色—权限绑定（仅管理员可操作）">
      <button v-if="canAdd" class="btn-primary" @click="openAdd">
        <AppIcon name="add" class="!text-[18px]" />
        添加角色
      </button>
    </PageHeader>

    <!-- 筛选 -->
    <div class="card p-4">
      <div class="grid grid-cols-2 gap-3 md:grid-cols-4 xl:grid-cols-5">
        <div>
          <label class="form-label">角色标识</label>
          <input v-model="filters.sysRole" class="input" placeholder="搜索角色标识…" @keyup.enter="search" />
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
              <th class="px-4 py-2.5">角色</th>
              <th class="px-4 py-2.5">已绑定权限</th>
              <th class="px-4 py-2.5 text-right">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="role in rows"
              :key="role.roleId"
              class="border-b border-line transition-colors last:border-0 hover:bg-gray-50"
            >
              <td class="px-4 py-3 align-top">
                <div class="flex items-center gap-3">
                  <div class="flex h-9 w-9 shrink-0 items-center justify-center id-chip">
                    <AppIcon name="shield_person" class="!text-[20px]" />
                  </div>
                  <div>
                    <div class="font-medium">{{ role.sysRole }}</div>
                    <div class="font-mono text-xs text-ink-faint">ID: {{ role.roleId }}</div>
                  </div>
                </div>
              </td>
              <td class="px-4 py-3">
                <div class="flex max-w-3xl flex-wrap gap-1.5">
                  <span
                    v-for="perm in role.permissions ?? []"
                    :key="perm.id"
                    class="rounded border border-line bg-gray-50 px-2 py-0.5 text-xs text-ink-secondary"
                  >
                    {{ perm.label }}
                  </span>
                  <span v-if="!role.permissions?.length" class="text-xs text-ink-faint">未绑定权限</span>
                </div>
              </td>
              <td class="px-4 py-3 text-right align-top whitespace-nowrap">
                <button
                  v-if="canEdit"
                  class="text-sm font-medium text-primary hover:underline"
                  @click="openEdit(role)"
                >
                  编辑
                </button>
                <button
                  v-if="canDelete"
                  class="ml-3 text-sm font-medium text-danger hover:underline"
                  @click="deleteTarget = role"
                >
                  删除
                </button>
              </td>
            </tr>
            <tr v-if="!loading && rows.length === 0">
              <td colspan="3" class="px-4 py-16 text-center text-ink-faint">暂无数据</td>
            </tr>
          </tbody>
        </table>
      </div>
      <PaginationBar :total="total" :page-num="pageNum" :page-size="pageSize" @change="changePage" />
    </div>

    <!-- 新增 / 编辑弹窗 -->
    <BaseModal :open="formOpen" :title="isEdit ? '编辑角色' : '添加角色'" width="560px" @close="formOpen = false">
      <div class="space-y-4">
        <div>
          <label class="form-label">角色标识 <span class="text-danger">*</span></label>
          <input v-model="form.sysRole" class="input" maxlength="64" placeholder="如 ops、readonly" />
        </div>
        <div v-if="auth.isAdmin">
          <div class="flex items-center justify-between">
            <label class="form-label">
              绑定权限（覆盖式，已选 {{ form.permissionIds.length }} / {{ allPermIds.length }} 项）
            </label>
            <div v-if="!editingAdminRole" class="flex gap-2 text-xs">
              <button type="button" class="font-medium text-primary hover:underline" @click="selectAllPerms">全选</button>
              <button type="button" class="font-medium text-ink-muted hover:underline" @click="clearPerms">清空</button>
            </div>
          </div>
          <div class="max-h-72 overflow-y-auto rounded-md border border-line">
            <div v-if="permTreeLoading" class="px-3 py-8 text-center text-xs text-ink-faint">加载中…</div>
            <div v-else-if="permGroups.length === 0" class="px-3 py-8 text-center text-xs text-ink-faint">
              暂无可分配权限
            </div>
            <div v-for="group in permGroups" :key="group.key" class="border-b border-line last:border-0">
              <label class="flex cursor-pointer items-center gap-2 bg-gray-50 px-3 py-2 text-sm font-medium text-ink">
                <input
                  type="checkbox"
                  class="h-4 w-4 accent-primary"
                  :checked="groupChecked(group)"
                  :indeterminate.prop="groupIndeterminate(group)"
                  :disabled="editingAdminRole || group.perms.length === 0"
                  @change="toggleGroup(group, ($event.target as HTMLInputElement).checked)"
                />
                {{ group.name }}
                <span class="text-xs font-normal text-ink-faint">
                  {{ selectedCount(group) }}/{{ group.perms.length }}
                </span>
              </label>
              <div v-if="group.perms.length" class="grid grid-cols-2 gap-x-4 gap-y-1.5 px-3 py-2.5 sm:grid-cols-3">
                <label
                  v-for="perm in group.perms"
                  :key="perm.nodeKey"
                  class="flex cursor-pointer items-center gap-2 text-sm text-ink-secondary"
                  :title="perm.permission"
                >
                  <input
                    type="checkbox"
                    class="h-4 w-4 accent-primary"
                    :checked="isPermChecked(perm.id)"
                    :disabled="editingAdminRole"
                    @change="setPerm(perm.id, ($event.target as HTMLInputElement).checked)"
                  />
                  {{ perm.name }}
                </label>
              </div>
              <div v-else class="px-3 py-2 text-xs text-ink-faint">该菜单暂无权限项</div>
            </div>
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
      title="删除角色"
      :message="`确定要删除角色「${deleteTarget?.sysRole}」吗？仅允许删除未绑定用户的角色，该操作不可恢复。`"
      :loading="deleting"
      danger
      @close="deleteTarget = null"
      @confirm="confirmDelete"
    />
  </div>
</template>
