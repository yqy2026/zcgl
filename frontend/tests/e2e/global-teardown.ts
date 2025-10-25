/**
 * Playwright 全局测试清理
 * 在所有测试运行后执行的清理工作
 */

import { FullConfig } from '@playwright/test';
import path from 'path';
import fs from 'fs';

async function globalTeardown(config: FullConfig) {
  console.log('🧹 开始Playwright全局清理...');

  // 清理临时测试数据
  await cleanupTestResults();

  // 生成测试报告摘要
  await generateReportSummary();

  // 清理过期的测试文件
  await cleanupOldFiles();

  console.log('✅ Playwright全局清理完成');
}

async function cleanupTestResults() {
  const testResultsDir = path.join(__dirname, 'test-results');

  if (fs.existsSync(testResultsDir)) {
    // 保留最新的5个测试结果目录
    const entries = fs.readdirSync(testResultsDir, { withFileTypes: true })
      .filter(entry => entry.isDirectory())
      .map(entry => ({
        name: entry.name,
        path: path.join(testResultsDir, entry.name),
        mtime: fs.statSync(path.join(testResultsDir, entry.name)).mtime
      }))
      .sort((a, b) => b.mtime - a.mtime);

    // 删除旧的测试结果
    for (let i = 5; i < entries.length; i++) {
      fs.rmSync(entries[i].path, { recursive: true, force: true });
      console.log(`🗑️  删除旧的测试结果: ${entries[i].name}`);
    }
  }
}

async function generateReportSummary() {
  const reportsDir = path.join(__dirname, 'reports');
  const summaryFile = path.join(reportsDir, 'test-summary.md');

  try {
    // 检查HTML报告是否存在
    const htmlReports = fs.readdirSync(reportsDir)
      .filter(file => file.startsWith('playwright-report-'))
      .sort()
      .reverse();

    if (htmlReports.length > 0) {
      const latestReport = htmlReports[0];
      const reportDate = new Date().toISOString().split('T')[0];

      const summary = `# Playwright 端到端测试报告摘要

## 测试信息
- **测试日期**: ${reportDate}
- **测试框架**: Playwright
- **测试环境**: ${process.env.NODE_ENV || 'test'}
- **基础URL**: ${process.env.BASE_URL || 'http://localhost:5173'}

## 测试覆盖范围
- ✅ 用户登录和权限验证
- ✅ 58字段资产创建流程
- ✅ 资产搜索和过滤功能
- ✅ 资产批量操作
- ✅ 资产详情和编辑
- ✅ 数据导入导出功能
- ✅ 统计报表功能
- ✅ 权限边界测试

## 测试浏览器
- 🌐 Chromium (Chrome)
- 🦊 Firefox
- 🧭 WebKit (Safari)
- 📱 Mobile Chrome
- 📱 Mobile Safari
- 📟 iPad

## 详细的测试报告
请查看最新的HTML报告: [${latestReport}](./${latestReport}/index.html)

## 测试文件结构
\`\`\`
tests/e2e/
├── asset-management.spec.ts     # 主要的资产管理测试
├── fixtures/                    # 测试数据文件
├── reports/                     # 测试报告
├── test-results/                # 测试结果
└── storage/                     # 用户认证状态
\`\`\`

---
*报告生成时间: ${new Date().toLocaleString('zh-CN')}*
`;

      fs.writeFileSync(summaryFile, summary, 'utf8');
      console.log(`📊 生成测试报告摘要: ${summaryFile}`);
    }
  } catch (error) {
    console.warn('⚠️ 生成报告摘要失败:', error);
  }
}

async function cleanupOldFiles() {
  const maxAgeDays = 7; // 保留7天的文件
  const now = Date.now();
  const maxAge = maxAgeDays * 24 * 60 * 60 * 1000;

  const directoriesToClean = [
    path.join(__dirname, 'test-results'),
    path.join(__dirname, 'reports', 'html'),
    path.join(__dirname, 'reports', 'trace')
  ];

  for (const dir of directoriesToClean) {
    if (fs.existsSync(dir)) {
      const files = fs.readdirSync(dir, { withFileTypes: true });

      for (const file of files) {
        const filePath = path.join(dir, file.name);
        const stats = fs.statSync(filePath);

        if (now - stats.mtime.getTime() > maxAge) {
          if (file.isDirectory()) {
            fs.rmSync(filePath, { recursive: true, force: true });
          } else {
            fs.unlinkSync(filePath);
          }
          console.log(`🗑️  清理过期文件: ${file.name}`);
        }
      }
    }
  }
}

export default globalTeardown;