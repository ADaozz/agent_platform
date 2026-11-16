import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { toast } from '@/composables/toast'
import { tr } from '@/composables/preferences'
import { parseCertLoginPayload } from '@/api/auth'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/LoginView.vue'),
      meta: { public: true },
    },
    {
      path: '/',
      component: () => import('@/layouts/AppLayout.vue'),
      redirect: '/agent',
      children: [
        {
          path: 'agent',
          name: 'agent',
          component: () => import('@/views/AgentChatView.vue'),
          meta: { title: 'Agent 对话' },
        },
        {
          path: 'settings/models',
          name: 'settings-models',
          component: () => import('@/views/ModelSettingsView.vue'),
          meta: { title: '模型配置', icon: 'memory', group: '平台设置', eyebrow: 'MODEL REGISTRY' },
        },
        {
          path: 'settings/capabilities',
          name: 'settings-capabilities',
          component: () => import('@/views/PlatformCapabilitiesView.vue'),
          meta: { title: '平台能力', icon: 'extension', group: '平台设置', eyebrow: 'CAPABILITY MOUNTS' },
        },
        {
          path: 'settings/usage',
          name: 'settings-usage',
          component: () => import('@/views/UsageDashboardView.vue'),
          meta: { title: '用量仪表盘', icon: 'telemetry', group: '平台设置', eyebrow: 'USAGE TELEMETRY' },
        },
        {
          path: 'system/user',
          name: 'system-user',
          component: () => import('@/views/UserListView.vue'),
          meta: { title: '用户管理', icon: 'group', group: '平台设置', permission: 'system:user:list', eyebrow: 'USER REGISTRY' },
        },
        {
          path: 'system/role',
          name: 'system-role',
          component: () => import('@/views/RoleListView.vue'),
          meta: { title: '角色管理', icon: 'shield_person', group: '平台设置', permission: 'system:role:list', eyebrow: 'ROLE MATRIX' },
        },
        {
          path: 'system/session',
          name: 'system-session',
          component: () => import('@/views/SessionListView.vue'),
          meta: { title: '登录设备管理', icon: 'devices', group: '平台设置', permission: 'system:session:list', eyebrow: 'SESSION LOG' },
        },
        {
          path: 'system/cert/mine',
          name: 'system-cert-mine',
          component: () => import('@/views/MyCertView.vue'),
          meta: { title: '我的证书', icon: 'verified_user', group: '平台设置', permission: 'system:cert:mine', eyebrow: 'MY CERTIFICATE' },
        },
        {
          path: 'system/cert',
          name: 'system-cert',
          component: () => import('@/views/CertManageView.vue'),
          meta: { title: '证书管理', icon: 'key', group: '平台设置', permission: 'system:cert:list', eyebrow: 'CERTIFICATE AUTHORITY' },
        },
      ],
    },
    { path: '/:pathMatch(.*)*', redirect: '/agent' },
  ],
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  const certPayload = to.hash.match(/^#certLogin=(.+)$/)?.[1]
  if (certPayload) {
    try {
      auth.persistLogin(parseCertLoginPayload(certPayload))
    } catch {
      toast.error(tr('证书登录失败'))
      return { path: '/login' }
    }
    toast.success(tr('证书登录成功'))
    return { path: (to.query.redirect as string) || '/' }
  }
  if (to.meta.public) {
    if (auth.isLoggedIn && to.name === 'login') return { path: '/' }
    return true
  }
  if (!auth.isLoggedIn) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }
  const perm = to.meta.permission as string | undefined
  if (perm && !auth.hasPerm(perm)) {
    toast.error('无权限访问该页面')
    return { path: '/agent' }
  }
  return true
})

export default router
