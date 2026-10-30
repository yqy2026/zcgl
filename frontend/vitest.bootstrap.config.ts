import path from 'node:path';
import { defineConfig } from 'vitest/config';

export default defineConfig({
  resolve: { alias: { '@': path.resolve(__dirname, 'src') } },
  test: {
    globals: true,
    environment: 'jsdom',
    pool: 'forks',
    maxWorkers: 1,
    sequence: { setupFiles: 'list' },
    setupFiles: ['./src/test/mswBootstrap.mock.ts', './src/test/setup.ts'],
    include: ['src/test/mswBootstrap.probe.ts'],
    // Import takes longer than this on purpose; only listen belongs in the hook.
    hookTimeout: 50,
    reporters: ['verbose'],
  },
});
