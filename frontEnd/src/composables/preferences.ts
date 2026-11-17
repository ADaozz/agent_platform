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

/** 平台外壳与已接入 i18n 的设置页英文文案 */
const EN: Record<string, string> = {
  'Agent 对话': 'Agent Chat',
  平台设置: 'Platform Settings',
  模型配置: 'Model Settings',
  平台能力: 'Capabilities',
  打开导航: 'Open navigation',
  用量仪表盘: 'Usage Dashboard',
  // 平台能力
  'Agent 当前挂载的工具与 Skill；调整仅影响新建的对话':
    'Tools and skills mounted for agents; changes apply only to new chats',
  工具: 'Tools',
  '正在加载平台能力…': 'Loading capabilities…',
  '只读视图：仅管理员可以调整挂载': 'Read-only: only administrators can change mounts',
  内核工具: 'Core tools',
  '平台内置，具有副作用的操作仍按会话权限请求审批':
    'Built into the platform; side-effecting actions still require session approval',
  扩展工具: 'Additional tools',
  平台注册的结构化工具: 'Structured tools registered by the platform',
  'Agent 按需加载的能力包，例如 Word 与 PPT 文档生成':
    'On-demand capability packs for agents, such as Word and PowerPoint generation',
  '暂无已安装的 Skill': 'No skills installed',
  内置扩展: 'Built-in',
  已安装: 'Installed',
  所属扩展功能已停用: 'Parent feature is disabled',
  '需同时挂载「子 Agent 委派」才会生效': 'Also mount “Delegate to subagent” for this to take effect',
  '{n} 项未保存的变更': '{n} unsaved change(s)',
  '变更仅对新建对话生效，进行中的对话保留创建时的配置':
    'Changes apply to new chats only; in-progress chats keep their original mounts',
  重置: 'Reset',
  '保存中…': 'Saving…',
  保存挂载: 'Save mounts',
  '平台能力已更新，新建对话生效': 'Capabilities updated; applies to new chats',
  列出文件: 'List files',
  列出线程工作区中的目录内容: 'List directory contents in the thread workspace',
  读取文件: 'Read files',
  按行读取工作区文件: 'Read workspace files by line',
  写入文件: 'Write files',
  创建或覆盖工作区文件: 'Create or overwrite workspace files',
  编辑文件: 'Edit files',
  对文件做精确的字符串替换: 'Exact string replacement in files',
  删除文件: 'Delete files',
  删除工作区中的文件: 'Delete files in the workspace',
  文件匹配: 'Find files',
  按通配符查找文件路径: 'Find file paths by glob pattern',
  搜索内容: 'Search contents',
  在文件中按正则搜索文本: 'Search file text with regular expressions',
  执行命令: 'Run commands',
  '在 Bubblewrap 沙箱内运行 Shell 命令': 'Run shell commands inside the Bubblewrap sandbox',
  '子 Agent 委派': 'Delegate to subagent',
  '派生隔离的子 Agent 并等待其结果': 'Spawn an isolated subagent and wait for its result',
  后台子任务: 'Background subagent',
  '在后台运行子 Agent，完成后自动回报结果': 'Run a subagent in the background and report when done',
  子任务日志: 'Subagent logs',
  查看委派任务的执行摘要: 'View execution summaries for delegated tasks',
  向用户提问: 'Ask the user',
  暂停执行并请求用户补充信息: 'Pause execution and ask the user for more information',
  联网搜索: 'Web search',
  通过搜索引擎检索公开信息: 'Search public information via search engines',
  抓取网页: 'Fetch web page',
  读取指定网址的页面内容: 'Read the content of a given URL',
  '按天 / 会话统计模型 Tokens 与估算费用，数据来自会话生成指标。':
    'Token and estimated cost by day or session, from generation metrics.',
  '按天统计模型 Tokens 与估算费用，数据来自会话生成指标。':
    'Daily token usage and estimated cost from generation metrics.',
  按天: 'By day',
  按会话: 'By session',
  刷新: 'Refresh',
  '加载遥测数据…': 'Loading telemetry…',
  '总 Tokens': 'Total tokens',
  '输入 / 输出': 'Input / output',
  估算费用: 'Est. cost',
  '调用 / 会话': 'Calls / sessions',
  日用量轨迹: 'Daily usage',
  会话用量排行: 'Session ranking',
  '薄荷绿 = Tokens · 航天橙 = 估算费用': 'Mint = tokens · Signal = estimated cost',
  '条形长度 = Tokens · 右侧标注估算费用': 'Bar length = tokens · labels show estimated cost',
  会话明细: 'Session details',
  暂无会话用量: 'No session usage yet',
  '按 DeepSeek 官方刊例估算（缓存命中×峰谷），非账单':
    'Estimated from DeepSeek list prices (cache × peak/off-peak), not an invoice',
  'DeepSeek Flash 刊例（元/百万 tok）': 'DeepSeek Flash list price (CNY / 1M tok)',
  空闲: 'Off-peak',
  高峰: 'Peak',
  缓存命中: 'Cache hit',
  缓存未命中: 'Cache miss',
  输出: 'Output',
  '峰时段：北京时间工作日 09:00–12:00、14:00–18:00；周末与法定节假日全天空闲':
    'Peak: Beijing weekdays 09:00–12:00 & 14:00–18:00; weekends and PRC holidays are off-peak',
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
  '近 7 天暂无对话': 'No chats in the last 7 days',
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
