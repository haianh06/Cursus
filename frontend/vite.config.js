import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    host: true,
    // Fail loudly on a taken port instead of silently drifting to 5174 —
    // backend CORS (src/main.py, settings.cors_origins) only allows 5173,
    // so a silent drift means every API call breaks with an opaque
    // "server not responding" banner instead of a clear "port in use" error
    // at startup that tells you to kill whatever's already listening.
    strictPort: true
  }
})
