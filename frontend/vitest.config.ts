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

const artifactsRoot = path.resolve(__dirname, '../test-results/frontend');
const reportsRoot = path.join(artifactsRoot, 'reports');
const coverageRoot = path.join(artifactsRoot, 'coverage');
const isStrictCoverage = process.env.VITEST_COVERAGE_STRICT === 'true';
const isCI = process.env.CI === 'true';

const coverageThresholds = isStrictCoverage
  ? {
      // 阶段2（严格）阈值：向 70% 目标对齐
      lines: 70,
      functions: 70,
      branches: 65,
      statements: 70,
      perFile: false,
    }
  : {
      // 阶段1（默认）阈值：从历史 50% 基线平滑上调
      lines: 55,
      functions: 55,
      branches: 50,
      statements: 55,
      perFile: false,
    };

const coverageWatermarks = isStrictCoverage
  ? {
      statements: [70, 85],
      functions: [70, 85],
      branches: [65, 80],
      lines: [70, 85],
    }
  : {
      statements: [55, 85],
      functions: [55, 85],
      branches: [50, 80],
      lines: [55, 85],
    };

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
    testTimeout: isCI ? 20000 : 10000,
    hookTimeout: isCI ? 20000 : 10000,
    teardownTimeout: isCI ? 20000 : 10000,

    // 并发和隔离
    isolate: true,
    pool: 'threads',
    singleThread: false,
    ...(isCI
      ? {
          // 覆盖率模式下系统页测试对CPU争用敏感，CI串行可显著降低超时抖动
          maxWorkers: 1,
          minWorkers: 1,
        }
      : {}),

    // 报告器
    reporters: ['verbose', 'json', 'html'],
    outputFile: {
      json: path.join(reportsRoot, 'vitest-results.json'),
      html: path.join(reportsRoot, 'vitest-report.html'),
    },

    // 监听模式
    watch: {
      ignore: ['**/node_modules/**', '**/dist/**', '**/coverage/**', '**/test-results/**'],
    },

    // =============================================================================
    // 覆盖率配置（分阶段目标）
    // =============================================================================
    coverage: {
      provider: 'v8',
      reportsDirectory: coverageRoot,

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
      // 阶段1质量门禁聚焦可稳定单测的核心逻辑层，UI层覆盖率单独跟踪
      include: [
        'src/api/**/*.{ts,tsx}',
        'src/services/**/*.{ts,tsx}',
        'src/store/**/*.{ts,tsx}',
        'src/utils/**/*.{ts,tsx}',
      ],

      // 覆盖率阈值（当前CI基线）
      thresholds: coverageThresholds,

      // 收集选项
      ignoreEmptyLines: true,

      // 水印（绿色=良好，黄色=警告）
      watermarks: coverageWatermarks,
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
