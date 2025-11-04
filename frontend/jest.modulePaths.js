const { pathsToModuleNameMapper } = require('ts-jest')

// 手动定义路径映射，避免JSON注释问题
const paths = {
  "@/*": ["src/*"],
  "@/components/*": ["src/components/*"],
  "@/pages/*": ["src/pages/*"],
  "@/services/*": ["src/services/*"],
  "@/types/*": ["src/types/*"],
  "@/utils/*": ["src/utils/*"],
  "@/hooks/*": ["src/hooks/*"],
  "@/store/*": ["src/store/*"],
  "@/constants/*": ["src/constants/*"]
}

module.exports = pathsToModuleNameMapper(paths, {
  prefix: '<rootDir>/',
})