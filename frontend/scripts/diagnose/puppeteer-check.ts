/**
 * Puppeteer 前端自动化诊断脚本
 * 自动打开 Chrome 浏览器，检查前端页面错误、网络请求、性能指标
 */

import * as fs from 'fs';
import * as path from 'path';
import puppeteer, { Browser, Page } from 'puppeteer';
import type { ConsoleMessage, DiagnosticOptions, DiagnosticReport, NetworkRequest, PageMetrics } from './types';
import { DiagnosticReporter } from './reporter';

const repoRoot = path.resolve(__dirname, '../../..');
const defaultScreenshotDir = path.join(repoRoot, 'test-results', 'frontend', 'diagnostics', 'screenshots');

export class FrontendDiagnostics {
  private browser: Browser | null = null;
  private reporter: DiagnosticReporter;
  private screenshotDir: string;

  constructor(options?: { reportDir?: string; screenshotDir?: string }) {
    this.reporter = new DiagnosticReporter(options?.reportDir);
    this.screenshotDir = options?.screenshotDir ?? defaultScreenshotDir;

    // 确保截图目录存在
    if (!fs.existsSync(this.screenshotDir)) {
      fs.mkdirSync(this.screenshotDir, { recursive: true });
    }
  }

  /**
   * 运行完整诊断
   */
  async runDiagnostics(options: DiagnosticOptions): Promise<DiagnosticReport> {
    console.log('🔍 开始前端诊断...\n');
    console.log(`📍 目标 URL: ${options.baseUrl}`);
    console.log(`📄 检查页面数: ${options.pages.length}`);
    console.log(`🔐 Headless模式: ${options.headless ?? true}\n`);

    // 启动浏览器
    this.browser = await puppeteer.launch({
      headless: options.headless ?? true,
      args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage'],
      defaultViewport: { width: 1920, height: 1080 },
    });

    const allConsoleLogs: ConsoleMessage[] = [];
    const allNetworkLogs: NetworkRequest[] = [];
    const pageMetrics: PageMetrics[] = [];

    // 检查每个页面
    for (const pagePath of options.pages) {
      console.log(`\n📄 检查页面: ${pagePath}`);

      const url = `${options.baseUrl}${pagePath}`;
      const page = await this.browser.newPage();

      // 收集该页面的数据
      const { logs, network, metrics } = await this.checkPage(page, url, pagePath);

      allConsoleLogs.push(...logs);
      allNetworkLogs.push(...network);
      pageMetrics.push(metrics);

      console.log(`  ✓ DOM加载: ${metrics.domContentLoaded.toFixed(0)}ms`);
      console.log(`  ✓ 完全加载: ${metrics.loadComplete.toFixed(0)}ms`);
      console.log(`  ✓ 控制台错误: ${metrics.consoleErrors}`);
      console.log(`  ✓ 失败请求: ${metrics.failedRequests}`);

      await page.close();
    }

    // 生成报告
    const report: DiagnosticReport = {
      timestamp: new Date().toISOString(),
      baseUrl: options.baseUrl,
      environment: this.detectEnvironment(options.baseUrl),
      pages: pageMetrics,
      summary: {
        totalPages: pageMetrics.length,
        totalErrors: allConsoleLogs.filter((log) => log.type === 'error').length,
        totalWarnings: allConsoleLogs.filter((log) => log.type === 'warn').length,
        totalFailedRequests: allNetworkLogs.filter((log) => log.failed).length,
        pagesWithErrors: pageMetrics.filter((p) => p.consoleErrors > 0 || p.failedRequests > 0).length,
        success:
          allConsoleLogs.filter((log) => log.type === 'error').length === 0 &&
          allNetworkLogs.filter((log) => log.failed).length === 0,
      },
      consoleLogs: allConsoleLogs,
      networkLogs: allNetworkLogs,
    };

    // 关闭浏览器
    await this.browser.close();

    // 保存报告
    console.log('\n📊 生成诊断报告...');
    const { jsonPath, htmlPath } = this.reporter.generateReport(report);

    console.log(`\n✅ 诊断完成!`);
    console.log(`  JSON报告: ${jsonPath}`);
    console.log(`  HTML报告: ${htmlPath}`);

    return report;
  }

