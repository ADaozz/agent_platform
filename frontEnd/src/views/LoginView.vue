<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { toast } from '@/composables/toast'
import AppIcon from '@/components/AppIcon.vue'
import BrandMark from '@/components/BrandMark.vue'
import TapeMask from '@/components/TapeMask.vue'
import LoginScene from '@/components/LoginScene.vue'
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

/** 窄屏下左侧主视觉区隐藏，不加载 3D 场景 */
const wideQuery = window.matchMedia('(min-width: 901px)')
const wide = ref(wideQuery.matches)
function onWideChange(e: MediaQueryListEvent) {
  wide.value = e.matches
}

onMounted(() => {
  wideQuery.addEventListener('change', onWideChange)
  const certError = route.query.certError as string | undefined
  if (certError) {
    toast.error(CERT_ERROR_MESSAGES[certError] ? tr(CERT_ERROR_MESSAGES[certError]) : decodeURIComponent(certError))
    router.replace({ path: '/login' })
  }
})

onBeforeUnmount(() => {
  wideQuery.removeEventListener('change', onWideChange)
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
    <!-- 整页背景层：左侧主视觉区完整露出，右侧透过磨砂面板隐约可见 -->
    <div class="login-backdrop" aria-hidden="true">
      <LoginScene v-if="wide" />
      <div class="login-scrim"></div>
      <TapeMask />
    </div>

    <!-- 左：任务控制台主视觉 -->
    <section class="login-hero">
      <div class="login-hero-top">
        <BrandMark :size="36" />
      </div>

      <div class="login-hero-copy">
        <div class="login-wordmark" aria-hidden="true">DEEP<br />AGENT</div>
        <p class="login-slogan">{{ tr('智能体工作平台 · 对话、执行与交付在同一座控制台完成') }}</p>
      </div>

      <p class="login-credit">
        Powered by
        <a href="https://github.com/ADaozz" target="_blank" rel="noopener noreferrer">@ADaozz</a>
      </p>
    </section>

    <!-- 右：身份验证表单（跟随主题） -->
    <section class="login-pane">
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
  position: relative;
  isolation: isolate;
  display: grid;
  min-height: 100%;
  grid-template-columns: minmax(0, 1.25fr) minmax(380px, 1fr);
}
.login-backdrop {
  position: absolute;
  inset: 0;
  z-index: -1;
  overflow: hidden;
  background: #181818 url('@/assets/login/login-bg.webp') center / cover no-repeat;
}
/* 走廊背景偏亮：压暗左下方大字与标语、左上角 logo 所在的区域，保证奶白文字可读 */
.login-scrim {
  position: absolute;
  inset: 0;
  background:
    linear-gradient(0deg, rgb(16 16 15 / 0.86) 0%, rgb(16 16 15 / 0.5) 34%, transparent 62%),
    linear-gradient(90deg, rgb(16 16 15 / 0.6) 0%, transparent 46%),
    linear-gradient(180deg, rgb(16 16 15 / 0.5) 0%, transparent 20%);
}

.login-hero {
  position: relative;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: 2.5rem 3rem;
  color: #f5eddc;
}
.login-hero-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.login-hero-top :deep(.brand-mark) {
  filter: brightness(1.15) saturate(1.15);
}
.login-hero-copy {
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
  padding-top: 1.25rem;
  border-top: 1px solid #403c35;
  font-size: 12.5px;
  letter-spacing: 0.04em;
  color: #8f8878;
}
.login-credit a {
  margin-left: 0.25em;
  font-weight: 600;
  color: #f5eddc;
  transition: color 0.16s;
}
.login-credit a:hover,
.login-credit a:focus-visible {
  color: #f36b18;
}

.login-pane {
  --login-glass: color-mix(in srgb, var(--color-page) 86%, transparent);
  position: relative;
  z-index: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2.5rem 1.5rem;
}
:global(:root[data-theme='dark']) .login-pane {
  --login-glass: color-mix(in srgb, var(--color-page) 66%, transparent);
}
/* 磨砂玻璃：向左伸进主视觉区，用遮罩从全透明渐变到不透明，替代硬分界线 */
.login-pane::before {
  content: '';
  position: absolute;
  inset: 0 0 0 -8rem;
  z-index: -1;
  pointer-events: none;
  background:
    radial-gradient(var(--grid-dot) 1px, transparent 1px) 0 0 / 22px 22px,
    var(--login-glass);
  -webkit-backdrop-filter: blur(20px) saturate(1.15);
  backdrop-filter: blur(20px) saturate(1.15);
  -webkit-mask-image: linear-gradient(90deg, transparent, #000 10rem);
  mask-image: linear-gradient(90deg, transparent, #000 10rem);
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

@media (max-width: 900px) {
  .login {
    grid-template-columns: minmax(0, 1fr);
  }
  .login-hero {
    display: none;
  }
  .login-pane::before {
    left: 0;
    -webkit-mask-image: none;
    mask-image: none;
  }
  .login-mobile-brand {
    display: block;
  }
}
</style>
