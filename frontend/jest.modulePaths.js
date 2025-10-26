const { pathsToModuleNameMapper } = require('ts-jest')
const { compilerOptions } = require('./tsconfig.json')

module.exports = pathsToModuleNameMapper(compilerOptions.paths, {
  prefix: '<rootDir>/',
})