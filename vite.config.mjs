import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Docker Desktop's Windows bind mounts don't reliably emit inotify events,
// so Vite's default file watcher misses edits and keeps serving a stale build.
export default defineConfig({
  plugins: [react()],
  server: {
    watch: {
      usePolling: true,
      interval: 300,
    },
  },
});
