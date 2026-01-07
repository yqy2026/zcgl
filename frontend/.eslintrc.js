module.exports = {
  root: true,
  env: { browser: true, es2020: true, node: true },
  extends: [
    'eslint:recommended',
    'plugin:@typescript-eslint/recommended',
    'plugin:react/recommended',
    'plugin:react-hooks/recommended',
    'plugin:prettier/recommended', // Must be last to override other configs
  ],
  ignorePatterns: [
    'dist',
    '.eslintrc.js',
    'node_modules',
    'coverage',
    'build',
    '*.config.js',
    '*.config.ts',
    'vite.config.ts',
  ],
  parser: '@typescript-eslint/parser',
  parserOptions: {
    ecmaVersion: 2020,
    sourceType: 'module',
    ecmaFeatures: {
      jsx: true,
    },
    tsconfigRootDir: __dirname,
  },
  plugins: ['@typescript-eslint', 'react-hooks', 'react', 'prettier'],
  settings: {
    react: {
      version: 'detect',
    },
  },
  rules: {
    // Prettier integration
    'prettier/prettier': 'error',

    // TypeScript strict rules
    '@typescript-eslint/no-unused-vars': [
      'error',
      { argsIgnorePattern: '^_', varsIgnorePattern: '^_' },
    ],
    '@typescript-eslint/no-explicit-any': 'error',
    '@typescript-eslint/ban-ts-comment': ['error', { 'ts-ignore': true }],
    '@typescript-eslint/explicit-module-boundary-types': 'off',
    '@typescript-eslint/consistent-type-definitions': ['error', 'interface'],

    // React rules
    'react/react-in-jsx-scope': 'off', // React 17+ doesn't need import
    'react/prop-types': 'off', // Using TypeScript for props validation
    'react-hooks/rules-of-hooks': 'error',
    'react-hooks/exhaustive-deps': 'warn',

    // General code quality
    'no-console': ['warn', { allow: ['warn', 'error'] }],
    'prefer-const': 'error',
    'no-var': 'error',
    curly: ['error', 'all'],
  },
  overrides: [
    {
      // Non-test source files - enable strict type checking
      files: ['src/**/*.ts', 'src/**/*.tsx'],
      excludedFiles: [
        '**/__tests__/**',
        '**/*.test.ts',
        '**/*.test.tsx',
        'src/test/**/*',
        'src/test-utils.*',
        'src/vitest-setup.*',
        'src/test-response-extraction.ts',
      ],
      extends: ['plugin:@typescript-eslint/recommended-type-checked'],
      parserOptions: {
        project: ['./tsconfig.eslint.json'],
        tsconfigRootDir: __dirname,
      },
      rules: {
        '@typescript-eslint/strict-boolean-expressions': 'warn',
        '@typescript-eslint/no-unsafe-assignment': 'warn',
        '@typescript-eslint/no-unsafe-member-access': 'warn',
        '@typescript-eslint/no-unsafe-call': 'warn',
        '@typescript-eslint/no-unsafe-return': 'warn',
        '@typescript-eslint/no-floating-promises': 'warn',
        '@typescript-eslint/no-misused-promises': 'warn',
      },
    },
    {
      // Test files special rules - no type checking
      files: [
        '**/__tests__/**/*',
        '**/*.test.ts',
        '**/*.test.tsx',
        'src/test/**/*',
        'src/test-utils.*',
        'src/vitest-setup.*',
        'src/test-response-extraction.ts',
      ],
      env: { jest: true },
      parserOptions: {
        project: null,
      },
      rules: {
        '@typescript-eslint/no-explicit-any': 'off',
        '@typescript-eslint/strict-boolean-expressions': 'off',
        '@typescript-eslint/no-unused-vars': [
          'warn',
          {
            argsIgnorePattern: '^_',
            varsIgnorePattern: '^_',
            ignoreRestSiblings: true,
          },
        ],
        'no-unused-vars': 'off',
      },
    },
  ],
};
