import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

// Builds into ../app/static/dist, which app/web.py mounts as StaticFiles and
// serves index.html from for every /courses* page. `base: '/static/dist/'`
// keeps the built asset URLs correct once served from that mount point.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  base: '/static/dist/',
  build: {
    outDir: '../app/static/dist',
    emptyOutDir: true,
  },
  server: {
    port: 9001,
    proxy: {
      // Dev-time only: `npm run dev` runs on :9001, the FastAPI backend on
      // :9000 (see ../README.md). Proxy both the session-authenticated web
      // API and the SSO cookie exchange so `npm run dev` behaves the same
      // as the production build served by FastAPI itself.
      '/web-api': 'http://localhost:9000',
      '/sso': 'http://localhost:9000',
    },
  },
});
