/**
 * API路径测试工具
 * 验证API路径的正确性，防止配置错误和回归问题
 */

/* eslint-disable no-console */

import {
  AUTH_API,
  PDF_API,
  SYSTEM_API,
  ASSET_API,
  STATISTICS_API,
  TEST_COVERAGE_API,
  MONITORING_API,
  ERROR_REPORTING_API
} from '../constants/api'

// API路径测试结果接口
export interface ApiPathTestResult {
  name: string
  path: string
  status: 'pass' | 'fail' | 'skip'
  expectedPattern?: RegExp
  actualValue?: string
  error?: string
}

// API路径测试套件
export class ApiPathTester {
  private results: ApiPathTestResult[] = []

  /**
   * 测试API路径是否符合预期模式
   */
  private testPath(name: string, path: string, expectedPattern: RegExp): boolean {
    const result = expectedPattern.test(path)
    this.results.push({
      name,
      path,
      status: result ? 'pass' : 'fail',
      expectedPattern,
      actualValue: path,
      error: result ? undefined : `Path "${path}" does not match expected pattern`
    })
    return result
  }

  /**
   * 测试所有认证相关API路径
   */
  testAuthPaths(): void {
    console.log('🔐 Testing Authentication API paths...')

    // 登录路径应该以 /api/auth 开头
    this.testPath('LOGIN', AUTH_API.LOGIN, /^\/api\/auth\/login$/)
    this.testPath('LOGOUT', AUTH_API.LOGOUT, /^\/api\/auth\/logout$/)
    this.testPath('USERS', AUTH_API.USERS, /^\/api\/auth\/users$/)
    this.testPath('PROFILE', AUTH_API.PROFILE, /^\/api\/auth\/profile$/)
  }

  /**
   * 测试PDF相关API路径
   */
  testPdfPaths(): void {
    console.log('📄 Testing PDF API paths...')

    // PDF路径应该以 /api/v1/pdf-import 开头
    this.testPath('PDF_INFO', PDF_API.INFO, /^\/api\/v1\/pdf-import\/info$/)
    this.testPath('PDF_SESSIONS', PDF_API.SESSIONS, /^\/api\/v1\/pdf-import\/sessions$/)
    this.testPath('PDF_UPLOAD', PDF_API.UPLOAD, /^\/api\/v1\/pdf-import\/upload$/)
  }

  /**
   * 测试系统管理API路径
   */
  testSystemPaths(): void {
    console.log('⚙️ Testing System API paths...')

    // 系统API应该以 /api/system 开头或使用legacy路径
    this.testPath('SYSTEM_USERS', SYSTEM_API.USERS, /^\/api\/auth\/users$/)
    this.testPath('SYSTEM_HEALTH', SYSTEM_API.HEALTH, /^\/api\/system\/health$/)
    this.testPath('SYSTEM_SETTINGS', SYSTEM_API.SETTINGS, /^\/api\/system\/settings$/)
  }

  /**
   * 测试资产管理API路径
   */
  testAssetPaths(): void {
    console.log('🏢 Testing Asset API paths...')

    // 资产API可能使用相对路径
    this.testPath('ASSET_LIST', ASSET_API.LIST, /^\/assets$/)
    this.testPath('ASSET_CREATE', ASSET_API.CREATE, /^\/assets$/)
  }

  /**
   * 测试统计API路径
   */
  testStatisticsPaths(): void {
    console.log('📊 Testing Statistics API paths...')

    this.testPath('STATS_OVERVIEW', STATISTICS_API.OVERVIEW, /^\/statistics\/overview$/)
  }

  /**
   * 测试测试覆盖率API路径
   */
  testTestCoveragePaths(): void {
    console.log('🧪 Testing Test Coverage API paths...')

    this.testPath('COVERAGE_REPORT', TEST_COVERAGE_API.REPORT, /^\/api\/v1\/test-coverage\/report$/)
    this.testPath('COVERAGE_TREND', TEST_COVERAGE_API.TREND(7), /^\/api\/v1\/test-coverage\/trend\?days=7$/)
  }

  /**
   * 测试监控API路径
   */
  testMonitoringPaths(): void {
    console.log('📈 Testing Monitoring API paths...')

    this.testPath('MONITORING_PERFORMANCE', MONITORING_API.ROUTE_PERFORMANCE, /^\/api\/v1\/monitoring\/route-performance$/)
    this.testPath('MONITORING_HEALTH', MONITORING_API.SYSTEM_HEALTH, /^\/api\/v1\/monitoring\/health$/)
  }

