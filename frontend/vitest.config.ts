import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  test: {
    // 全局配置
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],

    // 覆盖率配置
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html', 'lcov', 'json-summary'],
      exclude: [
        'node_modules/',
        'src/test/',
        '**/*.d.ts',
        '**/*.config.*',
        '**/mockData',
        'src/main.tsx',
        'src/vite-env.d.ts',
      ],
      // 覆盖率阈值（生产级别标准）
      thresholds: {
        statements: 80,
        branches: 75,
        functions: 80,
        lines: 80,
      },
    },

    // 测试文件匹配
    include: ['src/**/*.{test,spec}.{ts,tsx}'],
    exclude: ['node_modules/', 'dist/', 'e2e/'],

    // 超时配置
    testTimeout: 10000,
    hookTimeout: 10000,
    teardownTimeout: 10000,

    // 隔离和并发
    isolate: true,
    pool: 'threads',
    poolOptions: {
      threads: {
        singleThread: false,
        minThreads: 1,
        maxThreads: 4,
      },
    },

    // 报告器
    reporters: ['verbose', 'json', 'html'],
    outputFile: {
      json: './coverage/test-results.json',
      html: './coverage/test-report.html',
    },

    // 监听模式配置
    watch: {
      ignore: ['**/node_modules/**', '**/dist/**', '**/coverage/**'],
    },
  },

  // 路径解析（与vite.config.ts保持一致）
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      '@/components': path.resolve(__dirname, './src/components'),
      '@/pages': path.resolve(__dirname, './src/pages'),
      '@/services': path.resolve(__dirname, './src/services'),
      '@/utils': path.resolve(__dirname, './src/utils'),
      '@/hooks': path.resolve(__dirname, './src/hooks'),
      '@/test': path.resolve(__dirname, './src/test'),
      '@/types': path.resolve(__dirname, './src/types'),
      '@/constants': path.resolve(__dirname, './src/constants'),
      '@/config': path.resolve(__dirname, './src/config'),
    },
  },
})
