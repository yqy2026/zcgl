/**
 * 统一配置管理系统
 * 整合所有配置文件，提供统一的配置管理体验
 */

import { LogLevel } from "../types/common";

// 环境枚举
export enum Environment {
  DEVELOPMENT = "development",
  TESTING = "testing",
  STAGING = "staging",
  PRODUCTION = "production",
}

// API配置接口
export interface APIConfig {
  baseURL: string;
  timeout: number;
  retryCount: number;
  retryDelay: number;
  version: string;
}

// 认证配置接口
export interface AuthConfig {
  tokenKey: string;
  refreshTokenKey: string;
  userKey: string;
  tokenRefreshThreshold: number; // 分钟
  autoRefresh: boolean;
}

// 文件上传配置接口
export interface FileUploadConfig {
  maxFileSize: number; // 字节
  allowedTypes: string[];
  uploadURL: string;
  chunkSize: number; // 分片上传大小
  maxConcurrentUploads: number;
}

// 缓存配置接口
export interface CacheConfig {
  enabled: boolean;
  defaultTTL: number; // 秒
  maxSize: number; // MB
  storage: "localStorage" | "sessionStorage" | "memory";
}

// 日志配置接口
export interface LoggingConfig {
  level: LogLevel;
  maxLogSize: number; // 单个日志文件最大大小（字节）
  maxFiles: number; // 最多保留的日志文件数量
  enableConsole: boolean;
  enableFile: boolean;
  filePath?: string;
  dateFormat: string;
}

// 主题配置接口
export interface ThemeConfig {
  mode: "light" | "dark" | "auto";
  primaryColor: string;
  compactMode: boolean;
  animationEnabled: boolean;
}

// 监控配置接口
export interface MonitoringConfig {
  enabled: boolean;
  performanceMonitoring: boolean;
  errorTracking: boolean;
  userAnalytics: boolean;
  sampleRate: number; // 0-1
}

// 功能开关配置接口
export interface FeatureFlagsConfig {
  smartPreload: boolean;
  advancedAnalytics: boolean;
  betaFeatures: boolean;
  debugMode: boolean;
}

// 统一配置接口
export interface UnifiedConfig {
  // 基础配置
  environment: Environment;
  debug: boolean;
  version: string;

  // API配置
  api: APIConfig;

  // 认证配置
  auth: AuthConfig;

  // 文件上传配置
  fileUpload: FileUploadConfig;

  // 缓存配置
  cache: CacheConfig;

  // 日志配置
  logging: LoggingConfig;

  // 主题配置
  theme: ThemeConfig;

  // 监控配置
  monitoring: MonitoringConfig;

  // 功能开关
  features: FeatureFlagsConfig;
}

/**
 * 配置管理器类
 */
export class ConfigManager {
  private static instance: ConfigManager;
  private config: UnifiedConfig | null = null;
  private configListeners: Array<(config: UnifiedConfig) => void> = [];

  private constructor() {
    this.loadConfig();
  }

  static getInstance(): ConfigManager {
    if ((ConfigManager.instance === null || ConfigManager.instance === undefined)) {
      ConfigManager.instance = new ConfigManager();
    }
    return ConfigManager.instance;
  }

  /**
   * 加载配置
   */
  private loadConfig(): void {
    const environment = this.detectEnvironment();
    const baseConfig = this.getBaseConfig();
    const envConfig = this.getEnvironmentConfig(environment);

    this.config = {
      ...baseConfig,
      ...envConfig,
      environment,
      debug: environment === Environment.DEVELOPMENT,
      version: (baseConfig.version !== null && baseConfig.version !== undefined && baseConfig.version !== '') ? baseConfig.version : "1.0.0",
    } as UnifiedConfig;

    // 验证配置
    this.validateConfig();
  }

  /**
   * 获取配置
   */
  getConfig(): UnifiedConfig {
    if (!this.config) {
      throw new Error("Configuration not loaded");
    }
    return this.config;
  }

  /**
   * 更新配置
   */
  updateConfig(updates: Partial<UnifiedConfig>): void {
    if (!this.config) {
      throw new Error("Configuration not loaded");
    }

    this.config = { ...this.config, ...updates };
    this.validateConfig();
    this.notifyListeners();
  }

  /**
   * 监听配置变化
   */
  addConfigListener(listener: (config: UnifiedConfig) => void): () => void {
    this.configListeners.push(listener);

    // 返回取消监听的函数
    return () => {
      const index = this.configListeners.indexOf(listener);
      if (index > -1) {
        this.configListeners.splice(index, 1);
      }
    };
  }

