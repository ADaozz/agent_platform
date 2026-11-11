<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { toast } from '@/composables/toast'
import type { LoginResult } from '@/types'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

const userName = ref('')
const passWord = ref('')
const loading = ref(false)
const certLoading = ref(false)

const CERT_ERROR_MESSAGES: Record<string, string> = {
  no_client_cert: '未检测到客户端证书，请确认已导入 sign.p12',
}

function decodeBase64Url(value: string): string {
  const base64 = value.replace(/-/g, '+').replace(/_/g, '/')
  const pad = base64.length % 4 === 0 ? '' : '='.repeat(4 - (base64.length % 4))
  const binary = atob(base64 + pad)
  const bytes = Uint8Array.from(binary, (c) => c.charCodeAt(0))
  return new TextDecoder().decode(bytes)
}

function parseLoginPayload(json: string): LoginResult {
  return JSON.parse(json.replace(/([:[,]\s*)(\d{16,})(\s*[,}\]])/g, '$1"$2"$3'))
}

onMounted(() => {
  const certError = route.query.certError as string | undefined
  if (certError) {
    toast.error(CERT_ERROR_MESSAGES[certError] ?? decodeURIComponent(certError))
    router.replace({ path: '/login' })
  }

  const match = location.hash.match(/^#certLogin=(.+)$/)
  if (!match) return

  try {
    const data = parseLoginPayload(decodeBase64Url(match[1]!))
    auth.persistLogin(data)
    history.replaceState(null, '', location.pathname + location.search)
    toast.success('证书登录成功')
    const redirect = (route.query.redirect as string) || '/'
    router.replace(redirect)
  } catch {
    history.replaceState(null, '', location.pathname)
    toast.error('证书登录失败')
  }
})

async function handleLogin() {
  if (!userName.value.trim() || !passWord.value) {
    toast.error('请输入用户名和密码')
    return
  }
  loading.value = true
  try {
    await auth.login(userName.value.trim(), passWord.value)
    toast.success('登录成功')
    const redirect = (route.query.redirect as string) || '/'
    router.push(redirect)
  } catch {
    // 错误提示已由拦截器统一处理
  } finally {
    loading.value = false
  }
}

function handleCertLogin() {
  certLoading.value = true
  auth.loginByCert()
}
</script>

<template>
  <div class="flex min-h-full items-center justify-center bg-page px-4">
    <div class="w-full max-w-sm">
      <div class="card px-8 py-10 shadow-sm">
        <div class="mb-8 text-center">
          <img src="/deep-agent-icon.svg" alt="Deep Agent" class="mx-auto mb-4 h-12 w-12 rounded-lg" />
          <h1 class="text-xl font-semibold text-ink">Agent Platform</h1>
        </div>

        <form class="space-y-4" @submit.prevent="handleLogin">
          <div>
            <label class="form-label" for="username">用户名</label>
            <input
              id="username"
              v-model="userName"
              class="input"
              type="text"
              placeholder="请输入用户名"
              maxlength="64"
              autocomplete="username"
            />
          </div>
          <div>
            <label class="form-label" for="password">密码</label>
            <input
              id="password"
              v-model="passWord"
              class="input"
              type="password"
              placeholder="请输入密码"
              maxlength="128"
              autocomplete="current-password"
            />
          </div>
          <button class="btn-primary mt-2 w-full" type="submit" :disabled="loading || certLoading">
            {{ loading ? '登录中…' : '登 录' }}
          </button>
        </form>

        <div class="relative my-6">
          <div class="absolute inset-0 flex items-center">
            <div class="w-full border-t border-line"></div>
          </div>
          <div class="relative flex justify-center text-xs">
            <span class="bg-white px-2 text-ink-faint">或</span>
          </div>
        </div>

        <button
          class="btn-ghost w-full"
          type="button"
          :disabled="loading || certLoading"
          @click="handleCertLogin"
        >
          {{ certLoading ? '证书登录中…' : '证书登录' }}
        </button>
      </div>
      <p class="mt-6 text-center text-xs text-ink-faint">© 2026 Agent Workspace</p>
    </div>
  </div>
</template>
