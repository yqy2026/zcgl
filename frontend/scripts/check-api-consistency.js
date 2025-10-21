#!/usr/bin/env node

/**
 * 前端API一致性检查工具
 *
 * 用于检查前端API调用的一致性和最佳实践
 */

const fs = require('fs');
const path = require('path');

class APIConsistencyChecker {
  constructor() {
    this.issues = [];
    this.apiCalls = new Map();
  }

  /**
   * 运行所有检查
   */
  runChecks() {
    console.log('🔍 开始前端API一致性检查...');

    // 扫描服务文件
    this.scanServiceFiles();

    // 检查响应处理一致性
    this.checkResponseHandling();

    // 检查错误处理一致性
    this.checkErrorHandling();

    // 检查类型安全
    this.checkTypeSafety();

    // 检查API调用模式
    this.checkAPICallPatterns();

    console.log(`\n📊 检查完成，发现 ${this.issues.length} 个问题`);
    return this.issues;
  }

  /**
   * 扫描服务文件中的API调用
   */
  scanServiceFiles() {
    const servicesDir = path.join(process.cwd(), 'src/services');

    if (!fs.existsSync(servicesDir)) {
      console.warn('⚠️  services目录不存在');
      return;
    }

    const files = fs.readdirSync(servicesDir).filter(f => f.endsWith('.ts'));

    files.forEach(file => {
      const filePath = path.join(servicesDir, file);
      const content = fs.readFileSync(filePath, 'utf-8');

      this.parseAPICalls(content, filePath);
    });

    console.log(`✓ 扫描了 ${files.length} 个服务文件，发现 ${this.apiCalls.size} 个API调用`);
  }

