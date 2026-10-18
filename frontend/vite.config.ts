import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
export default defineConfig({ base: process.env.QUERYLAB_BASE_PATH || '/', plugins: [react()], server: { proxy: { '/api': { target: 'http://127.0.0.1:8080', changeOrigin: false } } }, build: { rollupOptions: { output: { manualChunks: { editor: ['@codemirror/state', '@codemirror/view', '@codemirror/lang-sql', '@codemirror/commands', '@codemirror/autocomplete', '@codemirror/language', '@lezer/highlight'] } } } } });
