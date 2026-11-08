import { defineConfig } from 'vite';
import { fileURLToPath } from 'node:url';
const root = fileURLToPath(new URL('.', import.meta.url));
const headers = { 'Cache-Control': 'no-store', 'Referrer-Policy': 'no-referrer', 'X-Content-Type-Options': 'nosniff' };
export default defineConfig({
  base: './', publicDir: false,
  server: { host: '127.0.0.1', port: 5173, strictPort: true, open: false, cors: false,
    allowedHosts: ['127.0.0.1', 'localhost'], headers, fs: { strict: true, allow: [root] } },
  preview: { host: '127.0.0.1', port: 4173, strictPort: true, open: false, cors: false,
    allowedHosts: ['127.0.0.1', 'localhost'], headers },
  build: { target: 'es2022', sourcemap: false, emptyOutDir: false, modulePreload: false, manifest: 'vite-manifest.json',
    rollupOptions: { output: { entryFileNames: 'assets/console.js', chunkFileNames: 'assets/[name]-[hash].js', assetFileNames: 'assets/[name]-[hash][extname]' } } }
});
