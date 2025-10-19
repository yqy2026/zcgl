module.exports = {
  // Test environment
  testEnvironment: 'jsdom',

  // Setup files
  setupFilesAfterEnv: ['<rootDir>/src/__tests__/setup.ts'],

  // Module name mapping for path aliases
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/src/$1',
    '^@/__tests__/(.*)$': '<rootDir>/src/__tests__/$1',
  },

  // File extensions to consider
  moduleFileExtensions: ['ts', 'tsx', 'js', 'jsx', 'json'],

  // Transform files
  transform: {
    '^.+\\.(ts|tsx)$': 'ts-jest',
    '^.+\\.(js|jsx)$': 'babel-jest',
  },

  // Files to ignore during transformation
  transformIgnorePatterns: [
    'node_modules/(?!(antd|@ant-design|rc-.+|@babel/runtime)/)',
  ],

  // Test file patterns
  testMatch: [
    '<rootDir>/src/**/__tests__/**/*.(ts|tsx|js|jsx)',
    '<rootDir>/src/**/*.(test|spec).(ts|tsx|js|jsx)',
  ],

  // Files to ignore
  testPathIgnorePatterns: [
    '<rootDir>/node_modules/',
    '<rootDir>/build/',
    '<rootDir>/dist/',
  ],

  // Coverage configuration
  collectCoverageFrom: [
    'src/**/*.{ts,tsx}',
    '!src/**/*.d.ts',
    '!src/index.tsx',
    '!src/reportWebVitals.ts',
    '!src/**/__tests__/**',
    '!src/**/*.test.{ts,tsx}',
    '!src/**/*.spec.{ts,tsx}',
    '!src/**/*.stories.{ts,tsx}',
  ],

  coverageReporters: ['text', 'lcov', 'html', 'json-summary'],

  coverageDirectory: '<rootDir>/coverage',

  coverageThreshold: {
    global: {
      branches: 80,
      functions: 80,
      lines: 80,
      statements: 80,
    },
  },

  // Module directories
  moduleDirectories: ['node_modules', '<rootDir>/src'],

  // Handle static assets
  moduleNameMapper: {
    '\\.(css|less|scss|sass)$': 'identity-obj-proxy',
    '\\.(jpg|jpeg|png|gif|eot|otf|webp|svg|ttf|woff|woff2|mp4|webm|wav|mp3|m4a|aac|oga)$':
      '<rootDir>/src/__tests__/__mocks__/fileMock.js',
  },

  // Global setup
  globals: {
    'ts-jest': {
      tsconfig: {
        jsx: 'react-jsx',
      },
    },
  },

  // Test timeout
  testTimeout: 10000,

  // Verbose output
  verbose: true,

  // Clear mocks between tests
  clearMocks: true,

  // Restore mocks after each test
  restoreMocks: true,

  // Error handling
  errorOnDeprecated: true,

  // Test suites configuration
  projects: [
    {
      displayName: 'unit',
      testMatch: [
        '<rootDir>/src/**/__tests__/**/*.test.(ts|tsx)',
        '<rootDir>/src/**/?(*.)(test).(ts|tsx)',
      ],
      testPathIgnorePatterns: [
        '<rootDir>/src/__tests__/integration/',
        '<rootDir>/src/__tests__/e2e/',
        '<rootDir>/src/__tests__/performance/',
      ],
    },
    {
      displayName: 'integration',
      testMatch: ['<rootDir>/src/__tests__/integration/**/*.test.(ts|tsx)'],
    },
    {
      displayName: 'e2e',
      testMatch: ['<rootDir>/src/__tests__/e2e/**/*.test.(ts|tsx)'],
      testTimeout: 30000,
    },
    {
      displayName: 'performance',
      testMatch: ['<rootDir>/src/__tests__/performance/**/*.test.(ts|tsx)'],
      testTimeout: 15000,
    },
  ],

  // Watch mode configuration
  watchPlugins: [
    'jest-watch-typeahead/filename',
    'jest-watch-typeahead/testname',
  ],

  // Snapshot serializers
  snapshotSerializers: ['@emotion/jest/serializer'],

  // Custom matchers
  setupFilesAfterEnv: [
    '<rootDir>/src/__tests__/setup.ts',
    '@testing-library/jest-dom',
  ],
}