import { fileURLToPath, URL } from 'node:url'
import path from 'node:path'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    // 🌟 在 vue() 裡面加上這段設定
    vue({
      template: {
        compilerOptions: {
          isCustomElement: (tag) => tag.startsWith('midi-'),
        },
      },
    }),
    vueDevTools(),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    host: true,
    // 開發時將 /api/* 請求轉發至 FastAPI 後端 (Docker 內部名稱為 backend)
    proxy: {
      '/api': {
        target: 'http://backend:8000',
        changeOrigin: true,
      },
    },
    hmr: {
      clientPort: 5173,
    },
  },
})
