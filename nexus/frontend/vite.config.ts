/// <reference types="vitest/config" />
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

const backend = process.env.NEXUS_BACKEND_URL ?? 'http://127.0.0.1:8000';

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    host: '127.0.0.1',
    port: 5173,
    proxy: { '/api': { target: backend, changeOrigin: false } },
  },
  preview: {
    host: '127.0.0.1',
    port: 4173,
    proxy: { '/api': { target: backend, changeOrigin: false } },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    css: false,
  },
});
