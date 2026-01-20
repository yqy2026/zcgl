/**
 * Playwright Diagnostics Runner
 * Simple JavaScript wrapper to run diagnostics
 */

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

// Configuration
const BASE_URL = process.env.BASE_URL || 'http://localhost:5173';
const HEADLESS = process.env.HEADLESS !== 'false';
const PAGES = process.env.PAGES?.split(',') || [
  '/',
  '/dashboard',
  '/assets/list',
];

async function runDiagnostics() {
  console.log('🔍 开始前端诊断...\n');
  console.log(`📍 目标 URL: ${BASE_URL}`);
  console.log(`📄 检查页面数: ${PAGES.length}`);
  console.log(`🔐 Headless模式: ${HEADLESS}\n`);

  const browser = await chromium.launch({
    headless: HEADLESS,
    channel: 'chrome', // Use system Chrome instead of downloaded Chromium
  });

  const results = {
    timestamp: new Date().toISOString(),
    baseUrl: BASE_URL,
    pages: [],
    summary: {
      totalPages: PAGES.length,
      totalErrors: 0,
      totalWarnings: 0,
      pagesWithErrors: 0,
      success: true,
    },
  };

  for (const pagePath of PAGES) {
    console.log(`\n📄 检查页面: ${pagePath}`);

    const page = await browser.newPage();
    const url = `${BASE_URL}${pagePath}`;

    const pageResult = {
      path: pagePath,
      url: url,
      errors: [],
      warnings: [],
      failedRequests: [],
      loadTime: 0,
    };

    // Collect console logs
    page.on('console', async (msg) => {
      const type = msg.type();
      const text = msg.text();

      if (type === 'error') {
        pageResult.errors.push({
          text,
          location: msg.location(),
        });
        results.summary.totalErrors++;
      } else if (type === 'warning') {
        pageResult.warnings.push({ text });
        results.summary.totalWarnings++;
      }
    });

    // Collect failed network requests
    page.on('response', (response) => {
      if (!response.ok()) {
        pageResult.failedRequests.push({
          url: response.url(),
          status: response.status(),
          statusText: response.statusText(),
        });
      }
    });

    // Navigate to page
    const startTime = Date.now();
    try {
      await page.goto(url, { waitUntil: 'networkidle', timeout: 30000 });
      await page.waitForTimeout(2000);
      pageResult.loadTime = Date.now() - startTime;
      pageResult.success = true;

      console.log(`  ✓ 加载时间: ${pageResult.loadTime}ms`);
      console.log(`  ✓ 错误: ${pageResult.errors.length}`);
      console.log(`  ✓ 警告: ${pageResult.warnings.length}`);
      console.log(`  ✓ 失败请求: ${pageResult.failedRequests.length}`);

    } catch (error) {
      pageResult.loadTime = Date.now() - startTime;
      pageResult.success = false;
      pageResult.errors.push({
        text: `Navigation failed: ${error.message}`,
      });
      console.log(`  ✗ 导航失败: ${error.message}`);
    }

    if (pageResult.errors.length > 0 || pageResult.failedRequests.length > 0) {
      results.summary.pagesWithErrors++;
      results.summary.success = false;
    }

    results.pages.push(pageResult);
    await page.close();
  }

  await browser.close();

  // Print summary
  console.log('\n' + '='.repeat(60));
  console.log('📊 诊断摘要');
  console.log('='.repeat(60));
  console.log(`总页面数: ${results.summary.totalPages}`);
  console.log(`总错误数: ${results.summary.totalErrors}`);
  console.log(`总警告数: ${results.summary.totalWarnings}`);
  console.log(`有问题页面: ${results.summary.pagesWithErrors}`);
  console.log('='.repeat(60));

  // Print details for pages with errors
  if (results.summary.pagesWithErrors > 0) {
    console.log('\n❌ 发现问题的页面:\n');

    for (const page of results.pages) {
      if (page.errors.length > 0 || page.failedRequests.length > 0) {
        console.log(`\n📄 ${page.path}`);
        console.log(`   URL: ${page.url}`);

        if (page.errors.length > 0) {
          console.log(`   错误 (${page.errors.length}):`);
          page.errors.forEach((err, i) => {
            console.log(`     ${i + 1}. ${err.text}`);
            if (err.location) {
              console.log(`        at ${err.location.url}:${err.location.lineNumber}`);
            }
          });
        }

        if (page.failedRequests.length > 0) {
          console.log(`   失败请求 (${page.failedRequests.length}):`);
          page.failedRequests.forEach((req, i) => {
            console.log(`     ${i + 1}. ${req.status} ${req.method} ${req.url}`);
          });
        }
      }
    }

    console.log('\n' + '='.repeat(60));
    console.log('✗ 诊断发现问题');
    console.log('='.repeat(60));
    process.exit(1);
  } else {
    console.log('\n✅ 所有检查通过');
    process.exit(0);
  }
}

runDiagnostics().catch((error) => {
  console.error('\n❌ 诊断失败:', error);
  process.exit(1);
});