  /**
   * 检测环境
   */
  private detectEnvironment(): Environment {
    const hostname = window.location.hostname;

    if (hostname === "localhost" || hostname === "127.0.0.1") {
      return Environment.DEVELOPMENT;
    }

    if (hostname.includes("staging") || hostname.includes("test")) {
      return Environment.STAGING;
    }

    if (hostname.includes("prod") || hostname.includes("app")) {
      return Environment.PRODUCTION;
    }

    return Environment.DEVELOPMENT;
  }

  /**
   * 获取基础配置
   */
  private getBaseConfig(): Partial<UnifiedConfig> {
    return {
      version: (process.env.REACT_APP_VERSION !== null && process.env.REACT_APP_VERSION !== undefined && process.env.REACT_APP_VERSION !== '') ? process.env.REACT_APP_VERSION : "1.0.0",

      api: {
        baseURL: this.getApiBaseURL(),
        timeout: 30000,
        retryCount: 3,
        retryDelay: 1000,
        version: "v1",
      },

      auth: {
        tokenKey: "access_token",
        refreshTokenKey: "refresh_token",
        userKey: "user_info",
        tokenRefreshThreshold: 5, // 5分钟
        autoRefresh: true,
      },

      fileUpload: {
        maxFileSize: 100 * 1024 * 1024, // 100MB
        allowedTypes: [
          "application/pdf",
          "application/vnd.ms-excel",
          "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
          "text/csv",
          "image/jpeg",
          "image/png",
        ],
        uploadURL: "/api/v1/upload",
        chunkSize: 1024 * 1024, // 1MB
        maxConcurrentUploads: 3,
      },

      cache: {
        enabled: true,
        defaultTTL: 3600, // 1小时
        maxSize: 50, // 50MB
        storage: "localStorage",
      },

      logging: {
        level: LogLevel.INFO,
        maxLogSize: 10 * 1024 * 1024, // 10MB
        maxFiles: 5,
        enableConsole: true,
        enableFile: false,
        dateFormat: "YYYY-MM-DD HH:mm:ss",
      },

      theme: {
        mode: "light",
        primaryColor: "#1890ff",
        compactMode: false,
        animationEnabled: true,
      },

      monitoring: {
        enabled: true,
        performanceMonitoring: true,
        errorTracking: true,
        userAnalytics: false,
        sampleRate: 0.1,
      },

      features: {
        smartPreload: true,
        advancedAnalytics: true,
        betaFeatures: false,
        debugMode: false,
      },
    };
  }

  /**
   * 获取环境特定配置
   */
  private getEnvironmentConfig(environment: Environment): Partial<UnifiedConfig> {
    switch (environment) {
      case Environment.DEVELOPMENT:
        return {
          api: {
            baseURL: "http://localhost:8002/api",
            timeout: 60000,
            retryCount: 1,
            retryDelay: 500,
            version: "v1",
          },
          logging: {
            level: LogLevel.DEBUG,
            maxLogSize: 50 * 1024 * 1024, // 50MB
            maxFiles: 10,
            enableConsole: true,
            enableFile: true,
            filePath: "/tmp/app-debug.log",
            dateFormat: "YYYY-MM-DD HH:mm:ss.SSS",
          },
          monitoring: {
            enabled: true,
            performanceMonitoring: true,
            errorTracking: true,
            userAnalytics: false,
            sampleRate: 1.0,
          },
          features: {
            smartPreload: true,
            advancedAnalytics: true,
            betaFeatures: true,
            debugMode: true,
          },
        };

      case Environment.TESTING:
        return {
          api: {
            baseURL: "http://test-api.example.com/api/v1",
            timeout: 30000,
            retryCount: 2,
            retryDelay: 1000,
            version: "v1",
          },
          logging: {
            level: LogLevel.WARN,
            maxLogSize: 20 * 1024 * 1024, // 20MB
            maxFiles: 3,
            enableConsole: false,
            enableFile: true,
            filePath: "/tmp/app-test.log",
            dateFormat: "YYYY-MM-DD HH:mm:ss",
          },
          monitoring: {
            enabled: false,
            performanceMonitoring: false,
            errorTracking: true,
            userAnalytics: false,
            sampleRate: 0,
          },
          features: {
            smartPreload: false,
            advancedAnalytics: false,
            betaFeatures: false,
            debugMode: false,
          },
        };

      case Environment.STAGING:
        return {
          api: {
            baseURL: "https://staging-api.example.com/api/v1",
            timeout: 30000,
            retryCount: 3,
            retryDelay: 1000,
            version: "v1",
          },
          logging: {
            level: LogLevel.INFO,
            maxLogSize: 5 * 1024 * 1024, // 5MB
            maxFiles: 2,
            enableConsole: false,
            enableFile: true,
            filePath: "/var/log/app-staging.log",
            dateFormat: "YYYY-MM-DD HH:mm:ss",
          },
          monitoring: {
            enabled: true,
            performanceMonitoring: true,
            errorTracking: true,
            userAnalytics: true,
            sampleRate: 0.5,
          },
          features: {
            smartPreload: true,
            advancedAnalytics: true,
            betaFeatures: true,
            debugMode: false,
          },
        };

      case Environment.PRODUCTION:
        return {
          api: {
            baseURL: "https://api.example.com/api/v1",
            timeout: 30000,
            retryCount: 3,
            retryDelay: 1000,
            version: "v1",
          },
          logging: {
            level: LogLevel.ERROR,
            maxLogSize: 3 * 1024 * 1024, // 3MB
            maxFiles: 1,
            enableConsole: false,
            enableFile: true,
            filePath: "/var/log/app-production.log",
            dateFormat: "YYYY-MM-DD HH:mm:ss",
          },
          monitoring: {
            enabled: true,
            performanceMonitoring: true,
            errorTracking: true,
            userAnalytics: true,
            sampleRate: 0.1,
          },
          features: {
            smartPreload: true,
            advancedAnalytics: true,
            betaFeatures: false,
            debugMode: false,
          },
        };

      default:
        return {};
    }
  }

