/**
 * Playwright 前端自动化诊断脚本
 * 使用 Playwright (已安装) 代替 Puppeteer 检查前端页面错误、网络请求、性能指标
 */

import * as fs from 'fs';
import * as path from 'path';
import { chromium, Browser, Page, ConsoleMessage, Response } from 'playwright';

const repoRoot = path.resolve(__dirname, '../../..');
const defaultReportDir = path.join(repoRoot, 'test-results', 'frontend', 'diagnostics');
const defaultScreenshotDir = path.join(defaultReportDir, 'screenshots');

interface DiagnosticOptions {
  baseUrl: string;
  pages: string[];
  headless?: boolean;
  timeout?: number;
}

interface ConsoleLog {
  type: 'log' | 'info' | 'warn' | 'error' | 'debug';
  text: string;
  timestamp: string;
  location?: string;
  stackTrace?: string;
}

interface NetworkRequest {
  url: string;
  method: string;
  status: number;
  statusText: string;
  duration: number;
  size: number;
  timestamp: string;
  failed: boolean;
  error?: string;
}

interface PageMetrics {
  timestamp: string;
  url: string;
  title: string;
  domContentLoaded: number;
  loadComplete: number;
  totalRequests: number;
  failedRequests: number;
  totalSize: number;
  consoleErrors: number;
  consoleWarnings: number;
  screenshotPath: string;
}

interface DiagnosticReport {
  timestamp: string;
  baseUrl: string;
  environment: 'development' | 'production' | 'staging';
  pages: PageMetrics[];
  summary: {
    totalPages: number;
    totalErrors: number;
    totalWarnings: number;
    totalFailedRequests: number;
    pagesWithErrors: number;
    success: boolean;
  };
  consoleLogs: ConsoleLog[];
  networkLogs: NetworkRequest[];
}

export class FrontendDiagnostics {
  private browser: Browser | null = null;
  private reportDir: string;
  private screenshotDir: string;

