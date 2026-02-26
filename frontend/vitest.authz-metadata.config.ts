import path from 'path';
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vitest/config';

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'node',
    include: ['src/routes/__tests__/AppRoutes.authz-metadata.test.ts'],
    pool: 'forks',
    maxWorkers: 1,
    minWorkers: 1,
    setupFiles: [],
    reporters: ['verbose'],
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
});
