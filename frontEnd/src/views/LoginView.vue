<script setup lang="ts">
import { onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { toast } from '@/composables/toast'
import { sendRegisterCode, register, certLoginAvailable } from '@/api/auth'
import AppIcon from '@/components/AppIcon.vue'
import BaseModal from '@/components/BaseModal.vue'
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
const certLoginEnabled = ref(false)

const CERT_ERROR_MESSAGES: Record<string, string> = {
  no_client_cert: '未检测到客户端证书，请确认已导入 sign.p12（不要选 encrypt.p12），并在弹窗中选择签名证',
  cert_not_bound: '证书未绑定或不是签名证，请重新导入本次签发的 sign.p12',
  cert_expired: '客户端证书已过期，请重新申请',
  cert_proxy: '证书登录代理边界未就绪，请检查服务端配置',
  account_disabled: '账号已停用',
  cert_login_failed: '证书登录失败',
}

/** 窄屏下左侧主视觉区隐藏，不加载 3D 场景 */
const wideQuery = window.matchMedia('(min-width: 1024px)')
const wide = ref(wideQuery.matches)
function onWideChange(e: MediaQueryListEvent) {
  wide.value = e.matches
}

onMounted(() => {
  wideQuery.addEventListener('change', onWideChange)
  certLoginAvailable().then((data) => {
    certLoginEnabled.value = Boolean(data?.enabled)
  }).catch(() => {
    certLoginEnabled.value = false
  })
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
    toast.error(tr('请输入用户名/邮箱和密码'))
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

// ───────── 注册（与后端 register.code 对齐：60s 重发 / 5 分钟有效）─────────
const CODE_RESEND_SECONDS = 60
const CODE_EXPIRE_MINUTES = 5
const regOpen = ref(false)
const regLoading = ref(false)
const regSuccess = ref(false)
const codeSending = ref(false)
const codeCountdown = ref(0)
let countdownTimer: ReturnType<typeof setInterval> | null = null

const regForm = reactive({
  userName: '',
  email: '',
  passWord: '',
  confirmPassWord: '',
  code: '',
})

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
/** 注册密码：6-12 位，大小写字母 + 数字 + 符号 */
const REGISTER_PASSWORD_RE = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).{6,12}$/
const REGISTER_PASSWORD_HINT = '6-12位，需含大小写字母、数字与符号'

function isValidRegisterPassword(pwd: string) {
  return REGISTER_PASSWORD_RE.test(pwd)
}

function openRegister() {
  regSuccess.value = false
  regOpen.value = true
}

function startCountdown() {
  if (countdownTimer) clearInterval(countdownTimer)
  codeCountdown.value = CODE_RESEND_SECONDS
  countdownTimer = setInterval(() => {
    codeCountdown.value -= 1
    if (codeCountdown.value <= 0 && countdownTimer) {
      clearInterval(countdownTimer)
      countdownTimer = null
    }
  }, 1000)
}

async function handleSendCode() {
  const email = regForm.email.trim()
  if (!email) {
    toast.error(tr('请输入邮箱地址'))
    return
  }
  if (!EMAIL_RE.test(email)) {
    toast.error(tr('邮箱格式不正确'))
    return
  }
  codeSending.value = true
  try {
    await sendRegisterCode(email)
    toast.success(tr('验证码已发送，请查收邮件'))
    startCountdown()
  } catch {
    // 错误提示已由拦截器统一处理
  } finally {
    codeSending.value = false
  }
}

async function handleRegister() {
  const { userName: name, email, passWord: pwd, confirmPassWord, code } = regForm
  if (!name.trim() || !email.trim() || !pwd || !confirmPassWord || !code.trim()) {
    toast.error(tr('请完整填写注册信息'))
    return
  }
  if (!EMAIL_RE.test(email.trim())) {
    toast.error(tr('邮箱格式不正确'))
    return
  }
  if (!isValidRegisterPassword(pwd)) {
    toast.error(tr(REGISTER_PASSWORD_HINT))
    return
  }
  if (pwd !== confirmPassWord) {
    toast.error(tr('两次输入的密码不一致'))
    return
  }
  regLoading.value = true
  try {
    await register({
      userName: name.trim(),
      email: email.trim(),
      passWord: pwd,
      confirmPassWord,
      code: code.trim(),
    })
    regOpen.value = false
    regSuccess.value = true
    // 回填用户名，密码留空让用户重新输入
    userName.value = name.trim()
    passWord.value = ''
    Object.assign(regForm, { userName: '', email: '', passWord: '', confirmPassWord: '', code: '' })
    toast.success(tr('注册成功，请登录'))
  } catch {
    // 错误提示已由拦截器统一处理
  } finally {
    regLoading.value = false
  }
}

onBeforeUnmount(() => {
  if (countdownTimer) clearInterval(countdownTimer)
})
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
        <p v-if="regSuccess" class="login-reg-success" role="status">
          <AppIcon name="check_circle" class="!text-[17px]" />
          {{ tr('注册成功，请使用新账号登录') }}
        </p>

        <form class="mt-8 space-y-4" @submit.prevent="handleLogin">
          <div>
            <label class="form-label" for="username">{{ tr('用户名 / 邮箱') }}</label>
            <input
              id="username"
              v-model="userName"
              class="input login-input"
              type="text"
              :placeholder="tr('请输入用户名或邮箱')"
              maxlength="128"
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

        <template v-if="certLoginEnabled">
          <div class="login-divider"><span>{{ tr('或') }}</span></div>

          <button class="btn-ghost login-cert" type="button" :disabled="loading || certLoading" @click="handleCertLogin">
            <AppIcon name="verified_user" class="!text-[17px]" />
            {{ tr(certLoading ? '证书登录中…' : '证书登录') }}
          </button>
        </template>

        <p class="login-register">
          {{ tr('还没有账号？') }}
          <button type="button" :disabled="loading || certLoading" @click="openRegister">{{ tr('注册账号') }}</button>
        </p>

        <p class="login-foot">Powered by @ADaozz</p>
      </div>
    </section>

    <!-- 注册弹窗：用户名 / 邮箱 / 密码二次确认 / 邮箱验证码 -->
    <BaseModal
      :open="regOpen"
      :title="tr('注册账号')"
      width="420px"
      centered
      surface="page"
      @close="regOpen = false"
    >
      <form class="reg-form" @submit.prevent="handleRegister">
        <p class="reg-lead">{{ tr('填写账号与邮箱，验证后即可进入工作区') }}</p>

        <div class="reg-section">
          <div class="reg-field">
            <label class="form-label" for="reg-username">{{ tr('用户名') }}</label>
            <input
              id="reg-username"
              v-model="regForm.userName"
              class="input reg-input"
              type="text"
              :placeholder="tr('请输入用户名')"
              maxlength="64"
              autocomplete="username"
            />
          </div>
          <div class="reg-field">
            <label class="form-label" for="reg-email">{{ tr('邮箱') }}</label>
            <input
              id="reg-email"
              v-model="regForm.email"
              class="input reg-input"
              type="email"
              :placeholder="tr('请输入邮箱')"
              maxlength="128"
              autocomplete="email"
            />
          </div>
        </div>

        <div class="reg-section">
          <div class="reg-pass-row">
            <div class="reg-field">
              <label class="form-label" for="reg-password">{{ tr('密码') }}</label>
              <input
                id="reg-password"
                v-model="regForm.passWord"
                class="input reg-input"
                type="password"
                :placeholder="tr(REGISTER_PASSWORD_HINT)"
                maxlength="12"
                autocomplete="new-password"
              />
            </div>
            <div class="reg-field">
              <label class="form-label" for="reg-confirm">{{ tr('确认密码') }}</label>
              <input
                id="reg-confirm"
                v-model="regForm.confirmPassWord"
                class="input reg-input"
                type="password"
                :placeholder="tr('再输入一次')"
                maxlength="12"
                autocomplete="new-password"
              />
            </div>
          </div>
        </div>

        <div class="reg-section">
          <div class="reg-field">
            <div class="reg-code-head">
              <label class="form-label" for="reg-code">{{ tr('邮箱验证码') }}</label>
              <span class="reg-code-hint">{{ tr('{n} 分钟内有效').replace('{n}', String(CODE_EXPIRE_MINUTES)) }}</span>
            </div>
            <div class="reg-code-group">
              <input
                id="reg-code"
                v-model="regForm.code"
                class="input reg-input reg-code-input"
                type="text"
                inputmode="numeric"
                :placeholder="tr('6 位数字')"
                maxlength="6"
                autocomplete="one-time-code"
              />
              <button
                class="reg-code-btn"
                type="button"
                :disabled="codeSending || codeCountdown > 0"
                @click="handleSendCode"
              >
                {{ codeCountdown > 0 ? `${codeCountdown}s` : tr(codeSending ? '发送中…' : '获取验证码') }}
              </button>
            </div>
          </div>
        </div>

        <button class="btn-primary reg-submit" type="submit" :disabled="regLoading">
          <span>{{ tr(regLoading ? '注册中…' : '创建账号') }}</span>
        </button>
      </form>
    </BaseModal>
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
  padding: 2.5rem 1.5rem 3.25rem;
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
.login-reg-success {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-top: 1rem;
  padding: 0.75rem 0.875rem;
  border: 1px solid color-mix(in srgb, var(--color-success) 35%, var(--color-line));
  border-radius: 10px;
  background: color-mix(in srgb, var(--color-success) 12%, var(--color-page));
  font-size: 13px;
  font-weight: 500;
  color: var(--color-success);
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
.login-register {
  margin-top: 1.25rem;
  text-align: center;
  font-size: 13px;
  color: var(--color-ink-muted);
}
.login-register button {
  margin-left: 0.25em;
  font-weight: 600;
  color: var(--color-signal);
  transition: color 0.16s;
}
.login-register button:hover:not(:disabled),
.login-register button:focus-visible {
  color: var(--color-signal-bright);
}
.login-register button:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
.reg-form {
  display: flex;
  flex-direction: column;
  gap: 1.15rem;
}
.reg-lead {
  margin: -0.25rem 0 0.15rem;
  font-size: 13px;
  line-height: 1.55;
  color: var(--color-ink-muted);
}
.reg-section {
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
}
.reg-field {
  min-width: 0;
}
.reg-input {
  height: 2.625rem;
}
.reg-pass-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.75rem;
}
.reg-code-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 0.75rem;
}
.reg-code-head .form-label {
  margin-bottom: 0.4rem;
}
.reg-code-hint {
  font-size: 11.5px;
  letter-spacing: 0.02em;
  color: var(--color-ink-faint);
  white-space: nowrap;
}
.reg-code-group {
  display: flex;
  align-items: stretch;
  border: 1px solid var(--color-line);
  border-radius: 8px;
  background: var(--field);
  overflow: hidden;
  transition:
    border-color 0.16s,
    box-shadow 0.16s;
}
.reg-code-group:focus-within {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--color-signal) 16%, transparent);
}
.reg-code-input {
  flex: 1;
  min-width: 0;
  border: 0 !important;
  border-radius: 0 !important;
  box-shadow: none !important;
  background: transparent !important;
  letter-spacing: 0.18em;
  font-variant-numeric: tabular-nums;
}
.reg-code-btn {
  flex-shrink: 0;
  min-width: 6.75rem;
  padding: 0 0.875rem;
  border: 0;
  border-left: 1px solid var(--color-line);
  background: color-mix(in srgb, var(--color-signal) 12%, transparent);
  color: var(--color-signal);
  font-size: 12.5px;
  font-weight: 600;
  letter-spacing: 0.02em;
  transition:
    background-color 0.16s,
    color 0.16s,
    opacity 0.16s;
}
.reg-code-btn:hover:not(:disabled) {
  background: color-mix(in srgb, var(--color-signal) 20%, transparent);
  color: var(--color-signal-bright);
}
.reg-code-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.reg-submit {
  margin-top: 0.15rem;
  width: 100%;
  height: 2.75rem;
  font-size: 15px;
  letter-spacing: 0.12em;
}
@media (max-width: 480px) {
  .reg-pass-row {
    grid-template-columns: 1fr;
  }
}
.login-foot {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 1.15rem;
  margin: 0;
  text-align: center;
  font-family: var(--font-mono);
  font-size: 10.5px;
  letter-spacing: 0.12em;
  color: var(--color-ink-faint);
  pointer-events: none;
}

@media (max-width: 1023px) {
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
