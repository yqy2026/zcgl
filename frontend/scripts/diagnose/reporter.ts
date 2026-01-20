/**
 * 诊断报告生成器
 * 生成详细的 HTML 和 JSON 格式的诊断报告
 */

import * as fs from 'fs';
import * as path from 'path';
import type { ConsoleMessage, DiagnosticReport, NetworkRequest, PageMetrics } from './types';

export class DiagnosticReporter {
  private reportDir: string;
  private timestamp: string;

  constructor(reportDir: string = 'frontend/diagnostics') {
    this.reportDir = reportDir;
    this.timestamp = new Date().toISOString().replace(/[:.]/g, '-');

    // 确保目录存在
    if (!fs.existsSync(reportDir)) {
      fs.mkdirSync(reportDir, { recursive: true });
    }
  }

  /**
   * 生成完整的诊断报告
   */
  generateReport(data: DiagnosticReport): { jsonPath: string; htmlPath: string } {
    const jsonPath = this.saveJsonReport(data);
    const htmlPath = this.saveHtmlReport(data);

    return { jsonPath, htmlPath };
  }

  /**
   * 保存 JSON 格式报告
   */
  private saveJsonReport(data: DiagnosticReport): string {
    const filename = `diagnostic-report-${this.timestamp}.json`;
    const filepath = path.join(this.reportDir, filename);

    fs.writeFileSync(filepath, JSON.stringify(data, null, 2), 'utf-8');

    return filepath;
  }

  /**
   * 保存 HTML 格式报告
   */
  private saveHtmlReport(data: DiagnosticReport): string {
    const filename = `diagnostic-report-${this.timestamp}.html`;
    const filepath = path.join(this.reportDir, filename);

    const html = this.generateHtml(data);
    fs.writeFileSync(filepath, html, 'utf-8');

    return filepath;
  }

  /**
   * 生成 HTML 报告内容
   */
  private generateHtml(data: DiagnosticReport): string {
    const isSuccess = data.summary.success;

    return `<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>前端诊断报告 - ${data.timestamp}</title>
  <style>
    * {
      margin: 0;
      padding: 0;
      box-sizing: border-box;
    }

    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB',
        'Microsoft YaHei', 'Helvetica Neue', Helvetica, Arial, sans-serif;
      line-height: 1.6;
      color: #333;
      background: #f5f5f5;
      padding: 20px;
    }

    .container {
      max-width: 1200px;
      margin: 0 auto;
      background: white;
      border-radius: 8px;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
      overflow: hidden;
    }

    .header {
      background: ${isSuccess ? '#52c41a' : '#ff4d4f'};
      color: white;
      padding: 24px;
    }

    .header h1 {
      font-size: 28px;
      margin-bottom: 8px;
    }

    .header .meta {
      opacity: 0.9;
      font-size: 14px;
    }

    .summary {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 16px;
      padding: 24px;
      background: #fafafa;
      border-bottom: 1px solid #e8e8e8;
    }

    .summary-card {
      background: white;
      padding: 16px;
      border-radius: 6px;
      border: 1px solid #e8e8e8;
    }

    .summary-card .label {
      font-size: 12px;
      color: #8c8c8c;
      margin-bottom: 4px;
    }

    .summary-card .value {
      font-size: 24px;
      font-weight: 600;
      color: ${isSuccess ? '#52c41a' : '#ff4d4f'};
    }

    .section {
      padding: 24px;
      border-bottom: 1px solid #e8e8e8;
    }

    .section-title {
      font-size: 18px;
      font-weight: 600;
      margin-bottom: 16px;
      color: #262626;
    }

    .page-card {
      background: #fafafa;
      border: 1px solid #e8e8e8;
      border-radius: 6px;
      padding: 16px;
      margin-bottom: 12px;
    }

    .page-card.has-errors {
      border-left: 4px solid #ff4d4f;
    }

    .page-card.no-errors {
      border-left: 4px solid #52c41a;
    }

    .page-card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 12px;
    }

    .page-path {
      font-weight: 600;
      font-size: 16px;
    }

    .page-badge {
      padding: 4px 12px;
      border-radius: 12px;
      font-size: 12px;
      font-weight: 600;
    }

    .badge-success {
      background: #f6ffed;
      color: #52c41a;
      border: 1px solid #b7eb8f;
    }

    .badge-error {
      background: #fff2f0;
      color: #ff4d4f;
      border: 1px solid #ffccc7;
    }

    .metrics-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
      gap: 12px;
      font-size: 13px;
    }

    .metric-item {
      display: flex;
      justify-content: space-between;
    }

    .metric-label {
      color: #8c8c8c;
    }

    .console-log {
      background: #1e1e1e;
      color: #d4d4d4;
      padding: 12px;
      border-radius: 4px;
      font-family: 'Courier New', monospace;
      font-size: 12px;
      margin-bottom: 8px;
      overflow-x: auto;
    }

    .log-error {
      color: #ff4d4f;
    }

    .log-warn {
      color: #faad14;
    }

    .network-table {
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
    }

    .network-table th,
    .network-table td {
      padding: 8px 12px;
      text-align: left;
      border-bottom: 1px solid #e8e8e8;
    }

    .network-table th {
      background: #fafafa;
      font-weight: 600;
      color: #262626;
    }

    .status-badge {
      padding: 2px 8px;
      border-radius: 4px;
      font-size: 11px;
      font-weight: 600;
    }

    .status-success {
      background: #f6ffed;
      color: #52c41a;
    }

    .status-error {
      background: #fff2f0;
      color: #ff4d4f;
    }

    .screenshot {
      width: 100%;
      border: 1px solid #e8e8e8;
      border-radius: 6px;
      margin-top: 12px;
    }
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>${isSuccess ? '✓ 前端诊断通过' : '✗ 发现前端问题'}</h1>
      <div class="meta">
        环境: ${data.environment} |
        URL: ${data.baseUrl} |
        时间: ${data.timestamp}
      </div>
    </div>

    <div class="summary">
      <div class="summary-card">
        <div class="label">检查页面</div>
        <div class="value">${data.summary.totalPages}</div>
      </div>
      <div class="summary-card">
        <div class="label">控制台错误</div>
        <div class="value">${data.summary.totalErrors}</div>
      </div>
      <div class="summary-card">
        <div class="label">控制台警告</div>
        <div class="value">${data.summary.totalWarnings}</div>
      </div>
      <div class="summary-card">
        <div class="label">失败请求</div>
        <div class="value">${data.summary.totalFailedRequests}</div>
      </div>
      <div class="summary-card">
        <div class="label">问题页面</div>
        <div class="value">${data.summary.pagesWithErrors}</div>
      </div>
    </div>

    <div class="section">
      <h2 class="section-title">页面检查结果</h2>
      ${data.pages.map((page) => this.renderPageCard(page)).join('')}
    </div>

    ${data.consoleLogs.length > 0 ? `
    <div class="section">
      <h2 class="section-title">控制台日志 (${data.consoleLogs.length})</h2>
      ${data.consoleLogs.map((log) => this.renderConsoleLog(log)).join('')}
    </div>
    ` : ''}

    ${data.networkLogs.filter((log) => log.failed).length > 0 ? `
    <div class="section">
      <h2 class="section-title">失败的网络请求</h2>
      ${this.renderNetworkTable(data.networkLogs.filter((log) => log.failed))}
    </div>
    ` : ''}
  </div>

  <script>
    // 自动刷新报告
    setTimeout(() => location.reload(), 60000);
  </script>
</body>
</html>`;
  }

