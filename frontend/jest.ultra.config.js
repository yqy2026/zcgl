/**
 * UltraThink优化Jest配置
 * 确保前端测试覆盖率监控自动化和最佳实践
 */

module.exports = {
  // 基础配置
  testEnvironment: 'jsdom',
  setupFilesAfterEnv: ['<rootDir>/src/setupTests.ts'],

  // 测试文件匹配模式
  testMatch: [
    '<rootDir>/src/**/__tests__/**/*.{js,jsx,ts,tsx}',
    '<rootDir>/src/**/*.{test,spec}.{js,jsx,ts,tsx}',
    '<rootDir>/tests/**/*.{test,spec}.{js,jsx,ts,tsx}'
  ],

  // 忽略文件和目录
  testPathIgnorePatterns: [
    '<rootDir>/node_modules/',
    '<rootDir>/build/',
    '<rootDir>/dist/',
    '<rootDir>/coverage/',
    '<rootDir>/config/',
    '<rootDir>/public/',
    '<rootDir>/scripts/',
    '<rootDir>/.vscode/',
    '<rootDir>/.github/'
  ],

  // 模块路径映射 - 解决路径别名问题
  moduleNameMapping: {
    '^@/(.*)$': '<rootDir>/src/$1',
    '^@components/(.*)$': '<rootDir>/src/components/$1',
    '^@pages/(.*)$': '<rootDir>/src/pages/$1',
    '^@services/(.*)$': '<rootDir>/src/services/$1',
    '^@utils/(.*)$': '<rootDir>/src/utils/$1',
    '^@types/(.*)$': '<rootDir>/src/types/$1',
    '^@hooks/(.*)$': '<rootDir>/src/hooks/$1',
    '^@assets/(.*)$': '<rootDir>/src/assets/$1',
    '^@styles/(.*)$': '<rootDir>/src/styles/$1'
  },

  // 覆盖率配置
  collectCoverage: true,
  collectCoverageFrom: [
    'src/**/*.{js,jsx,ts,tsx}',
    '!src/**/*.d.ts',
    '!src/**/*.stories.{js,jsx,ts,tsx}',
    '!src/**/index.{js,jsx,ts,tsx}',
    '!src/**/*.mock.{js,jsx,ts,tsx}',
    '!src/**/*.test.{js,jsx,ts,tsx}',
    '!src/**/*.spec.{js,jsx,ts,tsx}',
    '!src/setupTests.ts',
    '!src/main.tsx',
    '!src/vite-env.d.ts'
  ],

  // 覆盖率报告格式
  coverageReporters: [
    'text',
    'text-summary',
    'html',
    'lcov',
    'json',
    'clover'
  ],

  // 覆盖率输出目录
  coverageDirectory: 'coverage',

  // 覆盖率阈值
  coverageThreshold: {
    global: {
      branches: 60,
      functions: 65,
      lines: 65,
      statements: 65
    },
    // 核心组件要求更高覆盖率
    './src/components/AssetForm/': {
      branches: 75,
      functions: 80,
      lines: 80,
      statements: 80
    },
    './src/components/AssetList/': {
      branches: 70,
      functions: 75,
      lines: 75,
      statements: 75
    },
    './src/services/': {
      branches: 70,
      functions: 75,
      lines: 75,
      statements: 75
    }
  },

  // 忽略覆盖率的文件
  coveragePathIgnorePatterns: [
    '/node_modules/',
    '/coverage/',
    '/dist/',
    '/build/',
    'src/types/',
    'src/utils/test-utils.tsx',
    'src/mocks/',
    'src/vite-env.d.ts'
  ],

  // 转换配置
  transform: {
    '^.+\\.(js|jsx|mjs|cjs|ts|tsx)$': [
      'babel-jest',
      {
        presets: [
          ['@babel/preset-env', { targets: { node: 'current' } }],
          ['@babel/preset-react', { runtime: 'automatic' }],
          '@babel/preset-typescript'
        ],
        plugins: [
          ['@babel/plugin-transform-runtime', { corejs: 3, version: '^7.23.0' }]
        ]
      }
    ],
    '^.+\\.(css|less|scss|sass)$': 'jest-css-modules-transform',
    '^.+\\.(jpg|jpeg|png|gif|webp|avif|svg)$': 'jest-transform-stub'
  },

  // 模块文件扩展名
  moduleFileExtensions: [
    'ts',
    'tsx',
    'js',
    'jsx',
    'json',
    'node'
  ],

  // 模块目录
  moduleDirectories: [
    'node_modules',
    'src'
  ],

  // 清除Mock
  clearMocks: true,
  restoreMocks: true,

  // 测试超时
  testTimeout: 10000,

  // 详细输出
  verbose: true,

  // 错误时停止
  bail: false,

  // 最大并发数
  maxConcurrency: 5,

  // 最大Worker数量
  maxWorkers: '50%',

  // 强制退出
  forceExit: false,

  // 监听模式忽略模式
  watchPathIgnorePatterns: [
    '<rootDir>/node_modules/',
    '<rootDir>/coverage/',
    '<rootDir>/dist/',
    '<rootDir>/build/'
  ],

  // 全局设置
  globals: {
    'ts-jest': {
      tsconfig: {
        jsx: 'react-jsx',
        esModuleInterop: true,
        allowSyntheticDefaultImports: true
      }
    }
  },

  // Mock配置
  moduleNameMapping: {
    '\\.(css|less|scss|sass)$': 'identity-obj-proxy',
    '\\.(jpg|jpeg|png|gif|webp|avif|svg)$': '<rootDir>/__mocks__/fileMock.js'
  },

  // 测试环境选项
  testEnvironmentOptions: {
    url: 'http://localhost:3000'
  },

  // 全局变量
  globals: {
    ...require('jest-environment-jsdom')
  },

  // 自定义 reporters
  reporters: [
    'default',
    [
      'jest-junit',
      {
        outputDirectory: 'coverage',
        outputName: 'junit.xml',
        classNameTemplate: '{classname}',
        titleTemplate: '{title}',
        ancestorSeparator: ' › ',
        usePathForSuiteName: true
      }
    ],
    [
      'jest-html-reporters',
      {
        publicPath: './coverage/html-report',
        filename: 'report.html',
        expand: true,
        hideIcon: false,
        pageTitle: '地产资产管理系统 - 前端测试报告',
        logoImgPath: undefined,
        inlineSource: false
      }
    ]
  ],

  // 项目配置
  projects: [
    {
      displayName: 'unit',
      testMatch: ['<rootDir>/src/**/*.{test,spec}.{js,jsx,ts,tsx}'],
      setupFilesAfterEnv: ['<rootDir>/src/setupTests.ts'],
      testEnvironment: 'jsdom'
    },
    {
      displayName: 'integration',
      testMatch: ['<rootDir>/tests/integration/**/*.{test,spec}.{js,jsx,ts,tsx}'],
      setupFilesAfterEnv: ['<rootDir>/src/setupTests.ts'],
      testEnvironment: 'jsdom'
    }
  ],

  // 快照配置
  snapshotSerializers: [],

  // 测试结果处理器
  reporters: [
    'default',
    ['jest-junit', { outputDirectory: 'coverage', outputName: 'junit.xml' }]
  ]
};