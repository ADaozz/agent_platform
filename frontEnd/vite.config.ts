import { fileURLToPath, URL } from 'node:url'

import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd())
  // WSL 中访问 Windows 侧后端须用宿主机 IP（勿用 127.0.0.1）
  const proxyTarget = env.VITE_PROXY_TARGET || 'http://172.21.16.1:8080'

  return {
    plugins: [
      vue(),
      vueDevTools(),
      tailwindcss(),
    ],
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url)),
      },
    },
    server: {
      // WSL 下 /mnt 挂载的 Windows 盘收不到文件变更通知，只能轮询
      watch: { usePolling: process.cwd().startsWith('/mnt/') },
      // 前端请求统一带 /api 前缀（见 VITE_API_BASE），代理时剥掉前缀后转发给后端，
      // 避免后端路径（/login、/dashboard 等）与 SPA 页面路由冲突
      proxy: {
        '/api': {
          target: proxyTarget,
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/api/, ''),
        },
      },
    },
  }
})
