import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import { validateAccountConfig } from './config/accounts.mjs';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), 'VITE_');
  validateAccountConfig(env.VITE_SUPABASE_URL?.trim(), env.VITE_SUPABASE_PUBLISHABLE_KEY?.trim());
  return {
    base: process.env.QUERYLAB_BASE_PATH || '/',
    plugins: [react()],
    server: { proxy: { '/api': { target: 'http://127.0.0.1:8080', changeOrigin: false } } },
    build: { rollupOptions: { output: { manualChunks: {
      editor: ['@codemirror/state', '@codemirror/view', '@codemirror/lang-sql', '@codemirror/commands', '@codemirror/autocomplete', '@codemirror/language', '@lezer/highlight'],
      accounts: ['@supabase/supabase-js'],
    } } } },
  };
});
