/**
 * 前端诊断系统类型定义
 * 用于 Puppeteer 自动化检查和错误报告
 */

export interface ConsoleMessage {
  type: 'log' | 'warn' | 'error' | 'info' | 'debug';
  text: string;
  timestamp: string;
  location?: string;
  stackTrace?: string;
}

export interface NetworkRequest {
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

export interface PageMetrics {
  timestamp: string;
  url: string;
  title: string;

  // 性能指标
  domContentLoaded: number;
  loadComplete: number;
  firstPaint?: number;
  firstContentfulPaint?: number;

  // 资源统计
  totalRequests: number;
  failedRequests: number;
  totalSize: number;

  // 控制台统计
  consoleErrors: number;
  consoleWarnings: number;

  // 截图路径
  screenshotPath?: string;
}

export interface DiagnosticReport {
  timestamp: string;
  baseUrl: string;
  environment: 'development' | 'production' | 'staging';

  // 页面检查结果
  pages: PageMetrics[];

  // 汇总
  summary: {
    totalPages: number;
    totalErrors: number;
    totalWarnings: number;
    totalFailedRequests: number;
    pagesWithErrors: number;
    success: boolean;
  };

  // 详细日志
  consoleLogs: ConsoleMessage[];
  networkLogs: NetworkRequest[];
}

export interface DiagnosticOptions {
  baseUrl: string;
  pages: string[];
  screenshotDir?: string;
  headless?: boolean;
  timeout?: number;
  auth?: {
    username: string;
    password: string;
  };
}

export interface RouteInfo {
  path: string;
  name: string;
  requiresAuth: boolean;
  permissions?: string[];
}
