import fs from 'fs'
import path from 'path'

export interface TestResult {
  testName: string
  status: 'passed' | 'failed' | 'skipped'
  duration: number
  error?: string
  coverage?: {
    lines: number
    functions: number
    branches: number
    statements: number
  }
}

export interface TestSuite {
  suiteName: string
  results: TestResult[]
  totalTests: number
  passedTests: number
  failedTests: number
  skippedTests: number
  totalDuration: number
}

export class TestReporter {
  private suites: TestSuite[] = []
  private startTime: number = Date.now()

  addSuite(suite: TestSuite): void {
    this.suites.push(suite)
  }

  generateReport(): string {
    const endTime = Date.now()
    const totalDuration = endTime - this.startTime

    const totalTests = this.suites.reduce((sum, suite) => sum + suite.totalTests, 0)
    const totalPassed = this.suites.reduce((sum, suite) => sum + suite.passedTests, 0)
    const totalFailed = this.suites.reduce((sum, suite) => sum + suite.failedTests, 0)
    const totalSkipped = this.suites.reduce((sum, suite) => sum + suite.skippedTests, 0)

    let report = `
# 测试报告

## 总览
- 总测试数: ${totalTests}
- 通过: ${totalPassed}
- 失败: ${totalFailed}
- 跳过: ${totalSkipped}
- 总耗时: ${totalDuration}ms
- 成功率: ${((totalPassed / totalTests) * 100).toFixed(2)}%

## 测试套件详情

`

    this.suites.forEach(suite => {
      report += `
### ${suite.suiteName}
- 测试数: ${suite.totalTests}
- 通过: ${suite.passedTests}
- 失败: ${suite.failedTests}
- 跳过: ${suite.skippedTests}
- 耗时: ${suite.totalDuration}ms

`

      if (suite.results.some(r => r.status === 'failed')) {
        report += '#### 失败的测试:\n'
        suite.results
          .filter(r => r.status === 'failed')
          .forEach(result => {
            report += `- ${result.testName}: ${result.error}\n`
          })
        report += '\n'
      }
    })

    return report
  }

  saveReport(outputPath: string): void {
    const report = this.generateReport()
    const dir = path.dirname(outputPath)
    
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true })
    }
    
    fs.writeFileSync(outputPath, report, 'utf8')
  }

  generateJUnitXML(): string {
    const totalTests = this.suites.reduce((sum, suite) => sum + suite.totalTests, 0)
    const totalFailed = this.suites.reduce((sum, suite) => sum + suite.failedTests, 0)
    const totalDuration = this.suites.reduce((sum, suite) => sum + suite.totalDuration, 0)

    let xml = `<?xml version="1.0" encoding="UTF-8"?>
<testsuites tests="${totalTests}" failures="${totalFailed}" time="${totalDuration / 1000}">
`

    this.suites.forEach(suite => {
      xml += `  <testsuite name="${suite.suiteName}" tests="${suite.totalTests}" failures="${suite.failedTests}" time="${suite.totalDuration / 1000}">
`

      suite.results.forEach(result => {
        xml += `    <testcase name="${result.testName}" time="${result.duration / 1000}"`
        
        if (result.status === 'failed') {
          xml += `>
      <failure message="${result.error || 'Test failed'}">${result.error || 'Test failed'}</failure>
    </testcase>
`
        } else if (result.status === 'skipped') {
          xml += `>
      <skipped/>
    </testcase>
`
        } else {
          xml += '/>\n'
        }
      })

      xml += '  </testsuite>\n'
    })

    xml += '</testsuites>\n'
    return xml
  }

  saveJUnitReport(outputPath: string): void {
    const xml = this.generateJUnitXML()
    const dir = path.dirname(outputPath)
    
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true })
    }
    
    fs.writeFileSync(outputPath, xml, 'utf8')
  }
}

// Helper function to create test reporter instance
export const createTestReporter = (): TestReporter => {
  return new TestReporter()
}

// Helper function to measure test performance
export const measureTestPerformance = async (
  testFn: () => Promise<void> | void,
  testName: string
): Promise<TestResult> => {
  const startTime = Date.now()
  let status: 'passed' | 'failed' | 'skipped' = 'passed'
  let error: string | undefined

  try {
    await testFn()
  } catch (err) {
    status = 'failed'
    error = err instanceof Error ? err.message : String(err)
  }

  const endTime = Date.now()
  const duration = endTime - startTime

  return {
    testName,
    status,
    duration,
    error,
  }
}

// Helper function to generate coverage report
export const generateCoverageReport = (coverageData: any): string => {
  if (!coverageData) {
    return '覆盖率数据不可用'
  }

  let report = '# 代码覆盖率报告\n\n'

  Object.keys(coverageData).forEach(filePath => {
    const fileData = coverageData[filePath]
    const fileName = path.basename(filePath)
    
    const lineCoverage = (fileData.l?.covered || 0) / (fileData.l?.total || 1) * 100
    const functionCoverage = (fileData.f?.covered || 0) / (fileData.f?.total || 1) * 100
    const branchCoverage = (fileData.b?.covered || 0) / (fileData.b?.total || 1) * 100
    const statementCoverage = (fileData.s?.covered || 0) / (fileData.s?.total || 1) * 100

    report += `## ${fileName}\n`
    report += `- 行覆盖率: ${lineCoverage.toFixed(2)}%\n`
    report += `- 函数覆盖率: ${functionCoverage.toFixed(2)}%\n`
    report += `- 分支覆盖率: ${branchCoverage.toFixed(2)}%\n`
    report += `- 语句覆盖率: ${statementCoverage.toFixed(2)}%\n\n`
  })

  return report
}