  /**
   * 获取API基础URL
   */
  private getApiBaseURL(): string {
    // 优先使用环境变量
    const envApiURL = process.env.REACT_APP_API_URL;
    if (envApiURL !== null && envApiURL !== undefined && envApiURL !== '') {
      return envApiURL;
    }

    // 根据当前域名推断API URL
    const currentHost = window.location.hostname;

    if (currentHost === "localhost" || currentHost === "127.0.0.1") {
      return "http://localhost:8002/api";
    }

    // 生产环境使用相对路径
    return "/api";
  }

  /**
   * 验证配置
   */
  private validateConfig(): void {
    if (!this.config) {
      throw new Error("Configuration not loaded");
    }

    // 验证API配置
    if (!this.config.api.baseURL) {
      throw new Error("API baseURL is required");
    }

    // 验证文件上传配置
    if (this.config.fileUpload.maxFileSize <= 0) {
      throw new Error("File upload max size must be greater than 0");
    }

    // 验证缓存配置
    if (this.config.cache.maxSize <= 0) {
      throw new Error("Cache max size must be greater than 0");
    }

    // 验证监控配置
    if (this.config.monitoring.sampleRate < 0 || this.config.monitoring.sampleRate > 1) {
      throw new Error("Monitoring sample rate must be between 0 and 1");
    }
  }

  /**
   * 通知配置监听器
   */
  private notifyListeners(): void {
    if (this.config) {
      this.configListeners.forEach((listener) => listener(this.config!));
    }
  }

  /**
   * 检查功能是否启用
   */
  isFeatureEnabled(feature: keyof FeatureFlagsConfig): boolean {
    return this.getConfig().features[feature];
  }

  /**
   * 检查是否为开发环境
   */
  isDevelopment(): boolean {
    return this.getConfig().environment === Environment.DEVELOPMENT;
  }

  /**
   * 检查是否为生产环境
   */
  isProduction(): boolean {
    return this.getConfig().environment === Environment.PRODUCTION;
  }

  /**
   * 检查调试模式
   */
  isDebugMode(): boolean {
    return this.getConfig().debug || this.getConfig().features.debugMode;
  }
}

// 创建全局配置管理器实例
export const configManager = ConfigManager.getInstance();

// 便捷函数
export const getConfig = (): UnifiedConfig => configManager.getConfig();
export const updateConfig = (updates: Partial<UnifiedConfig>): void =>
  configManager.updateConfig(updates);
export const addConfigListener = (listener: (config: UnifiedConfig) => void): (() => void) =>
  configManager.addConfigListener(listener);
export const isFeatureEnabled = (feature: keyof FeatureFlagsConfig): boolean =>
  configManager.isFeatureEnabled(feature);
export const isDevelopment = (): boolean => configManager.isDevelopment();
export const isProduction = (): boolean => configManager.isProduction();
export const isDebugMode = (): boolean => configManager.isDebugMode();

export default configManager;
