import { ref, watch } from 'vue'

export type Theme = 'light' | 'dark'
export type Locale = 'zh' | 'en'

const THEME_KEY = 'itam-theme'
const LOCALE_KEY = 'itam-locale'

function saved(key: string) {
  try {
    return localStorage.getItem(key)
  } catch {
    return null
  }
}

function persist(key: string, value: string) {
  try {
    localStorage.setItem(key, value)
  } catch {
    /* 无法持久化时偏好仍在本次会话内生效 */
  }
}

/** 全站主题，默认黑夜模式；index.html 中的内联脚本用同一个键提前设置，避免首屏闪白 */
export const theme = ref<Theme>(saved(THEME_KEY) === 'light' ? 'light' : 'dark')
export const locale = ref<Locale>(saved(LOCALE_KEY) === 'en' ? 'en' : 'zh')

export function toggleTheme() {
  theme.value = theme.value === 'dark' ? 'light' : 'dark'
}

export function toggleLocale() {
  locale.value = locale.value === 'zh' ? 'en' : 'zh'
}

watch(
  theme,
  (value) => {
    document.documentElement.dataset.theme = value
    document.documentElement.style.colorScheme = value
    persist(THEME_KEY, value)
  },
  { immediate: true },
)

watch(
  locale,
  (value) => {
    document.documentElement.lang = value === 'zh' ? 'zh-CN' : 'en'
    persist(LOCALE_KEY, value)
  },
  { immediate: true },
)

/** 平台外壳（菜单、页头、面包屑）的英文文案；管理页面正文暂未翻译 */
const EN: Record<string, string> = {
  'Agent 对话': 'Agent Chat',
  平台设置: 'Platform Settings',
  模型配置: 'Model Settings',
  用户管理: 'Users',
  角色管理: 'Roles',
  登录设备管理: 'Login Devices',
  我的证书: 'My Certificates',
  证书管理: 'Certificates',
  管理员: 'Administrator',
  普通用户: 'User',
  退出登录: 'Sign out',
  切换语言: 'Switch language',
  切换为白天模式: 'Switch to light mode',
  切换为黑夜模式: 'Switch to dark mode',
  新建对话: 'New chat',
  历史对话: 'History',
  全局文件: 'All files',
  最近对话: 'Recent chats',
  搜索对话: 'Search chats',
  删除对话: 'Delete chat',
  暂无对话: 'No chats yet',
  确认操作: 'Confirm',
  取消: 'Cancel',
  确定: 'OK',
  '处理中…': 'Working…',
  // 登录页
  '智能体工作平台 · 对话、执行与交付在同一座控制台完成': 'One console for conversation, execution and delivery',
  使用平台账号或客户端证书进入工作区: 'Sign in with your platform account or client certificate',
  用户名: 'Username',
  请输入用户名: 'Enter your username',
  密码: 'Password',
  请输入密码: 'Enter your password',
  '登 录': 'Sign in',
  '登录中…': 'Signing in…',
  或: 'or',
  证书登录: 'Sign in with certificate',
  '证书登录中…': 'Signing in with certificate…',
  证书登录成功: 'Signed in with certificate',
  证书登录失败: 'Certificate sign-in failed',
  请输入用户名和密码: 'Enter your username and password',
  登录成功: 'Signed in',
  '未检测到客户端证书，请确认已导入 sign.p12': 'No client certificate found. Make sure sign.p12 is imported.',
  // 注册
  '还没有账号？': "Don't have an account?",
  注册账号: 'Create account',
  邮箱: 'Email',
  请输入邮箱: 'Enter your email',
  确认密码: 'Confirm password',
  请再次输入密码: 'Re-enter your password',
  验证码: 'Verification code',
  请输入验证码: 'Enter the code',
  发送验证码: 'Send code',
  '发送中…': 'Sending…',
  '注册中…': 'Signing up…',
  '注 册': 'Sign up',
  '验证码已发送，请查收邮件': 'Code sent. Check your inbox.',
  '注册成功，请登录': 'Account created. Please sign in.',
  '注册成功，请使用新账号登录': 'Account created. Sign in with your new account.',
  请输入邮箱地址: 'Enter your email address',
  邮箱格式不正确: 'Invalid email format',
  请完整填写注册信息: 'Please fill in all fields',
  密码至少6位: 'Password must be at least 6 characters',
  两次输入的密码不一致: 'Passwords do not match',
  '验证码发送后 {n} 分钟内有效': 'The code is valid for {n} minutes',
  '填写账号与邮箱，验证后即可进入工作区': 'Create an account with email verification to enter the workspace',
  '至少 6 位': 'At least 6 characters',
  再输入一次: 'Enter again',
  邮箱验证码: 'Email code',
  '{n} 分钟内有效': 'Valid for {n} min',
  '6 位数字': '6-digit code',
  获取验证码: 'Get code',
  创建账号: 'Create account',
}

export function tr(text: string) {
  return locale.value === 'en' ? (EN[text] ?? text) : text
}
