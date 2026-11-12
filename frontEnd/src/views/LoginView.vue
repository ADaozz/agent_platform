<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { toast } from '@/composables/toast'
import type { LoginResult } from '@/types'
import AppIcon from '@/components/AppIcon.vue'
import BrandMark from '@/components/BrandMark.vue'
import OrbitDial from '@/components/OrbitDial.vue'
import SpaceField from '@/components/SpaceField.vue'
import TapeMask from '@/components/TapeMask.vue'
import TopbarControls from '@/components/TopbarControls.vue'
import { tr } from '@/composables/preferences'

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
    toast.error(CERT_ERROR_MESSAGES[certError] ? tr(CERT_ERROR_MESSAGES[certError]) : decodeURIComponent(certError))
    router.replace({ path: '/login' })
  }

  const match = location.hash.match(/^#certLogin=(.+)$/)
  if (!match) return

  try {
    const data = parseLoginPayload(decodeBase64Url(match[1]!))
    auth.persistLogin(data)
    history.replaceState(null, '', location.pathname + location.search)
    toast.success(tr('证书登录成功'))
    const redirect = (route.query.redirect as string) || '/'
    router.replace(redirect)
  } catch {
    history.replaceState(null, '', location.pathname)
    toast.error(tr('证书登录失败'))
  }
})

