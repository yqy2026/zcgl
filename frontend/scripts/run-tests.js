#!/usr/bin/env node

const { spawn } = require('child_process')
const path = require('path')
const fs = require('fs')

// Test configuration
const TEST_TYPES = {
  unit: {
    name: '单元测试',
    command: 'npm run test:unit',
    timeout: 60000,
  },
  integration: {
    name: '集成测试',
    command: 'npm run test:integration',
    timeout: 120000,
  },
  e2e: {
    name: '端到端测试',
    command: 'npm run test:e2e',
    timeout: 300000,
  },
  performance: {
    name: '性能测试',
    command: 'npm run test:performance',
    timeout: 180000,
  },
}

// Colors for console output
const colors = {
  reset: '\x1b[0m',
  bright: '\x1b[1m',
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  magenta: '\x1b[35m',
  cyan: '\x1b[36m',
}

function colorize(text, color) {
  return `${colors[color]}${text}${colors.reset}`
}

function log(message, color = 'reset') {
  console.log(colorize(message, color))
}

function logSection(title) {
  console.log('\n' + '='.repeat(60))
  log(title, 'bright')
  console.log('='.repeat(60))
}

function logSubSection(title) {
  console.log('\n' + '-'.repeat(40))
  log(title, 'cyan')
  console.log('-'.repeat(40))
}

async function runCommand(command, options = {}) {
  return new Promise((resolve, reject) => {
    const [cmd, ...args] = command.split(' ')
    const child = spawn(cmd, args, {
      stdio: 'pipe',
      shell: true,
      ...options,
    })

    let stdout = ''
    let stderr = ''

    child.stdout.on('data', (data) => {
      stdout += data.toString()
      if (options.verbose) {
        process.stdout.write(data)
      }
    })

    child.stderr.on('data', (data) => {
      stderr += data.toString()
      if (options.verbose) {
        process.stderr.write(data)
      }
    })

    child.on('close', (code) => {
      if (code === 0) {
        resolve({ stdout, stderr, code })
      } else {
        reject({ stdout, stderr, code })
      }
    })

    // Handle timeout
    if (options.timeout) {
      setTimeout(() => {
        child.kill('SIGTERM')
        reject(new Error(`Command timed out after ${options.timeout}ms`))
      }, options.timeout)
    }
  })
}

async function runTestSuite(testType, options = {}) {
  const config = TEST_TYPES[testType]
  if (!config) {
    throw new Error(`Unknown test type: ${testType}`)
  }

  logSubSection(`运行 ${config.name}`)
  
  const startTime = Date.now()
  
  try {
    const result = await runCommand(config.command, {
      timeout: config.timeout,
      verbose: options.verbose,
    })
    
    const duration = Date.now() - startTime
    log(`✅ ${config.name} 通过 (${duration}ms)`, 'green')
    
    return {
      type: testType,
      name: config.name,
      success: true,
      duration,
      output: result.stdout,
    }
  } catch (error) {
    const duration = Date.now() - startTime
    log(`❌ ${config.name} 失败 (${duration}ms)`, 'red')
    
    if (options.verbose && error.stdout) {
      console.log('\n输出:')
      console.log(error.stdout)
    }
    
    if (error.stderr) {
      console.log('\n错误:')
      console.log(colorize(error.stderr, 'red'))
    }
    
    return {
      type: testType,
      name: config.name,
      success: false,
      duration,
      error: error.message || error.stderr || '未知错误',
      output: error.stdout,
    }
  }
}

