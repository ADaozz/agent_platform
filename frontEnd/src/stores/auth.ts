import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { login as apiLogin, loginByCert as apiLoginByCert } from '@/api/auth'
import { logoutApi } from '@/api/session'
import { TOKEN_KEY, USER_KEY, SESSION_KEY } from '@/api/request'
import type { SysUserInfoVO } from '@/types'

function loadUser(): SysUserInfoVO | null {
  try {
    const raw = localStorage.getItem(USER_KEY)
    return raw ? (JSON.parse(raw) as SysUserInfoVO) : null
  } catch {
    return null
  }
}

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem(TOKEN_KEY))
  const user = ref<SysUserInfoVO | null>(loadUser())

  const isLoggedIn = computed(() => !!token.value)
  const permissions = computed(() => (user.value?.permissions ?? []).map((p) => p.label))
  const roles = computed(() => (user.value?.roles ?? []).map((r) => r.label))
  /** 角色与权限的分配操作后端只放给 admin，非 admin 不渲染相关 UI */
  const isAdmin = computed(() => roles.value.includes('admin'))

  function hasPerm(perm: string) {
    return permissions.value.includes(perm)
  }

  function persistLogin(data: { token: string; sessionId: string; user: SysUserInfoVO }) {
    token.value = data.token
    user.value = data.user
    localStorage.setItem(TOKEN_KEY, data.token)
    localStorage.setItem(USER_KEY, JSON.stringify(data.user))
    localStorage.setItem(SESSION_KEY, data.sessionId)
  }

  async function login(userName: string, passWord: string) {
    persistLogin(await apiLogin(userName, passWord))
  }

  function loginByCert() {
    apiLoginByCert()
  }

  async function logout() {
    try {
      await logoutApi()
    } catch {
      // 401 等仍清本地态
    }
    token.value = null
    user.value = null
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
    localStorage.removeItem(SESSION_KEY)
  }

  return { token, user, isLoggedIn, permissions, roles, isAdmin, hasPerm, login, loginByCert, persistLogin, logout }
})
