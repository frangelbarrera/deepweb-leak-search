import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import path from 'path';
import { defineConfig } from 'vite';

export default defineConfig(() => {
  return {
    plugins: [react(), tailwindcss()],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, '.'),
      },
    },
    server: {
      proxy: {
        '/api': 'http://127.0.0.1:8000',
        '/dashboard': 'http://127.0.0.1:8000',
        '/docs': 'http://127.0.0.1:8000',
        '/openapi.json': 'http://127.0.0.1:8000',
      },
    },
  };
});