async function generateReport(results) {
  const totalTests = results.length
  const passedTests = results.filter(r => r.success).length
  const failedTests = totalTests - passedTests
  const totalDuration = results.reduce((sum, r) => sum + r.duration, 0)

  logSection('测试报告')
  
  log(`总测试套件: ${totalTests}`, 'bright')
  log(`通过: ${passedTests}`, 'green')
  log(`失败: ${failedTests}`, failedTests > 0 ? 'red' : 'green')
  log(`总耗时: ${totalDuration}ms`, 'blue')
  log(`成功率: ${((passedTests / totalTests) * 100).toFixed(2)}%`, 'bright')

  console.log('\n详细结果:')
  results.forEach(result => {
    const status = result.success ? '✅' : '❌'
    const color = result.success ? 'green' : 'red'
    log(`${status} ${result.name} (${result.duration}ms)`, color)
    
    if (!result.success && result.error) {
      log(`   错误: ${result.error}`, 'red')
    }
  })

  // Generate JSON report
  const reportPath = path.join(__dirname, '../test-results.json')
  const report = {
    timestamp: new Date().toISOString(),
    summary: {
      total: totalTests,
      passed: passedTests,
      failed: failedTests,
      duration: totalDuration,
      successRate: (passedTests / totalTests) * 100,
    },
    results,
  }

  fs.writeFileSync(reportPath, JSON.stringify(report, null, 2))
  log(`\n📊 详细报告已保存到: ${reportPath}`, 'blue')

  return report
}

async function checkPrerequisites() {
  logSection('检查前置条件')
  
  // Check if package.json exists
  const packageJsonPath = path.join(__dirname, '../package.json')
  if (!fs.existsSync(packageJsonPath)) {
    throw new Error('package.json 不存在')
  }
  log('✅ package.json 存在', 'green')

  // Check if node_modules exists
  const nodeModulesPath = path.join(__dirname, '../node_modules')
  if (!fs.existsSync(nodeModulesPath)) {
    log('⚠️  node_modules 不存在，正在安装依赖...', 'yellow')
    await runCommand('npm install', { verbose: true })
    log('✅ 依赖安装完成', 'green')
  } else {
    log('✅ node_modules 存在', 'green')
  }

  // Check if Jest is available
  try {
    await runCommand('npx jest --version')
    log('✅ Jest 可用', 'green')
  } catch (error) {
    throw new Error('Jest 不可用，请检查安装')
  }
}

async function main() {
  const args = process.argv.slice(2)
  const options = {
    verbose: args.includes('--verbose') || args.includes('-v'),
    coverage: args.includes('--coverage') || args.includes('-c'),
    watch: args.includes('--watch') || args.includes('-w'),
    type: args.find(arg => Object.keys(TEST_TYPES).includes(arg)),
  }

  try {
    logSection('🧪 资产管理系统测试套件')
    
    // Check prerequisites
    await checkPrerequisites()

    // Determine which tests to run
    let testTypes = []
    if (options.type) {
      testTypes = [options.type]
    } else if (args.includes('--all')) {
      testTypes = Object.keys(TEST_TYPES)
    } else {
      // Default: run unit and integration tests
      testTypes = ['unit', 'integration']
    }

    log(`\n将运行以下测试类型: ${testTypes.join(', ')}`, 'blue')

    // Run tests
    const results = []
    for (const testType of testTypes) {
      const result = await runTestSuite(testType, options)
      results.push(result)
    }

    // Generate report
    const report = await generateReport(results)

    // Run coverage if requested
    if (options.coverage) {
      logSubSection('生成覆盖率报告')
      try {
        await runCommand('npm run test:coverage', { verbose: options.verbose })
        log('✅ 覆盖率报告生成完成', 'green')
      } catch (error) {
        log('❌ 覆盖率报告生成失败', 'red')
      }
    }

    // Exit with appropriate code
    const hasFailures = results.some(r => !r.success)
    if (hasFailures) {
      log('\n❌ 部分测试失败', 'red')
      process.exit(1)
    } else {
      log('\n✅ 所有测试通过', 'green')
      process.exit(0)
    }

  } catch (error) {
    log(`\n💥 测试运行失败: ${error.message}`, 'red')
    process.exit(1)
  }
}

// Handle CLI usage
if (require.main === module) {
  main().catch(error => {
    console.error(colorize(`Fatal error: ${error.message}`, 'red'))
    process.exit(1)
  })
}

module.exports = {
  runTestSuite,
  generateReport,
  checkPrerequisites,
}