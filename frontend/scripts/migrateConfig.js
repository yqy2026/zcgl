#!/usr/bin/env node

/**
 * 前端配置迁移工具
 * 将分散的配置文件迁移到统一配置管理系统
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

class ConfigMigrator {
  constructor() {
    this.projectRoot = path.resolve(__dirname, '../..');
    this.configDir = path.join(this.projectRoot, 'src', 'config');
    this.backupDir = path.join(this.projectRoot, 'config-backups');
    this.migrationLog = [];

    // 创建必要的目录
    this.ensureDirectoryExists(this.configDir);
    this.ensureDirectoryExists(this.backupDir);
  }

  /**
   * 执行配置迁移
   */
  async migrateAll() {
    console.log('🚀 开始前端配置迁移...');

    try {
      // 识别现有配置文件
      const configFiles = this.identifyConfigFiles();
      console.log(`📁 发现 ${configFiles.length} 个配置文件`);

      // 备份现有配置
      this.backupExistingConfigs(configFiles);

      // 分析配置文件
      const configAnalysis = this.analyzeConfigFiles(configFiles);

      // 生成新的统一配置
      this.generateUnifiedConfig(configAnalysis);

      // 更新导入语句
      this.updateImportStatements();

      // 验证新配置
      if (this.validateNewConfig()) {
        console.log('✅ 前端配置迁移成功！');
        this.printMigrationSummary();
        return true;
      } else {
        console.log('❌ 配置验证失败，正在回滚...');
        this.rollbackMigration();
        return false;
      }

    } catch (error) {
      console.error(`❌ 迁移过程中发生错误: ${error.message}`);
      this.rollbackMigration();
      return false;
    }
  }

  /**
   * 识别配置文件
   */
  identifyConfigFiles() {
    const configFiles = [];
    const configPatterns = [
      '**/config*.js',
      '**/config*.ts',
      '**/constants/**/*.js',
      '**/constants/**/*.ts',
      '**/.env*',
      '**/package.json'
    ];

    configPatterns.forEach(pattern => {
      try {
        const files = this.findFiles(pattern);
        configFiles.push(...files);
      } catch (error) {
        console.warn(`⚠️ 搜索模式 ${pattern} 时出错: ${error.message}`);
      }
    });

    // 去重并过滤
    return [...new Set(configFiles)].filter(file => {
      const relativePath = path.relative(this.projectRoot, file);
      return !relativePath.includes('node_modules') &&
             !relativePath.includes('dist') &&
             !relativePath.includes('.git');
    });
  }

  /**
   * 查找匹配模式的文件
   */
  findFiles(pattern) {
    const { execSync } = require('child_process');
    const result = execSync(`find "${this.projectRoot}" -name "${pattern.replace('**/', '')}" -type f`, {
      encoding: 'utf8'
    });
    return result.trim().split('\n').filter(Boolean).map(file => path.resolve(file));
  }

  /**
   * 备份现有配置
   */
  backupExistingConfigs(configFiles) {
    console.log('💾 备份现有配置文件...');

    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const backupDir = path.join(this.backupDir, `migration-${timestamp}`);
    this.ensureDirectoryExists(backupDir);

    configFiles.forEach(configFile => {
      try {
        const relativePath = path.relative(this.projectRoot, configFile);
        const backupPath = path.join(backupDir, relativePath);
        this.ensureDirectoryExists(path.dirname(backupPath));

        fs.copyFileSync(configFile, backupPath);
        this.migrationLog.push(`备份: ${relativePath}`);

      } catch (error) {
        console.warn(`⚠️ 备份失败 ${configFile}: ${error.message}`);
      }
    });
  }

  /**
   * 分析配置文件
   */
  analyzeConfigFiles(configFiles) {
    console.log('🔍 分析配置文件...');

    const analysis = {
      constants: {},
      configs: {},
      envVars: {},
      packageConfig: {}
    };

    configFiles.forEach(configFile => {
      try {
        const content = fs.readFileSync(configFile, 'utf8');
        const relativePath = path.relative(this.projectRoot, configFile);

        if (configFile.includes('constants')) {
          analysis.constants[relativePath] = this.parseConstantsFile(content);
        } else if (configFile.includes('config')) {
          analysis.configs[relativePath] = this.parseConfigFile(content);
        } else if (path.basename(configFile).startsWith('.env')) {
          analysis.envVars[relativePath] = this.parseEnvFile(content);
        } else if (path.basename(configFile) === 'package.json') {
          analysis.packageConfig[relativePath] = JSON.parse(content);
        }

        this.migrationLog.push(`分析: ${relativePath}`);

      } catch (error) {
        console.warn(`⚠️ 分析失败 ${configFile}: ${error.message}`);
      }
    });

    return analysis;
  }

  /**
   * 解析常量文件
   */
  parseConstantsFile(content) {
    const constants = {};

    // 匹配导出的常量
    const exportRegex = /export\s+(const|let|var)\s+(\w+)\s*=\s*([^;]+);?/g;
    let match;

    while ((match = exportRegex.exec(content)) !== null) {
      const [full, type, name, value] = match;
      try {
        constants[name] = this.parseValue(value.trim());
      } catch (error) {
        constants[name] = value.trim();
      }
    }

    return constants;
  }

  /**
   * 解析配置文件
   */
  parseConfigFile(content) {
    const config = {};

    // 匹配置对象
    const objectRegex = /(?:const|let|var)\s+(\w+)\s*=\s*({[\s\S]*?});?/g;
    let match;

    while ((match = objectRegex.exec(content)) !== null) {
      const [full, name, value] = match;
      try {
        config[name] = eval(`(${value})`);
      } catch (error) {
        config[name] = value;
      }
    }

    return config;
  }

  /**
   * 解析环境文件
   */
  parseEnvFile(content) {
    const envVars = {};

    content.split('\n').forEach(line => {
      line = line.trim();
      if (line && !line.startsWith('#') && line.includes('=')) {
        const [key, ...valueParts] = line.split('=');
        envVars[key.trim()] = valueParts.join('=').trim();
      }
    });

    return envVars;
  }

  /**
   * 解析值
   */
  parseValue(value) {
    value = value.trim();

    // 字符串
    if ((value.startsWith('"') && value.endsWith('"')) ||
        (value.startsWith("'") && value.endsWith("'"))) {
      return value.slice(1, -1);
    }

    // 数字
    if (!isNaN(value) && value !== '') {
      return Number(value);
    }

    // 布尔值
    if (value === 'true') return true;
    if (value === 'false') return false;

    // 数组
    if (value.startsWith('[') && value.endsWith(']')) {
      return eval(value);
    }

    // 对象
    if (value.startsWith('{') && value.endsWith('}')) {
      return eval(value);
    }

    return value;
  }

  /**
   * 生成统一配置
   */
  generateUnifiedConfig(analysis) {
    console.log('📝 生成统一配置文件...');

    // 生成配置类型定义
    this.generateConfigTypes(analysis);

    // 生成配置管理器
    this.generateConfigManager(analysis);

    // 生成环境配置
    this.generateEnvironmentConfig(analysis);

    // 生成默认配置
    this.generateDefaultConfig(analysis);
  }

  /**
   * 生成配置类型定义
   */
  generateConfigTypes(analysis) {
    const typesContent = `/**
 * 统一配置类型定义
 * 自动生成于 ${new Date().toISOString()}
 */

// 环境枚举
export enum Environment {
  DEVELOPMENT = 'development',
  TESTING = 'testing',
  STAGING = 'staging',
  PRODUCTION = 'production'
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
  tokenRefreshThreshold: number;
  autoRefresh: boolean;
}

// 文件上传配置接口
export interface FileUploadConfig {
  maxFileSize: number;
  allowedTypes: string[];
  uploadURL: string;
  chunkSize: number;
  maxConcurrentUploads: number;
}

// 缓存配置接口
export interface CacheConfig {
  enabled: boolean;
  defaultTTL: number;
  maxSize: number;
  storage: 'localStorage' | 'sessionStorage' | 'memory';
}

// 日志配置接口
export interface LoggingConfig {
  enabled: boolean;
  level: 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR';
  consoleEnabled: boolean;
  remoteEnabled: boolean;
  remoteURL?: string;
  maxLogSize: number;
}

// 主题配置接口
export interface ThemeConfig {
  mode: 'light' | 'dark' | 'auto';
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
  sampleRate: number;
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
  environment: Environment;
  debug: boolean;
  version: string;

  api: APIConfig;
  auth: AuthConfig;
  fileUpload: FileUploadConfig;
  cache: CacheConfig;
  logging: LoggingConfig;
  theme: ThemeConfig;
  monitoring: MonitoringConfig;
  features: FeatureFlagsConfig;
}

export default UnifiedConfig;
`;

    const typesFile = path.join(this.configDir, 'types.ts');
    fs.writeFileSync(typesFile, typesContent);
    this.migrationLog.push(`生成配置类型: ${path.relative(this.projectRoot, typesFile)}`);
  }

  /**
   * 生成配置管理器
   */
  generateConfigManager(analysis) {
    const managerContent = `/**
 * 统一配置管理器
 * 自动生成于 ${new Date().toISOString()}
 */

import { LogLevel } from '@/types/common';
import {
  Environment,
  UnifiedConfig,
  APIConfig,
  AuthConfig,
  FileUploadConfig,
  CacheConfig,
  LoggingConfig,
  ThemeConfig,
  MonitoringConfig,
  FeatureFlagsConfig
} from './types';

class ConfigManager {
  private static instance: ConfigManager;
  private config: UnifiedConfig | null = null;
  private configListeners: Array<(config: UnifiedConfig) => void> = [];

  private constructor() {
    this.loadConfig();
  }

  static getInstance(): ConfigManager {
    if (!ConfigManager.instance) {
      ConfigManager.instance = new ConfigManager();
    }
    return ConfigManager.instance;
  }

  private loadConfig(): void {
    const environment = this.detectEnvironment();
    const baseConfig = this.getBaseConfig();
    const envConfig = this.getEnvironmentConfig(environment);

    this.config = {
      ...baseConfig,
      ...envConfig,
      environment,
      debug: environment === Environment.DEVELOPMENT
    };

    this.validateConfig();
  }

  private detectEnvironment(): Environment {
    const hostname = window.location.hostname;

    if (hostname === 'localhost' || hostname === '127.0.0.1') {
      return Environment.DEVELOPMENT;
    }

    if (hostname.includes('staging') || hostname.includes('test')) {
      return Environment.STAGING;
    }

    if (hostname.includes('prod') || hostname.includes('app')) {
      return Environment.PRODUCTION;
    }

    return Environment.DEVELOPMENT;
  }

  private getBaseConfig(): Partial<UnifiedConfig> {
    return {
      version: process.env.REACT_APP_VERSION || '1.0.0',

      api: this.getAPIConfig(),
      auth: this.getAuthConfig(),
      fileUpload: this.getFileUploadConfig(),
      cache: this.getCacheConfig(),
      logging: this.getLoggingConfig(),
      theme: this.getThemeConfig(),
      monitoring: this.getMonitoringConfig(),
      features: this.getFeatureFlagsConfig()
    };
  }

  private getAPIConfig(): APIConfig {
    return {
      baseURL: this.getApiBaseURL(),
      timeout: 30000,
      retryCount: 3,
      retryDelay: 1000,
      version: 'v1'
    };
  }

  private getAuthConfig(): AuthConfig {
    return {
      tokenKey: 'access_token',
      refreshTokenKey: 'refresh_token',
      userKey: 'user_info',
      tokenRefreshThreshold: 5,
      autoRefresh: true
    };
  }

  private getFileUploadConfig(): FileUploadConfig {
    return {
      maxFileSize: 100 * 1024 * 1024, // 100MB
      allowedTypes: [
        'application/pdf',
        'application/vnd.ms-excel',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'text/csv',
        'image/jpeg',
        'image/png'
      ],
      uploadURL: '/api/v1/upload',
      chunkSize: 1024 * 1024,
      maxConcurrentUploads: 3
    };
  }

  private getCacheConfig(): CacheConfig {
    return {
      enabled: true,
      defaultTTL: 3600,
      maxSize: 50,
      storage: 'localStorage'
    };
  }

  private getLoggingConfig(): LoggingConfig {
    return {
      enabled: true,
      level: LogLevel.INFO,
      consoleEnabled: true,
      remoteEnabled: false,
      maxLogSize: 1000
    };
  }

  private getThemeConfig(): ThemeConfig {
    return {
      mode: 'light',
      primaryColor: '#1890ff',
      compactMode: false,
      animationEnabled: true
    };
  }

  private getMonitoringConfig(): MonitoringConfig {
    return {
      enabled: true,
      performanceMonitoring: true,
      errorTracking: true,
      userAnalytics: false,
      sampleRate: 0.1
    };
  }

  private getFeatureFlagsConfig(): FeatureFlagsConfig {
    return {
      smartPreload: true,
      advancedAnalytics: true,
      betaFeatures: false,
      debugMode: false
    };
  }

  private getEnvironmentConfig(environment: Environment): Partial<UnifiedConfig> {
    switch (environment) {
      case Environment.DEVELOPMENT:
        return {
          api: {
            baseURL: 'http://localhost:8002/api/v1',
            timeout: 60000,
            retryCount: 1,
            retryDelay: 500,
            version: 'v1'
          },
          logging: {
            enabled: true,
            level: LogLevel.DEBUG,
            consoleEnabled: true,
            remoteEnabled: false
          },
          monitoring: {
            enabled: true,
            performanceMonitoring: true,
            errorTracking: true,
            userAnalytics: false,
            sampleRate: 1.0
          },
          features: {
            smartPreload: true,
            advancedAnalytics: true,
            betaFeatures: true,
            debugMode: true
          }
        };

      case Environment.PRODUCTION:
        return {
          api: {
            baseURL: '/api/v1',
            timeout: 30000,
            retryCount: 3,
            retryDelay: 1000,
            version: 'v1'
          },
          logging: {
            enabled: true,
            level: LogLevel.ERROR,
            consoleEnabled: false,
            remoteEnabled: true
          },
          monitoring: {
            enabled: true,
            performanceMonitoring: true,
            errorTracking: true,
            userAnalytics: true,
            sampleRate: 0.1
          },
          features: {
            smartPreload: true,
            advancedAnalytics: true,
            betaFeatures: false,
            debugMode: false
          }
        };

      default:
        return {};
    }
  }

  private getApiBaseURL(): string {
    const envApiURL = process.env.REACT_APP_API_URL;
    if (envApiURL) {
      return envApiURL;
    }

    const currentHost = window.location.hostname;

    if (currentHost === 'localhost' || currentHost === '127.0.0.1') {
      return 'http://localhost:8002/api/v1';
    }

    return '/api/v1';
  }

  private validateConfig(): void {
    if (!this.config) {
      throw new Error('Configuration not loaded');
    }

    if (!this.config.api.baseURL) {
      throw new Error('API baseURL is required');
    }

    if (this.config.fileUpload.maxFileSize <= 0) {
      throw new Error('File upload max size must be greater than 0');
    }

    if (this.config.monitoring.sampleRate < 0 || this.config.monitoring.sampleRate > 1) {
      throw new Error('Monitoring sample rate must be between 0 and 1');
    }
  }

  getConfig(): UnifiedConfig {
    if (!this.config) {
      throw new Error('Configuration not loaded');
    }
    return this.config;
  }

  updateConfig(updates: Partial<UnifiedConfig>): void {
    if (!this.config) {
      throw new Error('Configuration not loaded');
    }

    this.config = { ...this.config, ...updates };
    this.validateConfig();
    this.notifyListeners();
  }

  addConfigListener(listener: (config: UnifiedConfig) => void): () => void {
    this.configListeners.push(listener);

    return () => {
      const index = this.configListeners.indexOf(listener);
      if (index > -1) {
        this.configListeners.splice(index, 1);
      }
    };
  }

  private notifyListeners(): void {
    if (this.config) {
      this.configListeners.forEach(listener => listener(this.config!));
    }
  }

  isFeatureEnabled(feature: keyof FeatureFlagsConfig): boolean {
    return this.getConfig().features[feature];
  }

  isDevelopment(): boolean {
    return this.getConfig().environment === Environment.DEVELOPMENT;
  }

  isProduction(): boolean {
    return this.getConfig().environment === Environment.PRODUCTION;
  }

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
`;

    const managerFile = path.join(this.configDir, 'index.ts');
    fs.writeFileSync(managerFile, managerContent);
    this.migrationLog.push(`生成配置管理器: ${path.relative(this.projectRoot, managerFile)}`);
  }

  /**
   * 生成环境配置
   */
  generateEnvironmentConfig(analysis) {
    // 这里可以根据需要生成特定环境的配置文件
    // 目前主要依赖环境变量和运行时检测
  }

  /**
   * 生成默认配置
   */
  generateDefaultConfig(analysis) {
    // 这里可以生成默认配置文件
  }

  /**
   * 更新导入语句
   */
  updateImportStatements() {
    console.log('🔄 更新导入语句...');

    // 这里可以添加自动更新导入语句的逻辑
    // 由于涉及复杂的AST操作，建议手动更新或使用专门的工具
  }

  /**
   * 验证新配置
   */
  validateNewConfig() {
    console.log('✅ 验证新配置...');

    try {
      // 尝试导入配置管理器
      const configManagerPath = path.join(this.configDir, 'index.ts');
      const typesPath = path.join(this.configDir, 'types.ts');

      if (!fs.existsSync(configManagerPath)) {
        throw new Error('配置管理器文件不存在');
      }

      if (!fs.existsSync(typesPath)) {
        throw new Error('配置类型文件不存在');
      }

      console.log('✅ 配置验证通过');
      return true;

    } catch (error) {
      console.error(`❌ 配置验证失败: ${error.message}`);
      return false;
    }
  }

  /**
   * 回滚迁移
   */
  rollbackMigration() {
    console.log('🔄 回滚迁移...');

    try {
      // 删除生成的新配置文件
      const newFiles = [
        path.join(this.configDir, 'types.ts'),
        path.join(this.configDir, 'index.ts')
      ];

      newFiles.forEach(file => {
        if (fs.existsSync(file)) {
          fs.unlinkSync(file);
        }
      });

      console.log('✅ 迁移已回滚');

    } catch (error) {
      console.error(`❌ 回滚失败: ${error.message}`);
    }
  }

  /**
   * 打印迁移摘要
   */
  printMigrationSummary() {
    console.log('\n' + '='*60);
    console.log('🎉 前端配置迁移完成摘要');
    console.log('='*60);
    console.log(`📋 操作日志: ${this.migrationLog.length} 个操作`);
    console.log('\n📝 生成的文件:');
    console.log('  - src/config/types.ts (配置类型定义)');
    console.log('  - src/config/index.ts (配置管理器)');
    console.log('\n🔧 后续步骤:');
    console.log('  1. 检查生成的配置文件');
    console.log('  2. 更新组件中的配置导入');
    console.log('  3. 测试应用启动');
    console.log('  4. 确认无问题后可删除旧配置文件');
    console.log('\n📖 使用示例:');
    console.log('  import { getConfig } from "@/config"');
    console.log('  const config = getConfig();');
    console.log('  console.log(config.api.baseURL);');
    console.log('='*60);
  }

  /**
   * 确保目录存在
   */
  ensureDirectoryExists(dir) {
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }
  }
}

/**
 * 主函数
 */
async function main() {
  const migrator = new ConfigMigrator();

  console.log('🚀 地产资产管理系统 - 前端配置迁移工具');
  console.log('⚠️ 此工具将迁移现有配置到统一配置管理系统');
  console.log();

  // 确认执行
  const readline = require('readline');
  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout
  });

  rl.question('是否继续执行配置迁移? (y/N): ', (answer) => {
    rl.close();

    if (answer.toLowerCase() !== 'y' && answer.toLowerCase() !== 'yes') {
      console.log('❌ 取消配置迁移');
      return;
    }

    // 执行迁移
    migrator.migrateAll().then(success => {
      if (success) {
        console.log('\n🎉 前端配置迁移成功完成!');
        process.exit(0);
      } else {
        console.log('\n❌ 前端配置迁移失败!');
        process.exit(1);
      }
    });
  });
}

// 如果直接运行此脚本
if (require.main === module) {
  main();
}

module.exports = ConfigMigrator;