  /**
   * 检查单个页面
   */
  private async checkPage(
    page: Page,
    url: string,
    pagePath: string
  ): Promise<{
    logs: ConsoleMessage[];
    network: NetworkRequest[];
    metrics: PageMetrics;
  }> {
    const logs: ConsoleMessage[] = [];
    const network: NetworkRequest[] = [];

    // 监听控制台消息
    page.on('console', (msg) => {
      const log: ConsoleMessage = {
        type: msg.type() as ConsoleMessage['type'],
        text: msg.text(),
        timestamp: new Date().toISOString(),
        location: msg.location()?.url ? `${msg.location().url}:${msg.location().lineNumber}` : undefined,
      };

      // 尝试获取堆栈跟踪
      if (log.type === 'error') {
        try {
          log.stackTrace = msg.stackTrace()?.map((frame) => frame.text).join('\n');
        } catch {
          // 忽略
        }
      }

      logs.push(log);
    });

    // 监听网络请求
    page.on('response', async (response) => {
      const req = response.request();
      const url = response.url();

      // 忽略 data: URL 和 blob: URL
      if (url.startsWith('data:') || url.startsWith('blob:')) {
        return;
      }

      const networkReq: NetworkRequest = {
        url,
        method: req.method(),
        status: response.status(),
        statusText: response.statusText(),
        duration: 0, // 将在 request 时计算
        size: 0,
        timestamp: new Date().toISOString(),
        failed: !response.ok(),
        error: !response.ok() ? response.statusText() : undefined,
      };

      try {
        // 尝试获取响应头中的内容长度
        const contentLength = response.headers()['content-length'];
        if (contentLength) {
          networkReq.size = parseInt(contentLength, 10);
        }
      } catch {
        // 忽略
      }

      network.push(networkReq);
    });

    // 监听请求时间
    const requestTimes = new Map<string, number>();
    page.on('request', (request) => {
      requestTimes.set(request.url(), Date.now());
    });

    page.on('response', (response) => {
      const startTime = requestTimes.get(response.url());
      if (startTime) {
        const req = network.find((r) => r.url === response.url());
        if (req) {
          req.duration = Date.now() - startTime;
        }
      }
    });

    // 监听页面错误
    page.on('pageerror', (error) => {
      logs.push({
        type: 'error',
        text: error.message,
        timestamp: new Date().toISOString(),
        stackTrace: error.stack,
      });
    });

    // 设置超时
    await page.setDefaultTimeout(options?.timeout ?? 30000);
    await page.setDefaultNavigationTimeout(options?.timeout ?? 30000);

    // 访问页面
    const startTime = Date.now();
    await page.goto(url, { waitUntil: 'networkidle0', timeout: options?.timeout ?? 30000 });

    // 等待一段时间以确保所有异步操作完成
    await page.waitForTimeout(2000);

    // 收集性能指标
    const metrics = await page.metrics();
    const loadTime = Date.now() - startTime;

    // 截图
    const screenshotPath = path.join(this.screenshotDir, `${pagePath.replace(/\//g, '-')}.png`);
    await page.screenshot({ path: screenshotPath, fullPage: true });

    // 获取页面标题
    const title = await page.title();

    return {
      logs,
      network,
      metrics: {
        timestamp: new Date().toISOString(),
        url,
        title,
        domContentLoaded: metrics.DomContentLoaded || loadTime * 0.6,
        loadComplete: loadTime,
        totalRequests: network.length,
        failedRequests: network.filter((n) => n.failed).length,
        totalSize: network.reduce((sum, n) => sum + n.size, 0),
        consoleErrors: logs.filter((log) => log.type === 'error').length,
        consoleWarnings: logs.filter((log) => log.type === 'warn').length,
        screenshotPath,
      },
    };
  }

  /**
   * 检测环境类型
   */
  private detectEnvironment(baseUrl: string): 'development' | 'production' | 'staging' {
    const url = new URL(baseUrl);

    if (url.hostname === 'localhost' || url.hostname === '127.0.0.1' || url.hostname === '::1') {
      return 'development';
    }

    if (url.hostname.includes('staging') || url.hostname.includes('stg') || url.hostname.includes('test')) {
      return 'staging';
    }

    return 'production';
  }
}

/**
 * 默认配置的路由
 */
export const DEFAULT_ROUTES = [
  '/',
  '/dashboard',
  '/assets/list',
  '/rental/contracts',
  '/maintenance/requests',
  '/financial/overview',
  '/reports/analysis',
];

/**
 * CLI 入口
 */
export async function main() {
  const baseUrl = process.env.BASE_URL || 'http://localhost:5173';
  const pages = process.env.PAGES?.split(',') || DEFAULT_ROUTES;

  const diagnostics = new FrontendDiagnostics();

  try {
    const report = await diagnostics.runDiagnostics({
      baseUrl,
      pages,
      headless: process.env.HEADLESS !== 'false',
      timeout: parseInt(process.env.TIMEOUT || '30000', 10),
    });

    // 根据结果设置退出码
    if (!report.summary.success) {
      console.error('\n❌ 诊断发现问题，请查看报告详情');
      process.exit(1);
    } else {
      console.log('\n✅ 所有检查通过');
      process.exit(0);
    }
  } catch (error) {
    console.error('❌ 诊断失败:', error);
    process.exit(1);
  }
}

// 如果直接运行此脚本
if (require.main === module) {
  main();
}
