/**
 * ESLint自定义规则：检测API响应处理不规范问题
 *
 * 安装说明：
 * 1. 将此文件添加到项目根目录
 * 2. 在.eslintrc.js中添加：'extends': ['./.eslintrc.api-response.js']
 * 3. 运行ESLint检查：npm run lint -- --ext .ts,.tsx src/
 */

module.exports = {
  // 继承项目基础配置
  extends: ['./.eslintrc.js'],

  rules: {
    // 自定义规则将在下面定义

    // 现有规则强化
    'no-console': ['warn', { allow: ['warn', 'error'] }],
    '@typescript-eslint/no-explicit-any': 'warn',
    '@typescript-eslint/ban-ts-comment': 'warn',

    // 强制使用类型安全
    '@typescript-eslint/explicit-function-return-type': 'warn',
    '@typescript-eslint/no-unused-vars': 'error',

    // 强制错误处理
    '@typescript-eslint/prefer-nullish-coalescing': 'error',
    '@typescript-eslint/prefer-optional-chain': 'error'
  },

  // 自定义规则定义
  overrides: [
    {
      files: ['src/services/**/*.ts', 'src/api/**/*.ts'],
      rules: {
        // 检测直接访问response.data以外属性的情况
        'custom/no-direct-response-access': 'error',
        // 检测缺少统一错误处理的情况
        'custom/require-unified-error-handling': 'warn',
        // 检测重复的响应处理逻辑
        'custom/no-duplicate-response-handling': 'error'
      }
    }
  ]
};