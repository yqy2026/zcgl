/**
 * Vitest 配置文件
 *
 * 测试框架配置，包含：
 * - MSW集成（通过setupFiles）
 * - 覆盖率配置（分阶段目标：50% → 70% → 85%）
 * - TypeScript路径解析
 * - 并行执行和性能优化
 */

import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],

  test: {
    // =============================================================================
    // 全局配置
    // =============================================================================
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    root: '.',

    // 测试文件匹配
    include: ['src/**/*.{test,spec}.{ts,tsx}'],
    exclude: ['node_modules/', 'dist/', 'e2e/', 'src/e2e/'],

    // 超时配置（毫秒）
    testTimeout: 10000,
    hookTimeout: 10000,
    teardownTimeout: 10000,

    // 并发和隔离
    isolate: true,
    pool: 'threads',
    singleThread: false,

    // 报告器
    reporters: ['verbose', 'json', 'html'],
    outputFile: {
      json: './coverage/test-results.json',
      html: './coverage/test-report.html',
    },

    // 监听模式
    watch: {
      ignore: ['**/node_modules/**', '**/dist/**', '**/coverage/**'],
    },

    // =============================================================================
    // 覆盖率配置（分阶段目标）
    // =============================================================================
    coverage: {
      provider: 'v8',
      reportsDirectory: './coverage',

      // 报告格式
      reporter: [
        'text', // 终端文本输出
        'text-summary', // 终端摘要
        'json', // JSON格式
        'json-summary', // JSON摘要（CI友好）
        'html', // HTML可视化报告
        'lcov', // LCOV格式
        'lcovonly', // 仅LCOV文件
      ],

      // 排除文件（不统计覆盖率）
      exclude: [
        'node_modules/',
        'src/test/',
        'src/mocks/', // Mock数据
        '**/*.d.ts',
        '**/*.config.*',
        '**/mockData',
        'src/main.tsx', // 应用入口
        'src/vite-env.d.ts',
        '**/__tests__/**',
        '**/*.test.{ts,tsx}',
        '**/*.spec.{ts,tsx}',
      ],

      // 包含文件（统计覆盖率）
      include: ['src/**/*.{ts,tsx}'],

      // 覆盖率阈值（匹配TESTING_STANDARDS.md目标）
      // Target: 75% (lines, functions, statements) / 70% (branches)
      // Note: Thresholds disabled here - CI workflow uses incremental_coverage_check.py
      // TODO: Re-enable thresholds once coverage improves
      /*
      thresholds: {
        lines: 75,      // 从50%提升到75%
        functions: 75,  // 从50%提升到75%
        branches: 70,   // 从45%提升到70%
        statements: 75, // 从50%提升到75%

        perFile: false, // 不对单个文件强制要求
        autoUpdate: true, // 自动更新配置
      },
      */

      // 收集选项
      ignoreEmptyLines: true,

      // 水印（绿色=良好，黄色=警告）
      watermarks: {
        statements: [50, 85],
        functions: [50, 85],
        branches: [45, 80],
        lines: [50, 85],
      },
    },
  },

  // =============================================================================
  // 路径解析（与vite.config.ts保持一致）
  // =============================================================================
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
      '@/api': path.resolve(__dirname, './src/api'),
      '@/store': path.resolve(__dirname, './src/store'),
      '@/monitoring': path.resolve(__dirname, './src/monitoring'),
      // Mock @sentry/react for tests (optional dependency)
      '@sentry/react': path.resolve(__dirname, './src/mocks/sentry.ts'),
    },
  },
});
