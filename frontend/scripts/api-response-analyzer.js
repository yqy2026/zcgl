#!/usr/bin/env node

/**
 * API响应处理质量分析工具
 *
 * 使用方法：
 * node scripts/api-response-analyzer.js [options]
 *
 * 选项：
 * --path <path>     指定扫描路径 (默认: src/)
 * --output <file>   输出报告文件 (默认: api-response-analysis.json)
 * --fix             自动修复简单问题
 * --verbose         详细输出
 */

const fs = require('fs');
const path = require('path');

class ApiResponseAnalyzer {
  constructor(options = {}) {
    this.options = {
      path: options.path || 'src/',
      outputFile: options.output || 'api-response-analysis.json',
      fix: options.fix || false,
      verbose: options.verbose || false,
      ...options
    };

    this.issues = [];
    this.stats = {
      files: 0,
      apiCalls: 0,
      issues: 0,
      fixed: 0
    };
  }

  /**
   * 执行分析
   */
  async analyze() {
    console.log('🔍 开始分析API响应处理质量...');

    // 扫描文件
    const files = this.scanFiles(this.options.path);
    console.log(`📁 找到 ${files.length} 个文件`);

    // 分析每个文件
    for (const file of files) {
      await this.analyzeFile(file);
    }

    // 生成报告
    const report = this.generateReport();

    // 保存报告
    this.saveReport(report);

    // 输出摘要
    this.printSummary(report);

    return report;
  }

  /**
   * 扫描TypeScript/JavaScript文件
   */
  scanFiles(dir) {
    const files = [];

    if (!fs.existsSync(dir)) {
      console.error(`❌ 目录不存在: ${dir}`);
      return files;
    }

    const scan = (currentDir) => {
      const items = fs.readdirSync(currentDir);

      for (const item of items) {
        const fullPath = path.join(currentDir, item);
        const stat = fs.statSync(fullPath);

        if (stat.isDirectory() && !item.startsWith('.') && item !== 'node_modules') {
          scan(fullPath);
        } else if (stat.isFile() && /\.(ts|tsx|js|jsx)$/.test(item)) {
          files.push(fullPath);
        }
      }
    };

    scan(dir);
    return files;
  }

  /**
   * 分析单个文件
   */
  async analyzeFile(filePath) {
    try {
      const content = fs.readFileSync(filePath, 'utf8');
      const lines = content.split('\n');

      this.stats.files++;

      // 分析API调用
      this.analyzeApiCalls(filePath, content, lines);

      // 分析响应处理
      this.analyzeResponseHandling(filePath, content, lines);

      // 分析错误处理
      this.analyzeErrorHandling(filePath, content, lines);

      // 如果启用了修复，尝试修复简单问题
      if (this.options.fix) {
        await this.fixSimpleIssues(filePath, content, lines);
      }

    } catch (error) {
      console.error(`❌ 分析文件失败: ${filePath}`, error.message);
    }
  }