  /**
   * 测试错误报告API路径
   */
  testErrorReportingPaths(): void {
    console.log('🚨 Testing Error Reporting API paths...')

    this.testPath('ERROR_REPORT', ERROR_REPORTING_API.REPORT, /^\/api\/v1\/errors\/report$/)
  }

  /**
   * 运行所有测试
   */
  runAllTests(): ApiPathTestResult[] {
    console.log('🧪 Starting API Path Tests...\n')

    this.results = [] // 重置结果

    this.testAuthPaths()
    this.testPdfPaths()
    this.testSystemPaths()
    this.testAssetPaths()
    this.testStatisticsPaths()
    this.testTestCoveragePaths()
    this.testMonitoringPaths()
    this.testErrorReportingPaths()

    return this.results
  }

  /**
   * 生成测试报告
   */
  generateReport(): { passed: number; failed: number; total: number; results: ApiPathTestResult[] } {
    const passed = this.results.filter(r => r.status === 'pass').length
    const failed = this.results.filter(r => r.status === 'fail').length
    const total = this.results.length

    return {
      passed,
      failed,
      total,
      results: this.results
    }
  }

  /**
   * 打印测试结果
   */
  printResults(): void {
    const report = this.generateReport()

    console.log('\n📋 API Path Test Results:')
    console.log(`✅ Passed: ${report.passed}`)
    console.log(`❌ Failed: ${report.failed}`)
    console.log(`📊 Total: ${report.total}`)
    console.log(`🎯 Success Rate: ${((report.passed / report.total) * 100).toFixed(1)}%`)

    if (report.failed > 0) {
      console.log('\n❌ Failed Tests:')
      report.results
        .filter(r => r.status === 'fail')
        .forEach(test => {
          console.log(`  - ${test.name}: ${test.error}`)
          console.log(`    Expected: ${test.expectedPattern?.source}`)
          console.log(`    Actual: ${test.actualValue}`)
        })
    }

    console.log('\n' + '='.repeat(50))
  }

  /**
   * 检查是否存在常见的API路径问题
   */
  checkCommonIssues(): string[] {
    const issues: string[] = []

    // 检查是否有重复的/api/前缀
    const duplicateApiPaths = this.results.filter(r =>
      r.actualValue && r.actualValue.includes('/api/api/')
    )

    if (duplicateApiPaths.length > 0) {
      issues.push(`Found ${duplicateApiPaths.length} paths with duplicate /api/ prefix`)
    }

    // 检查是否有HTTP/HTTPS硬编码
    const hardcodedProtocols = this.results.filter(r =>
      r.actualValue && (r.actualValue.includes('http://') || r.actualValue.includes('https://'))
    )

    if (hardcodedProtocols.length > 0) {
      issues.push(`Found ${hardcodedProtocols.length} paths with hardcoded protocols`)
    }

    // 检查是否有尾部斜杠不一致
    const trailingSlashIssues = this.results.filter(r =>
      r.actualValue && (r.actualValue.endsWith('/') || !r.actualValue.startsWith('/'))
    )

    if (trailingSlashIssues.length > 0) {
      issues.push(`Found ${trailingSlashIssues.length} paths with formatting inconsistencies`)
    }

    return issues
  }
}

// 便捷的测试函数
export const runApiPathTests = (): { passed: number; failed: number; total: number; success: boolean } => {
  console.log('🚀 Running API Path Integrity Tests...\n')

  const tester = new ApiPathTester()
  tester.runAllTests()
  tester.printResults()

  const report = tester.generateReport()
  const issues = tester.checkCommonIssues()

  if (issues.length > 0) {
    console.log('\n⚠️ Common Issues Found:')
    issues.forEach(issue => console.log(`  - ${issue}`))
  }

  return {
    passed: report.passed,
    failed: report.failed,
    total: report.total,
    success: report.failed === 0 && issues.length === 0
  }
}

// 开发环境自动运行测试
if (process.env.NODE_ENV === 'development') {
  // 延迟执行，确保其他代码加载完成
  setTimeout(() => {
    try {
      runApiPathTests()
    } catch (error) {
      console.error('❌ API Path Tests failed:', error)
    }
  }, 1000)
}

export default ApiPathTester
