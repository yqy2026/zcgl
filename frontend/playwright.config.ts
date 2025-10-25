/**
 * Playwright 端到端测试配置
 * 支持跨浏览器测试、并发执行、报告生成
 */

import { defineConfig, devices } from '@playwright/test';
import path from 'path';

// 测试配置
const config = defineConfig({
  // 测试目录
  testDir: './tests/e2e',

  // 并行执行配置
  fullyParallel: true,
  workers: process.env.CI ? 2 : 4,

  // 全局测试配置
  globalSetup: require.resolve('./tests/e2e/global-setup.ts'),
  globalTeardown: require.resolve('./tests/e2e/global-teardown.ts'),

  // 超时配置
  timeout: 60 * 1000, // 60秒
  expect: {
    timeout: 10 * 1000, // 10秒
  },

  // 重试配置
  retries: process.env.CI ? 2 : 0,

  // 报告配置
  reporter: [
    ['html', {
      outputFolder: './tests/e2e/reports/html',
      open: process.env.CI ? 'never' : 'on-failure'
    }],
    ['json', {
      outputFile: './tests/e2e/reports/test-results.json'
    }],
    ['junit', {
      outputFile: './tests/e2e/reports/junit.xml'
    }],
    process.env.CI ? ['github'] : ['list']
  ],

  // 输出目录
  outputDir: './tests/e2e/test-results',

  // 测试文件匹配模式
  testMatch: [
    '**/*.spec.ts',
    '**/*.e2e.ts',
    '**/*.test.ts'
  ],

  // 忽略模式
  testIgnore: [
    '**/node_modules/**',
    '**/dist/**',
    '**/.next/**',
    '**/coverage/**'
  ],

  // 测试环境
  use: {
    // 基础URL
    baseURL: process.env.BASE_URL || 'http://localhost:5173',

    // 操作配置
    actionTimeout: 15 * 1000,
    navigationTimeout: 30 * 1000,

    // 截图配置
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    trace: 'retain-on-failure',

    // 测试数据配置
    storageState: './tests/e2e/storage/admin-state.json',

    // 颜色主题偏好
    colorScheme: 'light',

    // 地区设置
    locale: 'zh-CN',
    timezoneId: 'Asia/Shanghai',

    // 用户代理
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Playwright',

    // 忽略HTTPS错误
    ignoreHTTPSErrors: !process.env.CI,
  },

  // 项目配置 - 多浏览器支持
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },

    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },

    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },

    // 移动端测试
    {
      name: 'Mobile Chrome',
      use: { ...devices['Pixel 5'] },
    },

    {
      name: 'Mobile Safari',
      use: { ...devices['iPhone 12'] },
    },

    // 平板测试
    {
      name: 'iPad',
      use: { ...devices['iPad Pro'] },
    },

    // 不同用户角色测试
    {
      name: 'admin-user',
      use: {
        storageState: './tests/e2e/storage/admin-state.json',
        ...devices['Desktop Chrome']
      },
      testMatch: '**/admin/**/*.spec.ts',
    },

    {
      name: 'asset-manager',
      use: {
        storageState: './tests/e2e/storage/asset-manager-state.json',
        ...devices['Desktop Chrome']
      },
      testMatch: '**/asset-manager/**/*.spec.ts',
    },

    {
      name: 'asset-viewer',
      use: {
        storageState: './tests/e2e/storage/asset-viewer-state.json',
        ...devices['Desktop Chrome']
      },
      testMatch: '**/asset-viewer/**/*.spec.ts',
    },

    // 性能测试
    {
      name: 'performance',
      use: {
        ...devices['Desktop Chrome'],
        launchOptions: {
          args: ['--disable-web-security', '--disable-features=IsolateOrigins,site-per-process']
        }
      },
      testMatch: '**/performance/**/*.spec.ts',
      retries: 0,
    },

    // 可访问性测试
    {
      name: 'accessibility',
      use: {
        ...devices['Desktop Chrome'],
        launchOptions: {
          args: ['--force-prefers-reduced-motion', '--high-contrast-mode']
        }
      },
      testMatch: '**/accessibility/**/*.spec.ts',
    }
  ],

  // 测试环境配置
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:5173',
    reuseExistingServer: !process.env.CI,
    timeout: 120 * 1000,
  },

  // 元数据配置
  metadata: {
    'Test Environment': process.env.NODE_ENV || 'test',
    'Base URL': process.env.BASE_URL || 'http://localhost:5173',
    'Browser': 'Playwright',
    'Test Suite': 'Asset Management E2E Tests'
  }
});

export default config;