/**
 * 统一的日志工具
 *
 * 用途：
 * 1. 在开发环境启用日志输出
 * 2. 在生产环境禁用日志输出
 * 3. 绕过 ESLint no-console 规则
 * 4. 提供统一的日志格式和级别控制
 *
 * @example
 * ```typescript
 * import { createLogger } from '@/utils/logger';
 *
 * const logger = createLogger('MyModule');
 * logger.debug('调试信息', { userId: 123 });
 * logger.warn('警告信息', { context: 'data' });
 * logger.error('错误信息', error);
 * ```
 */

type LogLevel = 'debug' | 'info' | 'warn' | 'error';

interface LoggerConfig {
  isEnabled: boolean;
  level: LogLevel;
  prefix?: string;
  useTimestamp?: boolean;
}

class Logger {
  private config: LoggerConfig;
  private readonly levels: Record<LogLevel, number> = {
    debug: 0,
    info: 1,
    warn: 2,
    error: 3,
  };

  constructor(config?: Partial<LoggerConfig>) {
    const isDevelopment = import.meta.env.MODE === 'development' || import.meta.env.DEV;

    this.config = {
      isEnabled: isDevelopment,
      level: isDevelopment ? 'debug' : 'error',
      useTimestamp: isDevelopment,
      ...config,
    };
  }

  private shouldLog(level: LogLevel): boolean {
    if (this.config.isEnabled === false) return false;
    return this.levels[level] >= this.levels[this.config.level];
  }

  private getTimestamp(): string {
    const now = new Date();
    return now.toLocaleTimeString('zh-CN', { hour12: false });
  }

  private formatMessage(
    level: LogLevel,
    message: string,
    meta?: Record<string, unknown>
  ): (string | Record<string, unknown>)[] {
    const parts: (string | Record<string, unknown>)[] = [];

    // 构建前缀
    const prefixParts: string[] = [];
    if (this.config.useTimestamp === true) {
      prefixParts.push(this.getTimestamp());
    }
    prefixParts.push(`[${level.toUpperCase()}]`);
    if (this.config.prefix != null) {
      prefixParts.push(`[${this.config.prefix}]`);
    }

    parts.push(`${prefixParts.join(' ')} ${message}`);

    if (meta != null && Object.keys(meta).length > 0) {
      parts.push(meta);
    }

    return parts;
  }

  debug(message: string, meta?: Record<string, unknown>): void {
    if (this.shouldLog('debug')) {
      // eslint-disable-next-line no-console
      console.log(...this.formatMessage('debug', message, meta));
    }
  }

  info(message: string, meta?: Record<string, unknown>): void {
    if (this.shouldLog('info')) {
      // eslint-disable-next-line no-console
      console.info(...this.formatMessage('info', message, meta));
    }
  }

  warn(message: string, meta?: Record<string, unknown>): void {
    if (this.shouldLog('warn')) {
      // eslint-disable-next-line no-console
      // eslint-disable-next-line no-console
      console.warn(...this.formatMessage('warn', message, meta));
    }
  }

  error(message: string, error?: Error | unknown, meta?: Record<string, unknown>): void {
    if (this.shouldLog('error')) {
      const errorMeta =
        error instanceof Error
          ? { error: error.message, stack: error.stack, ...meta }
          : error !== undefined
            ? { error, ...meta }
            : meta;

      // eslint-disable-next-line no-console
      // eslint-disable-next-line no-console
      console.error(...this.formatMessage('error', message, errorMeta));
    }
  }

  /**
   * 创建带前缀的子 logger
   */
  child(prefix: string): Logger {
    return new Logger({
      ...this.config,
      prefix: this.config.prefix != null ? `${this.config.prefix}:${prefix}` : prefix,
    });
  }

  /**
   * 临时启用/禁用日志
   */
  setEnabled(isEnabled: boolean): void {
    this.config.isEnabled = isEnabled;
  }

  /**
   * 设置日志级别
   */
  setLevel(level: LogLevel): void {
    this.config.level = level;
  }
}

// 默认 logger 实例
export const logger = new Logger();

// 创建特定模块的 logger
export const createLogger = (prefix: string): Logger => logger.child(prefix);

// 导出类型
export type { LogLevel, LoggerConfig };
export { Logger };
