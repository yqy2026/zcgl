/**
 * Playwright 端到端测试配置
 * 统一前端 E2E 测试入口（tests/e2e）
 */

import path from 'path';
import { defineConfig, devices, type PlaywrightTestConfig, type Project } from '@playwright/test';

const artifactsRoot = path.resolve(__dirname, '../test-results/frontend/playwright');
const reportRoot = path.join(artifactsRoot, 'reports');
const outputRoot = path.join(artifactsRoot, 'output');

const readNodeEnv = (name: string): string | undefined => {
  const rawValue = process.env[name];
  return typeof rawValue === 'string' && rawValue !== '' ? rawValue : undefined;
};

const readBooleanEnv = (name: string, fallbackValue: boolean): boolean => {
  const rawValue = readNodeEnv(name)?.toLowerCase();
  if (rawValue === '1' || rawValue === 'true' || rawValue === 'yes') {
    return true;
  }
  if (rawValue === '0' || rawValue === 'false' || rawValue === 'no') {
    return false;
  }
  return fallbackValue;
};

const isCI = readNodeEnv('CI') != null;
const baseUrl = readNodeEnv('BASE_URL') ?? 'http://127.0.0.1:5173';
const testEnvironment = readNodeEnv('NODE_ENV') ?? 'test';
const enableFullMatrix = readBooleanEnv('E2E_FULL_MATRIX', isCI);
const resolvedWorkers = (() => {
  const rawWorkers = readNodeEnv('E2E_WORKERS');
  if (rawWorkers == null || rawWorkers === '') {
    return 1;
  }

  const parsedWorkers = Number.parseInt(rawWorkers, 10);
  if (Number.isInteger(parsedWorkers) && parsedWorkers > 0) {
    return parsedWorkers;
  }

  return 1;
})();

const baseProjects: Project[] = [
  {
    name: 'chromium',
    use: {
      ...devices['Desktop Chrome'],
      storageState: './tests/e2e/storage/admin-state.json',
    },
  },
];

const roleProjects: Project[] = [
  {
    name: 'admin-user',
    use: {
      ...devices['Desktop Chrome'],
      storageState: './tests/e2e/storage/admin-state.json',
    },
    testMatch: '**/admin/**/*.spec.ts',
  },
  {
    name: 'asset-manager',
    use: {
      ...devices['Desktop Chrome'],
      storageState: './tests/e2e/storage/asset-manager-state.json',
    },
    testMatch: '**/asset-manager/**/*.spec.ts',
  },
  {
    name: 'asset-viewer',
    use: {
      ...devices['Desktop Chrome'],
      storageState: './tests/e2e/storage/asset-viewer-state.json',
    },
    testMatch: '**/asset-viewer/**/*.spec.ts',
  },
];

const matrixProjects: Project[] = enableFullMatrix
  ? [
      {
        name: 'firefox',
        use: { ...devices['Desktop Firefox'] },
      },
      {
        name: 'webkit',
        use: { ...devices['Desktop Safari'] },
      },
      {
        name: 'mobile-chrome',
        use: { ...devices['Pixel 5'] },
        testMatch: '**/mobile/**/*.spec.ts',
      },
    ]
  : [];

const projects: Project[] = [...baseProjects, ...roleProjects, ...matrixProjects];

const config: PlaywrightTestConfig = defineConfig({
  testDir: './tests/e2e',
  testMatch: ['**/*.spec.ts', '**/*.e2e.ts'],
  testIgnore: ['**/node_modules/**', '**/dist/**', '**/coverage/**'],

  fullyParallel: false,
  workers: resolvedWorkers,
  forbidOnly: isCI,
  retries: isCI ? 2 : 0,

  timeout: 60 * 1000,
  expect: {
    timeout: 10 * 1000,
  },

  globalSetup: require.resolve('./tests/e2e/global-setup.ts'),
  globalTeardown: require.resolve('./tests/e2e/global-teardown.ts'),

  reporter: [
    [
      'html',
      {
        outputFolder: path.join(reportRoot, 'html'),
        open: isCI ? 'never' : 'on-failure',
      },
    ],
    [
      'json',
      {
        outputFile: path.join(reportRoot, 'test-results.json'),
      },
    ],
    [
      'junit',
      {
        outputFile: path.join(reportRoot, 'junit.xml'),
      },
    ],
    isCI ? ['github'] : ['list'],
  ],

  outputDir: outputRoot,

  use: {
    baseURL: baseUrl,
    actionTimeout: 15 * 1000,
    navigationTimeout: 30 * 1000,
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    trace: 'retain-on-failure',
    storageState: './tests/e2e/storage/admin-state.json',
    locale: 'zh-CN',
    timezoneId: 'Asia/Shanghai',
    ignoreHTTPSErrors: !isCI,
  },

  projects,

  webServer: {
    command: 'pnpm dev --host 127.0.0.1 --port 5173',
    url: 'http://127.0.0.1:5173',
    reuseExistingServer: !isCI,
    timeout: 180 * 1000,
  },

  metadata: {
    'Test Environment': testEnvironment,
    'Base URL': baseUrl,
    Browser: 'Playwright',
    'Test Suite': 'Land Property Asset Management E2E Tests',
  },
});

export default config;
