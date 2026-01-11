module.exports = {
  root: true,
  env: { browser: true, es2020: true, node: true },
  extends: [
    'eslint:recommended',
    'plugin:@typescript-eslint/recommended',
    'plugin:react-hooks/recommended',
    'plugin:jsx-a11y/recommended',
    'plugin:react/recommended',
  ],
  ignorePatterns: ['dist', '.eslintrc.js', 'node_modules', 'coverage', 'build'],
  parser: '@typescript-eslint/parser',
  parserOptions: {
    ecmaVersion: 2020,
    sourceType: 'module',
    ecmaFeatures: {
      jsx: true,
    },
    project: ['./tsconfig.eslint.json'],
    tsconfigRootDir: __dirname,
  },
  plugins: ['@typescript-eslint', 'react-hooks', 'jsx-a11y'],
  settings: {
    react: {
      version: 'detect',
    },
  },
  rules: {
    '@typescript-eslint/no-unused-vars': ['error', { argsIgnorePattern: '^_', varsIgnorePattern: '^_' }],
    '@typescript-eslint/no-explicit-any': 'off', // 允许 any 类型用于测试和复杂转换
    '@typescript-eslint/ban-ts-comment': ['warn', { 'ts-ignore': true }],
    '@typescript-eslint/explicit-module-boundary-types': 'off', // 关闭严格边界类型要求
    '@typescript-eslint/consistent-type-definitions': ['error', 'interface'],
    '@typescript-eslint/strict-boolean-expressions': 'warn',
    '@typescript-eslint/no-unsafe-assignment': 'warn', // 降级为警告
    '@typescript-eslint/no-unsafe-member-access': 'warn',
    '@typescript-eslint/no-unsafe-call': 'warn',
    '@typescript-eslint/no-unsafe-return': 'warn',
    'react-hooks/rules-of-hooks': 'error',
    'react-hooks/exhaustive-deps': 'warn',
    'no-console': 'warn',
    'prefer-const': 'error',
    // UI Design Audit - Accessibility rules (warn mode to avoid breaking builds)
    'jsx-a11y/anchor-is-valid': 'warn',
    'jsx-a11y/click-events-have-key-events': 'warn',
    'jsx-a11y/no-static-element-interactions': 'warn',
    'jsx-a11y/no-autofocus': 'warn',
    'jsx-a11y/label-has-associated-control': 'warn',
    // React best practices for UI consistency
    'react/jsx-props-no-spreading': 'off', // Allow spreading for flexibility
    'react/prop-types': 'off', // Using TypeScript
    'react/react-in-jsx-scope': 'off', // React 17+ doesn't need it
  },
  overrides: [
    {
      // 测试文件的特殊规则
      files: ['**/__tests__/**/*', '**/*.test.ts', '**/*.test.tsx', 'src/test/**/*', 'src/test-utils.*', 'src/vitest-setup.*'],
      env: { jest: true },
      parserOptions: {
        // Disable project for test files since they're excluded from tsconfig.json
        project: null,
      },
      rules: {
        '@typescript-eslint/no-explicit-any': 'off', // 测试中允许 any
        '@typescript-eslint/no-unsafe-assignment': 'off',
        // Disable type-aware rules for test files (no project config)
        '@typescript-eslint/strict-boolean-expressions': 'off',
        '@typescript-eslint/no-unsafe-member-access': 'off',
        '@typescript-eslint/no-unsafe-call': 'off',
        '@typescript-eslint/no-unsafe-return': 'off',
        // Allow unused vars with underscore prefix in tests
        '@typescript-eslint/no-unused-vars': ['warn', { argsIgnorePattern: '^_', varsIgnorePattern: '^_', ignoreRestSiblings: true }],
        'no-unused-vars': 'off', // Use TypeScript version instead
      },
    },
  ],
}
