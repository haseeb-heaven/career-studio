import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  // Load env from root project dir (one level up from frontend/)
  const env = loadEnv(mode, '../', '')

  const host = env.FRONTEND_HOST || 'localhost'
  const port = parseInt(env.FRONTEND_PORT || '5173', 10)

  return {
    plugins: [react()],
    server: {
      host,
      port,
    },
  }
})