  private renderPageCard(page: PageMetrics): string {
    const hasErrors = page.consoleErrors > 0 || page.failedRequests > 0;

    return `
    <div class="page-card ${hasErrors ? 'has-errors' : 'no-errors'}">
      <div class="page-card-header">
        <div class="page-path">${page.url}</div>
        <span class="page-badge ${hasErrors ? 'badge-error' : 'badge-success'}">
          ${hasErrors ? '发现问题' : '正常'}
        </span>
      </div>

      <div class="metrics-grid">
        <div class="metric-item">
          <span class="metric-label">DOM加载:</span>
          <span>${page.domContentLoaded.toFixed(0)}ms</span>
        </div>
        <div class="metric-item">
          <span class="metric-label">完全加载:</span>
          <span>${page.loadComplete.toFixed(0)}ms</span>
        </div>
        <div class="metric-item">
          <span class="metric-label">请求数:</span>
          <span>${page.totalRequests}</span>
        </div>
        <div class="metric-item">
          <span class="metric-label">失败:</span>
          <span>${page.failedRequests}</span>
        </div>
        <div class="metric-item">
          <span class="metric-label">错误:</span>
          <span>${page.consoleErrors}</span>
        </div>
        <div class="metric-item">
          <span class="metric-label">警告:</span>
          <span>${page.consoleWarnings}</span>
        </div>
      </div>

      ${page.screenshotPath ? `
        <img src="${page.screenshotPath}" alt="Screenshot" class="screenshot" />
      ` : ''}
    </div>
    `;
  }

  private renderConsoleLog(log: ConsoleMessage): string {
    const typeClass = log.type === 'error' ? 'log-error' : log.type === 'warn' ? 'log-warn' : '';

    return `
    <div class="console-log ${typeClass}">
      <div>[${log.timestamp}] [${log.type.toUpperCase()}] ${log.text}</div>
      ${log.location ? `<div style="color: #8c8c8c; font-size: 11px;">位置: ${log.location}</div>` : ''}
      ${log.stackTrace ? `<div style="color: #8c8c8c; font-size: 11px; margin-top: 4px;">${log.stackTrace}</div>` : ''}
    </div>
    `;
  }

  private renderNetworkTable(requests: NetworkRequest[]): string {
    return `
    <table class="network-table">
      <thead>
        <tr>
          <th>方法</th>
          <th>URL</th>
          <th>状态</th>
          <th>耗时</th>
          <th>大小</th>
          <th>错误</th>
        </tr>
      </thead>
      <tbody>
        ${requests
          .map((req) => `
          <tr>
            <td>${req.method}</td>
            <td>${req.url}</td>
            <td><span class="status-badge ${req.failed ? 'status-error' : 'status-success'}">${req.status}</span></td>
            <td>${req.duration}ms</td>
            <td>${this.formatBytes(req.size)}</td>
            <td>${req.error || '-'}</td>
          </tr>
        `)
          .join('')}
      </tbody>
    </table>
    `;
  }

  private formatBytes(bytes: number): string {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }
}
