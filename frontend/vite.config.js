import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 3000,
    watch: {
      usePolling: true
    },
    hmr: {
      port: 3000,
      host: 'localhost'
    }
  },
  preview: {
    host: '0.0.0.0',
    port: 3000
  }
})
