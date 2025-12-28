#!/usr/bin/env node

/**
 * 版本兼容性检查脚本
 * 检查依赖版本兼容性，浏览器支持，以及API兼容性
 */

const fs = require('fs')
const path = require('path')

// 最低支持的浏览器版本
const BROWSER_REQUIREMENTS = {
  chrome: '90',
  firefox: '88',
  safari: '14',
  edge: '90'
}

// 关键依赖的兼容性版本
const DEPENDENCY_COMPATIBILITY = {
  'react': { min: '18.0.0', max: '19.0.0' },
  'react-dom': { min: '18.0.0', max: '19.0.0' },
  'react-router-dom': { min: '6.8.0', max: '7.0.0' },
  'antd': { min: '5.0.0', max: '6.0.0' },
  'typescript': { min: '5.0.0', max: '6.0.0' }
}

function checkBrowserCompatibility() {
  console.log('🔍 检查浏览器兼容性...')

  const userAgent = process.env.BROWSER_USER_AGENT || navigator.userAgent
  let compatible = true
  let warnings = []

  if (userAgent.includes('Chrome/')) {
    const version = userAgent.match(/Chrome\/(\d+)/)?.[1]
    if (version && parseInt(version) < parseInt(BROWSER_REQUIREMENTS.chrome)) {
      compatible = false
      warnings.push(`Chrome版本过低。需要 >= ${BROWSER_REQUIREMENTS.chrome}，当前版本：${version}`)
    }
  }

  if (userAgent.includes('Firefox/')) {
    const version = userAgent.match(/Firefox\/(\d+)/)?.[1]
    if (version && parseInt(version) < parseInt(BROWSER_REQUIREMENTS.firefox)) {
      compatible = false
      warnings.push(`Firefox版本过低。需要 >= ${BROWSER_REQUIREMENTS.firefox}，当前版本：${version}`)
    }
  }

  if (warnings.length > 0) {
    console.warn('⚠️  浏览器兼容性警告:')
    warnings.forEach(warning => console.warn(`  - ${warning}`))
  }

  return { compatible, warnings }
}

function checkDependencyCompatibility() {
  console.log('📦 检查依赖版本兼容性...')

  try {
    const packageJsonPath = path.join(__dirname, '../package.json')
    const packageJson = JSON.parse(fs.readFileSync(packageJsonPath, 'utf8'))
    const dependencies = { ...packageJson.dependencies, ...packageJson.devDependencies }

    let compatible = true
    const issues = []

    Object.entries(DEPENDENCY_COMPATIBILITY).forEach(([dep, versionRange]) => {
      const currentVersion = dependencies[dep]

      if (!currentVersion) {
        issues.push(`缺少依赖: ${dep}`)
        compatible = false
        return
      }

      // 移除版本前缀并解析版本号
      const cleanVersion = currentVersion.replace(/^[\^~]/, '')
      const [major] = cleanVersion.split('.').map(Number)

      if (major) {
        const [minMajor] = versionRange.min.split('.').map(Number)
        const [maxMajor] = versionRange.max.split('.').map(Number)

        if (major < minMajor || major > maxMajor) {
          issues.push(`${dep}版本不兼容。推荐: ^${versionRange.min}，当前: ${currentVersion}`)
          compatible = false
        }
      }
    })

    if (issues.length > 0) {
      console.error('❌ 依赖版本兼容性问题:')
      issues.forEach(issue => console.error(`  - ${issue}`))
    } else {
      console.log('✅ 所有依赖版本兼容')
    }

    return { compatible, issues }
  } catch (error) {
    console.error('❌ 检查依赖兼容性失败:', error.message)
    return { compatible: false, issues: [error.message] }
  }
}

function checkAPICompatibility() {
  console.log('🌐 检查API兼容性...')

  const issues = []

  // 检查支持的API
  if (!window.fetch) {
    issues.push('Fetch API不支持')
  }

  if (!window.Promise) {
    issues.push('Promise不支持')
  }

  if (!window.URLSearchParams) {
    issues.push('URLSearchParams不支持')
  }

  if (!window.IntersectionObserver) {
    issues.push('IntersectionObserver不支持（影响懒加载）')
  }

  if (!window.ResizeObserver) {
    issues.push('ResizeObserver不支持（影响响应式组件）')
  }

  if (issues.length > 0) {
    console.warn('⚠️  API兼容性问题:')
    issues.forEach(issue => console.warn(`  - ${issue}`))
  } else {
    console.log('✅ 所有必需API都支持')
  }

  return issues
}

function generateCompatibilityReport() {
  console.log('📋 生成兼容性报告...')

  const browserCheck = checkBrowserCompatibility()
  const dependencyCheck = checkDependencyCompatibility()
  const apiCheck = checkAPICompatibility()

  const report = {
    timestamp: new Date().toISOString(),
    browser: browserCheck,
    dependencies: dependencyCheck,
    apis: apiCheck,
    overall: browserCheck.compatible && dependencyCheck.compatible && apiCheck.length === 0
  }

  try {
    const reportPath = path.join(__dirname, '../compatibility-report.json')
    fs.writeFileSync(reportPath, JSON.stringify(report, null, 2))
    console.log(`✅ 兼容性报告已生成: ${reportPath}`)
  } catch (error) {
    console.error('❌ 生成兼容性报告失败:', error.message)
  }

  return report
}

// 主执行逻辑
if (require.main === module) {
  console.log('🚀 开始版本兼容性检查...\n')

  const report = generateCompatibilityReport()

  console.log('\n📊 兼容性检查结果:')
  console.log(`浏览器兼容性: ${report.browser.compatible ? '✅ 通过' : '❌ 失败'}`)
  console.log(`依赖兼容性: ${report.dependencies.compatible ? '✅ 通过' : '❌ 失败'}`)
  console.log(`API兼容性: ${report.apis.length === 0 ? '✅ 通过' : '⚠️  有警告'}`)
  console.log(`总体评估: ${report.overall ? '✅ 兼容' : '❌ 不兼容'}`)

  if (!report.overall) {
    console.log('\n💡 建议:')
    console.log('1. 更新浏览器到最新版本')
    console.log('2. 运行 npm update 更新依赖')
    console.log('3. 检查并更新 package.json 中的依赖版本')
    console.log('4. 考虑添加 polyfill 支持旧版浏览器')
  }
}

module.exports = {
  checkBrowserCompatibility,
  checkDependencyCompatibility,
  checkAPICompatibility,
  generateCompatibilityReport
}