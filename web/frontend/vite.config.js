import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // Proxy /api to Flask in development so there's no CORS friction.
    proxy: { '/api': { target: 'http://localhost:5000', changeOrigin: true } },
  },
  build: {
    // Route-level code splitting keeps the initial bundle small; recharts
    // only downloads for users who open the admin dashboard.
    rollupOptions: {
      output: { manualChunks: { charts: ['recharts'] } },
    },
  },
});