async function handleLogin() {
  if (!userName.value.trim() || !passWord.value) {
    toast.error(tr('请输入用户名和密码'))
    return
  }
  loading.value = true
  try {
    await auth.login(userName.value.trim(), passWord.value)
    toast.success(tr('登录成功'))
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
  <div class="login">
    <!-- 左：任务控制台主视觉（恒定碳黑） -->
    <section class="login-hero">
      <SpaceField />
      <div class="login-hero-top">
        <BrandMark :size="36" />
      </div>

      <div class="login-dial"><div class="login-dial-tape"><OrbitDial /></div></div>

      <div class="login-hero-copy">
        <div class="login-wordmark" aria-hidden="true">DEEP<br />AGENT</div>
        <p class="login-slogan">{{ tr('智能体工作平台 · 对话、执行与交付在同一座控制台完成') }}</p>
      </div>

      <p class="login-credit">
        Powered by
        <a href="https://github.com/ADaozz" target="_blank" rel="noopener noreferrer">@ADaozz</a>
      </p>
      <TapeMask />
    </section>

    <!-- 右：身份验证表单（跟随主题） -->
    <section class="login-pane dot-grid">
      <TopbarControls class="login-controls" />
      <div class="login-form-wrap">
        <div class="login-mobile-brand">
          <BrandMark :size="40" />
        </div>
        <h1 class="login-title">Agent Platform</h1>
        <p class="login-sub">{{ tr('使用平台账号或客户端证书进入工作区') }}</p>

        <form class="mt-8 space-y-4" @submit.prevent="handleLogin">
          <div>
            <label class="form-label" for="username">{{ tr('用户名') }}</label>
            <input
              id="username"
              v-model="userName"
              class="input login-input"
              type="text"
              :placeholder="tr('请输入用户名')"
              maxlength="64"
              autocomplete="username"
            />
          </div>
          <div>
            <label class="form-label" for="password">{{ tr('密码') }}</label>
            <input
              id="password"
              v-model="passWord"
              class="input login-input"
              type="password"
              :placeholder="tr('请输入密码')"
              maxlength="128"
              autocomplete="current-password"
            />
          </div>
          <button class="btn-primary login-submit" type="submit" :disabled="loading || certLoading">
            <span>{{ tr(loading ? '登录中…' : '登 录') }}</span>
          </button>
        </form>

        <div class="login-divider"><span>{{ tr('或') }}</span></div>

        <button class="btn-ghost login-cert" type="button" :disabled="loading || certLoading" @click="handleCertLogin">
          <AppIcon name="verified_user" class="!text-[17px]" />
          {{ tr(certLoading ? '证书登录中…' : '证书登录') }}
        </button>

        <p class="login-foot">© 2026 Agent Workspace</p>
      </div>
    </section>
  </div>
</template>

<style scoped>
.login {
  display: grid;
  min-height: 100%;
  grid-template-columns: minmax(0, 1.25fr) minmax(380px, 1fr);
  background-color: var(--color-page);
}

.login-hero {
  position: relative;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  overflow: hidden;
  padding: 2.5rem 3rem;
  background-color: #131312;
  border-right: 1px solid #302f2a;
  color: #f2ead9;
}
.login-hero-top {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.login-dial {
  position: absolute;
  top: 50%;
  right: -18%;
  width: min(92vh, 78%);
  aspect-ratio: 1;
  transform: translateY(-50%);
  color: #f2ead9;
  opacity: 0.9;
  /* 录像带的低饱和 + 亮部光渗 */
  filter: saturate(0.82) drop-shadow(0 0 6px rgb(226 133 79 / 0.22));
}
/* 走带干扰条扫过时，星盘随之错位一帧并出现轻微色散 */
.login-dial-tape {
  height: 100%;
  animation: login-tape-jitter 11s steps(1) infinite;
}
.login-hero :deep(.space) {
  filter: saturate(0.8);
}
@keyframes login-tape-jitter {
  0%,
  52.6%,
  100% {
    transform: none;
    filter: none;
  }
  50.4% {
    transform: translateX(3px);
    filter: drop-shadow(2px 0 0 rgb(200 73 64 / 0.55)) drop-shadow(-2px 0 0 rgb(152 188 177 / 0.45));
  }
  51% {
    transform: translateX(-2px);
    filter: drop-shadow(-1.5px 0 0 rgb(200 73 64 / 0.4)) drop-shadow(1.5px 0 0 rgb(152 188 177 / 0.35));
  }
  51.8% {
    transform: translateX(1px);
    filter: none;
  }
}
.login-hero-copy {
  position: relative;
  z-index: 1;
  margin-top: auto;
  padding-bottom: 2.5rem;
}
.login-wordmark {
  font-family: var(--font-display);
  font-size: clamp(64px, 9vw, 132px);
  font-weight: 700;
  line-height: 0.86;
  letter-spacing: 0.02em;
  text-shadow: 0 0 22px rgb(226 133 79 / 0.2);
}
.login-slogan {
  margin-top: 1.5rem;
  max-width: 30em;
  font-size: 14px;
  line-height: 1.7;
  color: #b9b1a0;
}

.login-credit {
  position: relative;
  z-index: 1;
  padding-top: 1.25rem;
  border-top: 1px solid #302f2a;
  font-size: 12.5px;
  letter-spacing: 0.04em;
  color: #8f8878;
}
.login-credit a {
  margin-left: 0.25em;
  font-weight: 600;
  color: #f2ead9;
  transition: color 0.16s;
}
.login-credit a:hover,
.login-credit a:focus-visible {
  color: #e2854f;
}

.login-pane {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2.5rem 1.5rem;
}
.login-controls {
  position: absolute;
  top: 0.75rem;
  right: 1.5rem;
}
.login-form-wrap {
  width: 100%;
  max-width: 22.5rem;
}
.login-mobile-brand {
  display: none;
  margin-bottom: 2rem;
}
.login-title {
  font-size: 30px;
  line-height: 1.15;
  font-weight: 700;
  letter-spacing: 0.01em;
  color: var(--color-ink);
}
.login-sub {
  margin-top: 0.5rem;
  font-size: 13px;
  color: var(--color-ink-muted);
}
.login-input {
  height: 2.625rem;
}
.login-submit {
  margin-top: 0.5rem;
  width: 100%;
  height: 2.75rem;
  font-size: 15px;
  letter-spacing: 0.12em;
}
.login-divider {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin: 1.5rem 0;
  font-size: 12px;
  color: var(--color-ink-faint);
}
.login-divider::before,
.login-divider::after {
  content: '';
  height: 1px;
  flex: 1;
  background: var(--color-line);
}
.login-cert {
  width: 100%;
  height: 2.625rem;
}
.login-foot {
  margin-top: 2.5rem;
  text-align: center;
  font-family: var(--font-mono);
  font-size: 10.5px;
  letter-spacing: 0.12em;
  color: var(--color-ink-faint);
}

@media (prefers-reduced-motion: reduce) {
  .login-dial-tape {
    animation: none;
  }
}
@media (max-width: 900px) {
  .login {
    grid-template-columns: minmax(0, 1fr);
  }
  .login-hero {
    display: none;
  }
  .login-mobile-brand {
    display: block;
  }
}
</style>
