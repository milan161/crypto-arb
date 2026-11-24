import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'

// 端口统一在程序根目录 .env 里配置（本文件在 src/frontend，程序根 = ../..）
export default defineConfig(() => {
  const env = loadEnv('', '../..', 'DASH_')
  const backend = env.DASH_BACKEND_PORT || '8105'
  const frontend = Number(env.DASH_FRONTEND_PORT || '5185')
  return {
    plugins: [vue()],
    server: {
      port: frontend,
      strictPort: true, // 端口被占用就报错退出，不会悄悄换端口
      proxy: { '/api': 'http://127.0.0.1:' + backend },
    },
  }
})
