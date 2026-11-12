import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { toast } from '@/composables/toast'

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
          meta: { title: '模型配置', icon: 'module', group: '平台设置' },
        },
        {
          path: 'system/user',
          name: 'system-user',
          component: () => import('@/views/UserListView.vue'),
          meta: { title: '用户管理', icon: 'access', group: '平台设置', permission: 'system:user:list' },
        },
        {
          path: 'system/role',
          name: 'system-role',
          component: () => import('@/views/RoleListView.vue'),
          meta: { title: '角色管理', icon: 'route', group: '平台设置', permission: 'system:role:list' },
        },
        {
          path: 'system/session',
          name: 'system-session',
          component: () => import('@/views/SessionListView.vue'),
          meta: { title: '登录设备管理', icon: 'satellite', group: '平台设置', permission: 'system:session:list' },
        },
        {
          path: 'system/cert/mine',
          name: 'system-cert-mine',
          component: () => import('@/views/MyCertView.vue'),
          meta: { title: '我的证书', icon: 'scan', group: '平台设置', permission: 'system:cert:mine' },
        },
        {
          path: 'system/cert',
          name: 'system-cert',
          component: () => import('@/views/CertManageView.vue'),
          meta: { title: '证书管理', icon: 'beacon', group: '平台设置', permission: 'system:cert:list' },
        },
      ],
    },
    { path: '/:pathMatch(.*)*', redirect: '/agent' },
  ],
})

router.beforeEach((to) => {
  const auth = useAuthStore()
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