  /**
   * 解析API调用
   */
  parseAPICalls(content, filePath) {
    // 匹配 apiClient.xxx('/path', ...) 模式
    const apiCallRegex = /apiClient\.(get|post|put|delete|patch)\s*\(\s*['"`]([^'"`]+)['"`]/g;

    let match;
    while ((match = apiCallRegex.exec(content)) !== null) {
      const method = match[1].toUpperCase();
      const path = match[2];
      const lineNumber = content.substring(0, match.index).split('\n').length;

      const key = `${method}:${path}`;
      this.apiCalls.set(key, {
        method,
        path,
        file: filePath,
        lineNumber
      });
    }

    // 检查返回值处理模式
    const returnRegex = /return\s+(?:response\.data\s*\|\|\s*)?response/g;
    let returnMatch;
    while ((returnMatch = returnRegex.exec(content)) !== null) {
      const lineNumber = content.substring(0, returnMatch.index).split('\n').length;

      // 检查是否使用了兼容性代码
      if (returnMatch[0].includes('|| response')) {
        this.issues.push({
          type: 'response_handling',
          severity: 'warning',
          message: '发现兼容性代码，建议统一使用 response.data',
          file: filePath,
          lineNumber
        });
      }
    }
  }

  /**
   * 检查响应处理一致性
   */
  checkResponseHandling() {
    console.log('\n🔍 检查响应处理一致性...');

    let inconsistentResponses = 0;

    this.apiCalls.forEach((call, key) => {
      try {
        const content = fs.readFileSync(call.file, 'utf-8');
        const lines = content.split('\n');

        // 查找API调用附近的代码
        const startLine = Math.max(0, call.lineNumber - 3);
        const endLine = Math.min(lines.length, call.lineNumber + 3);
        const context = lines.slice(startLine, endLine).join('\n');

        // 检查是否有统一的响应处理
        if (context.includes('response.data || response')) {
          inconsistentResponses++;
        }
      } catch (error) {
        console.warn(`无法检查文件 ${call.file}: ${error.message}`);
      }
    });

    console.log(`  ⚠️  响应处理不一致: ${inconsistentResponses}`);
  }

  /**
   * 检查错误处理一致性
   */
  checkErrorHandling() {
    console.log('\n🔍 检查错误处理一致性...');

    const servicesDir = path.join(process.cwd(), 'src/services');
    const files = fs.readdirSync(servicesDir).filter(f => f.endsWith('.ts'));

    files.forEach(file => {
      const filePath = path.join(servicesDir, file);
      const content = fs.readFileSync(filePath, 'utf-8');

      // 检查是否有try-catch块
      const hasTryCatch = /try\s*\{/.test(content);
      const hasErrorHandling = /catch\s*\([^)]+)\s*\{/.test(content);

      if (hasTryCatch && !hasErrorHandling) {
        this.issues.push({
          type: 'error_handling',
          severity: 'warning',
          message: '发现try块但没有相应的错误处理',
          file: filePath
        });
      }

      // 检查是否正确处理HTTP错误
      const apiClientCalls = content.match(/apiClient\.\w+\([^)]+\)/g) || [];
      apiClientCalls.forEach(call => {
        // 检查API调用是否有错误处理
        const lines = content.split('\n');
        const callIndex = content.indexOf(call);
        const callLine = content.substring(0, callIndex).split('\n').length;

        // 查找附近的await和错误处理
        const nearbyLines = lines.slice(Math.max(0, callLine - 5), callLine + 5);
        const nearbyCode = nearbyLines.join('\n');

        if (nearbyCode.includes('await') && !nearbyCode.includes('try') && !nearbyCode.includes('.catch')) {
          this.issues.push({
            type: 'error_handling',
            severity: 'warning',
            message: '异步API调用缺少错误处理',
            file: filePath,
            lineNumber: callLine
          });
        }
      });
    });

    console.log(`  ⚠️  错误处理问题: ${this.issues.filter(i => i.type === 'error_handling').length}`);
  }

  /**
   * 检查类型安全
   */
  checkTypeSafety() {
    console.log('\n🔍 检查类型安全...');

    const servicesDir = path.join(process.cwd(), 'src/services');
    const files = fs.readdirSync(servicesDir).filter(f => f.endsWith('.ts'));

    files.forEach(file => {
      const filePath = path.join(servicesDir, file);
      const content = fs.readFileSync(filePath, 'utf-8');

      // 检查any类型的使用
      const anyTypeMatches = content.match(/:\s*any/g) || [];
      anyTypeMatches.forEach((match, index) => {
        const lineNumber = content.substring(0, content.indexOf(match, index)).split('\n').length;
        this.issues.push({
          type: 'type_safety',
          severity: 'info',
          message: '使用了any类型，建议使用具体类型',
          file: filePath,
          lineNumber
        });
      });

      // 检查是否有类型断言
      const typeAssertions = content.match(/as\s+[A-Za-z][A-Za-z0-9_<>]+/g) || [];
      typeAssertions.forEach(assertion => {
        if (assertion.includes('unknown')) {
          const lineNumber = content.substring(0, content.indexOf(assertion)).split('\n').length;
          this.issues.push({
            type: 'type_safety',
            severity: 'warning',
            message: '使用了类型断言，可能导致运行时错误',
            file: filePath,
            lineNumber
          });
        }
      });
    });

    console.log(`  ℹ️  类型安全问题: ${this.issues.filter(i => i.type === 'type_safety').length}`);
  }

  /**
   * 检查API调用模式
   */
  checkAPICallPatterns() {
    console.log('\n🔍 检查API调用模式...');

    const commonIssues = [];

    this.apiCalls.forEach((call, key) => {
      // 检查路径是否以/开头
      if (!call.path.startsWith('/')) {
        commonIssues.push({
          type: 'path_format',
          severity: 'warning',
          message: `API路径应该以/开头: ${call.path}`,
          file: call.file,
          lineNumber: call.lineNumber
        });
      }

      // 检查是否有硬编码的API路径
      if (call.path.includes('/') && !call.path.includes(':')) {
        // 这是一个完整路径，建议使用常量
        if (call.path.split('/').length > 2) {
          commonIssues.push({
            type: 'hardcoded_path',
            severity: 'info',
            message: `建议使用常量定义API路径: ${call.path}`,
            file: call.file,
            lineNumber: call.lineNumber
          });
        }
      }
    });

    this.issues.push(...commonIssues);
    console.log(`  ⚠️  API调用模式问题: ${commonIssues.length}`);
  }

  /**
   * 打印检查结果摘要
   */
  printSummary() {
    if (!this.issues.length) {
      console.log('\n✅ 所有前端API一致性检查通过！');
      return;
    }

    console.log('\n📋 问题摘要:');

    // 按类型分组
    const grouped = {};
    this.issues.forEach(issue => {
      if (!grouped[issue.type]) {
        grouped[issue.type] = [];
      }
      grouped[issue.type].push(issue);
    });

    Object.entries(grouped).forEach(([type, issues]) => {
      const severityCount = issues.reduce((acc, issue) => {
        acc[issue.severity] = (acc[issue.severity] || 0) + 1;
        return acc;
      }, {});

      console.log(`  ${this.getTypeIcon(type)} ${type}:`);
      Object.entries(severityCount).forEach(([severity, count]) => {
        console.log(`    ${this.getSeverityIcon(severity)} ${severity}: ${count}`);
      });
    });

    // 显示关键问题
    const criticalIssues = this.issues.filter(i => i.severity === 'critical');
    const warningIssues = this.issues.filter(i => i.severity === 'warning');

    if (criticalIssues.length > 0) {
      console.log('\n🚨 关键问题:');
      criticalIssues.slice(0, 5).forEach(issue => {
        console.log(`  - ${issue.message} (${path.basename(issue.file)})`);
      });
    }

    if (warningIssues.length > 0 && criticalIssues.length === 0) {
      console.log('\n⚠️  主要警告:');
      warningIssues.slice(0, 3).forEach(issue => {
        console.log(`  - ${issue.message} (${path.basename(issue.file)})`);
      });
    }
  }

  getTypeIcon(type) {
    const icons = {
      'response_handling': '🔄',
      'error_handling': '⚠️',
      'type_safety': '🛡️',
      'path_format': '📍',
      'hardcoded_path': '🔗'
    };
    return icons[type] || '📋';
  }

  getSeverityIcon(severity) {
    const icons = {
      'critical': '🚨',
      'warning': '⚠️',
      'info': 'ℹ️'
    };
    return icons[severity] || '•';
  }

  /**
   * 保存报告到文件
   */
  saveReport(outputFile) {
    const report = {
      timestamp: new Date().toISOString(),
      totalIssues: this.issues.length,
      issues: this.issues,
      summary: {
        byType: {},
        bySeverity: {}
      }
    };

    // 统计摘要
    this.issues.forEach(issue => {
      report.summary.byType[issue.type] = (report.summary.byType[issue.type] || 0) + 1;
      report.summary.bySeverity[issue.severity] = (report.summary.bySeverity[issue.severity] || 0) + 1;
    });

    fs.writeFileSync(outputFile, JSON.stringify(report, null, 2));
    console.log(`\n📄 详细报告已保存到: ${outputFile}`);
  }
}

// 主函数
function main() {
  const checker = new APIConsistencyChecker();
  const issues = checker.runChecks();

  checker.printSummary();
  checker.saveReport('frontend-api-consistency-report.json');

  // 如果有严重问题，返回非零退出码
  const criticalIssues = issues.filter(i => i.severity === 'critical');
  if (criticalIssues.length > 0) {
    process.exit(1);
  } else {
    process.exit(0);
  }
}

// 如果直接运行此脚本
if (require.main === module) {
  main();
}

module.exports = APIConsistencyChecker;