  /**
   * 分析API调用
   */
  analyzeApiCalls(filePath, content, lines) {
    // 匹配API调用模式
    const apiCallPatterns = [
      /\.(get|post|put|delete|patch)\s*\(/g,
      /axios\.(get|post|put|delete|patch)\s*\(/g,
      /apiClient\.(get|post|put|delete|patch)\s*\(/g,
      /fetch\s*\(/g
    ];

    apiCallPatterns.forEach(pattern => {
      let match;
      while ((match = pattern.exec(content)) !== null) {
        this.stats.apiCalls++;

        const lineIndex = content.substring(0, match.index).split('\n').length - 1;
        const line = lines[lineIndex];

        // 检查是否有正确的响应处理
        this.checkResponseHandling(filePath, lineIndex, line, match[0]);
      }
    });
  }

  /**
   * 分析响应处理
   */
  analyzeResponseHandling(filePath, content, lines) {
    // 检查直接的response属性访问
    const directAccessPattern = /response\.(?!data)[a-zA-Z_][a-zA-Z0-9_]*/g;
    let match;

    while ((match = directAccessPattern.exec(content)) !== null) {
      const property = match[0].replace('response.', '');

      // 允许的属性（排除data）
      const allowedProperties = ['status', 'headers', 'config', 'request'];
      if (!allowedProperties.includes(property)) {
        const lineIndex = content.substring(0, match.index).split('\n').length - 1;

        this.addIssue({
          type: 'direct_response_access',
          severity: 'error',
          file: filePath,
          line: lineIndex + 1,
          column: match.index - content.lastIndexOf('\n', match.index) - 1,
          message: `直接访问response.${property}，应该使用response.data或统一响应处理工具`,
          suggestion: '使用ResponseExtractor.smartExtract()或response.data'
        });
      }
    }

    // 检查重复的响应处理逻辑
    this.checkDuplicateResponseHandling(filePath, content, lines);
  }

  /**
   * 分析错误处理
   */
  analyzeErrorHandling(filePath, content, lines) {
    // 检查try-catch块
    const tryCatchPattern = /try\s*{[\s\S]*?catch\s*\([^)]*\)\s*{/g;
    let match;

    while ((match = tryCatchPattern.exec(content)) !== null) {
      const blockContent = match[0];
      const lineIndex = content.substring(0, match.index).split('\n').length - 1;

      // 检查是否只是简单console.error
      if (blockContent.includes('console.error') && !blockContent.includes('throw')) {
        this.addIssue({
          type: 'insufficient_error_handling',
          severity: 'warning',
          file: filePath,
          line: lineIndex + 1,
          message: '错误处理不充分，只是记录错误但没有重新抛出',
          suggestion: '应该重新抛出错误或进行适当的错误处理'
        });
      }
    }
  }

  /**
   * 检查响应处理
   */
  checkResponseHandling(filePath, lineIndex, line, apiCall) {
    // 查找后续的响应处理代码
    const nextLines = [];
    for (let i = lineIndex + 1; i < Math.min(lineIndex + 10, line.length); i++) {
      nextLines.push(line[i]);
    }

    const followingCode = nextLines.join('\n');

    // 检查是否有统一的响应处理
    const hasUnifiedHandling =
      followingCode.includes('ResponseExtractor') ||
      followingCode.includes('smartExtract') ||
      followingCode.includes('.extractData');

    if (!hasUnifiedHandling) {
      this.addIssue({
        type: 'missing_unified_handling',
        severity: 'warning',
        file: filePath,
        line: lineIndex + 1,
        message: `API调用${apiCall}缺少统一的响应处理`,
        suggestion: '使用ResponseExtractor.smartExtract()进行统一处理'
      });
    }
  }

  /**
   * 检查重复的响应处理
   */
  checkDuplicateResponseHandling(filePath, content, lines) {
    // 查找相似的响应处理模式
    const responsePatterns = [
      /if\s*\(\s*response\.data\s*\)\s*{[\s\S]*?}/g,
      /if\s*\(\s*response\.data.*success\s*\)\s*{[\s\S]*?}/g,
      /return\s+response\.data/g
    ];

    const patterns = [];

    responsePatterns.forEach(pattern => {
      let match;
      while ((match = pattern.exec(content)) !== null) {
        patterns.push({
          pattern: match[0],
          index: match.index,
          line: content.substring(0, match.index).split('\n').length
        });
      }
    });

    // 检查重复的模式
    for (let i = 0; i < patterns.length; i++) {
      for (let j = i + 1; j < patterns.length; j++) {
        if (this.arePatternsSimilar(patterns[i].pattern, patterns[j].pattern)) {
          this.addIssue({
            type: 'duplicate_response_handling',
            severity: 'warning',
            file: filePath,
            line: patterns[j].line,
            message: '发现重复的响应处理逻辑',
            suggestion: '提取公共函数或使用统一的响应处理工具'
          });
        }
      }
    }
  }

  /**
   * 判断两个模式是否相似
   */
  arePatternsSimilar(pattern1, pattern2) {
    // 简单的相似性检查（可以根据需要优化）
    const normalized1 = pattern1.replace(/\s+/g, ' ').trim();
    const normalized2 = pattern2.replace(/\s+/g, ' ').trim();

    return normalized1 === normalized2 ||
           Math.abs(normalized1.length - normalized2.length) < 10;
  }

  /**
   * 修复简单问题
   */
  async fixSimpleIssues(filePath, content, lines) {
    let modifiedContent = content;
    let hasChanges = false;

    // 修复简单的直接response访问问题
    modifiedContent = modifiedContent.replace(
      /response\.user/g,
      'response.data.user'
    );
    modifiedContent = modifiedContent.replace(
      /response\.tokens/g,
      'response.data.tokens'
    );
    modifiedContent = modifiedContent.replace(
      /response\.message/g,
      'response.data.message'
    );

    if (modifiedContent !== content) {
      hasChanges = true;
      fs.writeFileSync(filePath, modifiedContent);
      this.stats.fixed++;

      if (this.options.verbose) {
        console.log(`🔧 修复文件: ${filePath}`);
      }
    }

    return hasChanges;
  }

  /**
   * 添加问题
   */
  addIssue(issue) {
    this.issues.push(issue);
    this.stats.issues++;
  }

  /**
   * 生成报告
   */
  generateReport() {
    const report = {
      timestamp: new Date().toISOString(),
      summary: {
        ...this.stats,
        issueRate: this.stats.files > 0 ? (this.stats.issues / this.stats.files * 100).toFixed(2) : 0
      },
      issues: {
        byType: this.groupIssuesByType(),
        bySeverity: this.groupIssuesBySeverity(),
        byFile: this.groupIssuesByFile()
      },
      recommendations: this.generateRecommendations(),
      details: this.issues
    };

    return report;
  }

  /**
   * 按类型分组问题
   */
  groupIssuesByType() {
    const grouped = {};

    this.issues.forEach(issue => {
      if (!grouped[issue.type]) {
        grouped[issue.type] = 0;
      }
      grouped[issue.type]++;
    });

    return grouped;
  }

  /**
   * 按严重程度分组问题
   */
  groupIssuesBySeverity() {
    const grouped = { error: 0, warning: 0, info: 0 };

    this.issues.forEach(issue => {
      grouped[issue.severity] = (grouped[issue.severity] || 0) + 1;
    });

    return grouped;
  }

  /**
   * 按文件分组问题
   */
  groupIssuesByFile() {
    const grouped = {};

    this.issues.forEach(issue => {
      const relativePath = path.relative(process.cwd(), issue.file);
      if (!grouped[relativePath]) {
        grouped[relativePath] = [];
      }
      grouped[relativePath].push(issue);
    });

    return grouped;
  }

  /**
   * 生成建议
   */
  generateRecommendations() {
    const recommendations = [];

    if (this.stats.issues > 0) {
      recommendations.push('🔧 使用统一的API响应处理工具（ResponseExtractor）');
      recommendations.push('📚 遵循API响应处理编码规范');
    }

    const issuesByType = this.groupIssuesByType();

    if (issuesByType.direct_response_access) {
      recommendations.push('⚠️ 避免直接访问response对象属性，使用response.data');
    }

    if (issuesByType.missing_unified_handling) {
      recommendations.push('📦 为所有API调用添加统一响应处理');
    }

    if (issuesByType.duplicate_response_handling) {
      recommendations.push('🔄 提取重复的响应处理逻辑为公共函数');
    }

    if (issuesByType.insufficient_error_handling) {
      recommendations.push('🛡️ 完善错误处理机制，确保错误被正确传播');
    }

    return recommendations;
  }

  /**
   * 保存报告
   */
  saveReport(report) {
    try {
      fs.writeFileSync(this.options.outputFile, JSON.stringify(report, null, 2));
      console.log(`📄 报告已保存到: ${this.options.outputFile}`);
    } catch (error) {
      console.error('❌ 保存报告失败:', error.message);
    }
  }

  /**
   * 打印摘要
   */
  printSummary(report) {
    console.log('\n📊 分析摘要:');
    console.log(`   📁 扫描文件: ${report.summary.files}`);
    console.log(`   🌐 API调用: ${report.summary.apiCalls}`);
    console.log(`   ⚠️  发现问题: ${report.summary.issues}`);

    if (this.options.fix) {
      console.log(`   🔧 已修复: ${report.summary.fixed}`);
    }

    if (report.summary.issues > 0) {
      console.log(`   📈 问题率: ${report.summary.issueRate}%`);

      console.log('\n📋 问题分布:');
      Object.entries(report.issues.bySeverity).forEach(([severity, count]) => {
        console.log(`   ${severity === 'error' ? '🔴' : severity === 'warning' ? '🟡' : '🔵'} ${severity}: ${count}`);
      });

      console.log('\n💡 建议:');
      report.recommendations.forEach(rec => {
        console.log(`   ${rec}`);
      });
    } else {
      console.log('✅ 未发现问题，代码质量良好！');
    }
  }
}

// 命令行接口
if (require.main === module) {
  const args = process.argv.slice(2);
  const options = {};

  for (let i = 0; i < args.length; i++) {
    switch (args[i]) {
      case '--path':
        options.path = args[++i];
        break;
      case '--output':
        options.output = args[++i];
        break;
      case '--fix':
        options.fix = true;
        break;
      case '--verbose':
        options.verbose = true;
        break;
      case '--help':
        console.log(`
API响应处理质量分析工具

使用方法:
  node scripts/api-response-analyzer.js [选项]

选项:
  --path <path>     指定扫描路径 (默认: src/)
  --output <file>   输出报告文件 (默认: api-response-analysis.json)
  --fix             自动修复简单问题
  --verbose         详细输出
  --help            显示此帮助信息

示例:
  node scripts/api-response-analyzer.js --path src/services --fix
  node scripts/api-response-analyzer.js --output report.json --verbose
        `);
        process.exit(0);
    }
  }

  const analyzer = new ApiResponseAnalyzer(options);
  analyzer.analyze().catch(console.error);
}

module.exports = ApiResponseAnalyzer;