  constructor(options?: { reportDir?: string; screenshotDir?: string }) {
    this.reportDir = options?.reportDir ?? defaultReportDir;
    this.screenshotDir = options?.screenshotDir ?? defaultScreenshotDir;

    // 确保目录存在
    if (!fs.existsSync(this.reportDir)) {
      fs.mkdirSync(this.reportDir, { recursive: true });
    }
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
    this.browser = await chromium.launch({
      headless: options.headless ?? true,
      args: ['--no-sandbox', '--disable-setuid-sandbox'],
    });

    const allConsoleLogs: ConsoleLog[] = [];
    const allNetworkLogs: NetworkRequest[] = [];
    const pageMetrics: PageMetrics[] = [];

    // 检查每个页面
    for (const pagePath of options.pages) {
      console.log(`\n📄 检查页面: ${pagePath}`);

      const url = `${options.baseUrl}${pagePath}`;
      const page = await this.browser.newPage();

      // 收集该页面的数据
      const { logs, network, metrics } = await this.checkPage(page, url, pagePath, options.timeout ?? 30000);

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
    const { jsonPath, htmlPath } = this.generateReport(report);

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
    pagePath: string,
    timeout: number
  ): Promise<{
    logs: ConsoleLog[];
    network: NetworkRequest[];
    metrics: PageMetrics;
  }> {
    const logs: ConsoleLog[] = [];
    const network: NetworkRequest[] = [];

    // 监听控制台消息
    page.on('console', async (msg: ConsoleMessage) => {
      const log: ConsoleLog = {
        type: msg.type() as ConsoleLog['type'],
        text: msg.text(),
        timestamp: new Date().toISOString(),
      };

      // 尝试获取堆栈跟踪
      if (msg.type() === 'error') {
        try {
          const stack = msg.stackTrace();
          if (stack) {
            log.stackTrace = stack.map((frame) => `${frame.url}:${frame.lineNumber}:${frame.columnNumber}`).join('\n');
            if (stack.length > 0) {
              log.location = `${stack[0].url}:${stack[0].lineNumber}`;
            }
          }
        } catch {
          // 忽略
        }
      }

      logs.push(log);
    });

    // 监听网络请求
    const requestTimes = new Map<string, number>();
    page.on('request', (request) => {
      requestTimes.set(request.url(), Date.now());
    });

    page.on('response', async (response: Response) => {
      const url = response.url();

      // 忽略 data: URL 和 blob: URL
      if (url.startsWith('data:') || url.startsWith('blob:')) {
        return;
      }

      const startTime = requestTimes.get(url) || Date.now();
      const networkReq: NetworkRequest = {
        url,
        method: response.request().method(),
        status: response.status(),
        statusText: response.statusText(),
        duration: Date.now() - startTime,
        size: 0,
        timestamp: new Date().toISOString(),
        failed: !response.ok(),
        error: !response.ok() ? response.statusText() : undefined,
      };

      try {
        // 尝试获取内容长度
        const headers = response.headers();
        const contentLength = headers['content-length'];
        if (contentLength) {
          networkReq.size = parseInt(contentLength, 10);
        }
      } catch {
        // 忽略
      }

      network.push(networkReq);
    });

    // 监听页面错误
    page.on('pageerror', (error: Error) => {
      logs.push({
        type: 'error',
        text: error.message,
        timestamp: new Date().toISOString(),
        stackTrace: error.stack,
      });
    });

    // 设置超时
    page.setDefaultTimeout(timeout);

    // 访问页面
    const startTime = Date.now();
    await page.goto(url, { waitUntil: 'networkidle', timeout });

    // 等待一段时间以确保所有异步操作完成
    await page.waitForTimeout(2000);

    // 收集性能指标
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
        domContentLoaded: loadTime * 0.6, // 估算
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
    try {
      const url = new URL(baseUrl);

      if (url.hostname === 'localhost' || url.hostname === '127.0.0.1' || url.hostname === '::1') {
        return 'development';
      }

      if (url.hostname.includes('staging') || url.hostname.includes('stg') || url.hostname.includes('test')) {
        return 'staging';
      }

      return 'production';
    } catch {
      return 'development';
    }
  }

  /**
   * 生成报告
   */
  private generateReport(report: DiagnosticReport): { jsonPath: string; htmlPath: string } {
    const timestamp = report.timestamp.replace(/[:.]/g, '-');
    const jsonPath = path.join(this.reportDir, `diagnostic-report-${timestamp}.json`);
    const htmlPath = path.join(this.reportDir, `diagnostic-report-${timestamp}.html`);

    // 保存 JSON 报告
    fs.writeFileSync(jsonPath, JSON.stringify(report, null, 2));

    // 生成 HTML 报告
    const html = this.generateHTMLReport(report);
    fs.writeFileSync(htmlPath, html);

    return { jsonPath, htmlPath };
  }

  /**
   * 生成 HTML 报告
   */
  private generateHTMLReport(report: DiagnosticReport): string {
    const { summary, consoleLogs, networkLogs, pages } = report;
    const hasErrors = !summary.success;

    return `<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>前端诊断报告 - ${report.timestamp}</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f5f5f5; padding: 20px; }
    .container { max-width: 1400px; margin: 0 auto; }
    .header { background: white; padding: 30px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
    .status { padding: 15px 20px; border-radius: 6px; font-size: 18px; font-weight: bold; margin-bottom: 20px; }
    .status.success { background: #52c41a; color: white; }
    .status.error { background: #ff4d4f; color: white; }
    .summary { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; }
    .metric { background: #f9f9f9; padding: 20px; border-radius: 6px; text-align: center; }
    .metric-value { font-size: 32px; font-weight: bold; color: #1890ff; }
    .metric-label { color: #666; margin-top: 8px; }
    .section { background: white; padding: 30px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
    .section-title { font-size: 20px; font-weight: bold; margin-bottom: 20px; border-bottom: 2px solid #f0f0f0; padding-bottom: 10px; }
    .log-entry { padding: 12px; margin-bottom: 10px; border-radius: 4px; border-left: 4px solid; }
    .log-entry.error { background: #fff2f0; border-color: #ff4d4f; }
    .log-entry.warn { background: #fffbe6; border-color: #faad14; }
    .log-entry.info { background: #e6f7ff; border-color: #1890ff; }
    .log-time { font-size: 12px; color: #999; margin-bottom: 4px; }
    .log-text { font-family: monospace; font-size: 14px; white-space: pre-wrap; word-break: break-all; }
    .network-entry { display: grid; grid-template-columns: 1fr 100px 80px 100px; gap: 10px; padding: 12px; border-bottom: 1px solid #f0f0f0; }
    .network-entry:hover { background: #f9f9f9; }
    .network-url { font-family: monospace; font-size: 13px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .network-status { padding: 4px 8px; border-radius: 4px; font-size: 12px; text-align: center; }
    .network-status.success { background: #f6ffed; color: #52c41a; }
    .network-status.error { background: #fff2f0; color: #ff4d4f; }
    .screenshot { max-width: 100%; height: auto; border-radius: 4px; margin-top: 10px; }
    .page-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
    .page-card { background: #f9f9f9; padding: 20px; border-radius: 6px; }
    .page-title { font-weight: bold; margin-bottom: 10px; }
    .page-metric { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #e8e8e8; }
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>前端诊断报告</h1>
      <p style="color: #666; margin-top: 10px;">
        生成时间: ${new Date(report.timestamp).toLocaleString('zh-CN')}<br>
        环境: ${report.environment}<br>
        基础 URL: ${report.baseUrl}
      </p>
    </div>

    <div class="status ${hasErrors ? 'error' : 'success'}">
      ${hasErrors ? '✗ 发现前端问题' : '✓ 前端诊断通过'}
    </div>

    <div class="summary">
      <div class="metric">
        <div class="metric-value">${summary.totalPages}</div>
        <div class="metric-label">检查页面</div>
      </div>
      <div class="metric">
        <div class="metric-value">${summary.totalErrors}</div>
        <div class="metric-label">控制台错误</div>
      </div>
      <div class="metric">
        <div class="metric-value">${summary.totalWarnings}</div>
        <div class="metric-label">警告</div>
      </div>
      <div class="metric">
        <div class="metric-value">${summary.totalFailedRequests}</div>
        <div class="metric-label">失败请求</div>
      </div>
    </div>

    ${hasErrors ? `
    <div class="section">
      <div class="section-title">控制台错误 (${consoleLogs.filter(l => l.type === 'error').length})</div>
      ${consoleLogs.filter(l => l.type === 'error').map(log => `
        <div class="log-entry error">
          <div class="log-time">${new Date(log.timestamp).toLocaleString('zh-CN')}</div>
          <div class="log-text">${this.escapeHtml(log.text)}</div>
          ${log.stackTrace ? `<div class="log-text" style="margin-top: 8px; font-size: 12px;">${this.escapeHtml(log.stackTrace)}</div>` : ''}
        </div>
      `).join('')}
    </div>
    ` : ''}

    ${summary.totalWarnings > 0 ? `
    <div class="section">
      <div class="section-title">警告 (${consoleLogs.filter(l => l.type === 'warn').length})</div>
      ${consoleLogs.filter(l => l.type === 'warn').map(log => `
        <div class="log-entry warn">
          <div class="log-time">${new Date(log.timestamp).toLocaleString('zh-CN')}</div>
          <div class="log-text">${this.escapeHtml(log.text)}</div>
        </div>
      `).join('')}
    </div>
    ` : ''}

    ${summary.totalFailedRequests > 0 ? `
    <div class="section">
      <div class="section-title">失败的网络请求 (${networkLogs.filter(n => n.failed).length})</div>
      <div class="network-header" style="display: grid; grid-template-columns: 1fr 100px 80px 100px; gap: 10px; padding: 12px; background: #f5f5f5; font-weight: bold;">
        <div>URL</div>
        <div>方法</div>
        <div>状态</div>
        <div>耗时</div>
      </div>
      ${networkLogs.filter(n => n.failed).map(req => `
        <div class="network-entry">
          <div class="network-url" title="${this.escapeHtml(req.url)}">${this.escapeHtml(req.url)}</div>
          <div>${req.method}</div>
          <div class="network-status error">${req.status}</div>
          <div>${req.duration}ms</div>
        </div>
      `).join('')}
    </div>
    ` : ''}

    <div class="section">
      <div class="section-title">页面性能指标</div>
      <div class="page-grid">
        ${pages.map(page => `
          <div class="page-card">
            <div class="page-title">${this.escapeHtml(page.title)}</div>
            <div style="font-size: 12px; color: #999; margin-bottom: 10px;">${page.url}</div>
            <div class="page-metric">
              <span>DOM 加载</span>
              <strong>${page.domContentLoaded.toFixed(0)}ms</strong>
            </div>
            <div class="page-metric">
              <span>完全加载</span>
              <strong>${page.loadComplete.toFixed(0)}ms</strong>
            </div>
            <div class="page-metric">
              <span>请求数</span>
              <strong>${page.totalRequests}</strong>
            </div>
            <div class="page-metric">
              <span>失败请求</span>
              <strong style="color: ${page.failedRequests > 0 ? '#ff4d4f' : '#52c41a'}">${page.failedRequests}</strong>
            </div>
            <div class="page-metric">
              <span>控制台错误</span>
              <strong style="color: ${page.consoleErrors > 0 ? '#ff4d4f' : '#52c41a'}">${page.consoleErrors}</strong>
            </div>
          </div>
        `).join('')}
      </div>
    </div>
  </div>
</body>
</html>`;
  }

  private escapeHtml(text: string): string {
    const map: Record<string, string> = {
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#039;',
    };
    return text.replace(/[&<>"']/g, (char) => map[char]);
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

const readNodeEnv = (name: string): string | undefined => {
  const rawValue = process.env[name];
  return typeof rawValue === 'string' && rawValue !== '' ? rawValue : undefined;
};

const readNodeEnvBoolean = (name: string, defaultValue: boolean): boolean => {
  const rawValue = readNodeEnv(name);
  if (rawValue == null) {
    return defaultValue;
  }
  const normalizedValue = rawValue.toLowerCase();
  if (normalizedValue === 'true' || normalizedValue === '1') {
    return true;
  }
  if (normalizedValue === 'false' || normalizedValue === '0') {
    return false;
  }
  return defaultValue;
};

const readNodeEnvNumber = (name: string, defaultValue: number): number => {
  const rawValue = readNodeEnv(name);
  if (rawValue == null) {
    return defaultValue;
  }
  const parsedValue = Number.parseInt(rawValue, 10);
  return Number.isNaN(parsedValue) ? defaultValue : parsedValue;
};

/**
 * CLI 入口
 */
export async function main() {
  const baseUrl = readNodeEnv('BASE_URL') ?? 'http://localhost:5173';
  const pages = readNodeEnv('PAGES')?.split(',') ?? DEFAULT_ROUTES;

  const diagnostics = new FrontendDiagnostics();

  try {
    const report = await diagnostics.runDiagnostics({
      baseUrl,
      pages,
      headless: readNodeEnvBoolean('HEADLESS', true),
      timeout: readNodeEnvNumber('TIMEOUT', 30000),
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
