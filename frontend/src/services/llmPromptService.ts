/**
 * LLM Prompt 管理服务
 * 处理 Prompt 模板的 CRUD、版本管理、激活、回滚等 API 调用
 */

import { apiClient } from '@/api/client';
import { createLogger } from '@/utils/logger';
import type {
  PromptTemplate,
  PromptTemplateCreate,
  PromptTemplateUpdate,
  PromptTemplateListResponse,
  PromptVersion,
  PromptRollbackRequest,
  ExtractionFeedbackCreate,
  PromptStatistics,
  PromptQueryParams,
} from '@/types/llmPrompt';
import { DocType, PromptStatus, LLMProvider } from '@/types/llmPrompt';

const logger = createLogger('LLMPromptService');

const API_BASE = '/llm-prompts';

/**
 * 辅助函数：从ExtractResult中提取数据，如果数据为空则抛出错误
 */
function extractData<T>(result: { data?: T }, errorMessage: string): T {
  if (result.data == null) {
    throw new Error(errorMessage);
  }
  return result.data;
}

/**
 * LLM Prompt 管理服务
 */
export class LLMPromptService {
  /**
   * 获取 Prompt 列表
   */
  async getPrompts(params?: PromptQueryParams): Promise<PromptTemplateListResponse> {
    try {
      const { pageSize, page_size, ...rest } = params ?? {};
      const response = await apiClient.get<PromptTemplateListResponse>(API_BASE, {
        params: { ...rest, page: params?.page, page_size: page_size ?? pageSize },
      });
      return extractData(response, '获取 Prompt 列表失败: 响应数据为空');
    } catch (error) {
      logger.error('获取 Prompt 列表失败', error);
      throw error;
    }
  }

  /**
   * 获取单个 Prompt 详情
   */
  async getPrompt(id: string): Promise<PromptTemplate> {
    try {
      const response = await apiClient.get<PromptTemplate>(`${API_BASE}/${id}`);
      return extractData(response, `获取 Prompt 详情失败: ${id}`);
    } catch (error) {
      logger.error(`获取 Prompt 详情失败: ${id}`, error);
      throw error;
    }
  }

  /**
   * 创建新 Prompt
   */
  async createPrompt(data: PromptTemplateCreate): Promise<PromptTemplate> {
    try {
      const response = await apiClient.post<PromptTemplate>(API_BASE, data);
      const result = extractData(response, '创建 Prompt 失败: 响应数据为空');
      logger.info(`创建 Prompt 成功: ${result.name}`);
      return result;
    } catch (error) {
      logger.error('创建 Prompt 失败', error);
      throw error;
    }
  }

  /**
   * 更新 Prompt (自动创建新版本)
   */
  async updatePrompt(id: string, data: PromptTemplateUpdate): Promise<PromptTemplate> {
    try {
      const response = await apiClient.put<PromptTemplate>(`${API_BASE}/${id}`, data);
      const result = extractData(response, `更新 Prompt 失败: ${id}`);
      logger.info(`更新 Prompt 成功: ${result.name} -> v${result.version}`);
      return result;
    } catch (error) {
      logger.error(`更新 Prompt 失败: ${id}`, error);
      throw error;
    }
  }

  /**
   * 激活 Prompt
   */
  async activatePrompt(id: string): Promise<PromptTemplate> {
    try {
      const response = await apiClient.post<PromptTemplate>(
        `${API_BASE}/${id}/activate`,
        {}
      );
      const result = extractData(response, `激活 Prompt 失败: ${id}`);
      logger.info(`激活 Prompt 成功: ${result.name}`);
      return result;
    } catch (error) {
      logger.error(`激活 Prompt 失败: ${id}`, error);
      throw error;
    }
  }

  /**
   * 回滚 Prompt 到指定版本
   */
  async rollbackPrompt(id: string, request: PromptRollbackRequest): Promise<PromptTemplate> {
    try {
      const response = await apiClient.post<PromptTemplate>(
        `${API_BASE}/${id}/rollback`,
        request
      );
      const result = extractData(response, `回滚 Prompt 失败: ${id}`);
      logger.info(`回滚 Prompt 成功: ${result.name} -> v${result.version}`);
      return result;
    } catch (error) {
      logger.error(`回滚 Prompt 失败: ${id}`, error);
      throw error;
    }
  }

  /**
   * 获取 Prompt 版本历史
   */
  async getPromptVersions(id: string): Promise<PromptVersion[]> {
    try {
      const response = await apiClient.get<PromptVersion[]>(`${API_BASE}/${id}/versions`);
      return extractData(response, `获取 Prompt 版本历史失败: ${id}`);
    } catch (error) {
      logger.error(`获取 Prompt 版本历史失败: ${id}`, error);
      throw error;
    }
  }

  /**
   * 获取统计概览
   */
  async getStatistics(): Promise<PromptStatistics> {
    try {
      const response = await apiClient.get<PromptStatistics>(
        `${API_BASE}/statistics/overview`
      );
      return extractData(response, '获取统计概览失败: 响应数据为空');
    } catch (error) {
      logger.error('获取统计概览失败', error);
      throw error;
    }
  }

  /**
   * 提交用户反馈
   */
  async submitFeedback(
    data: ExtractionFeedbackCreate
  ): Promise<{ success: boolean; feedback_id: string }> {
    try {
      const response = await apiClient.post<{ success: boolean; feedback_id: string }>(
        `${API_BASE}/feedback`,
        data
      );
      const result = extractData(response, '提交反馈失败: 响应数据为空');
      logger.info(`提交反馈成功: ${result.feedback_id}`);
      return result;
    } catch (error) {
      logger.error('提交反馈失败', error);
      throw error;
    }
  }

  /**
   * 获取活跃的 Prompt (按文档类型和提供商)
   */
  async getActivePrompt(
    docType: DocType,
    provider?: LLMProvider
  ): Promise<PromptTemplate | null> {
    try {
      const params: PromptQueryParams = {
        doc_type: docType,
        status: PromptStatus.ACTIVE,
      };

      if (provider != null && provider.trim() !== '') {
        params.provider = provider;
      }

      const response = await this.getPrompts({
        ...params,
        page_size: 1,
      });

      return response.items[0] ?? null;
    } catch (error) {
      logger.error(`获取活跃 Prompt 失败: ${docType}, ${provider}`, error);
      return null;
    }
  }

  /**
   * 测试 Prompt (可选功能)
   * 在实际应用中用于测试 Prompt 效果
   */
  async testPrompt(
    id: string,
    testFile?: File
  ): Promise<{ success: boolean; result?: unknown; error?: string }> {
    try {
      if (testFile == null) {
        throw new Error('请提供测试文件');
      }

      const formData = new FormData();
      formData.append('file', testFile);

      const response = await apiClient.post<{ success: boolean; result: unknown }>(
        `${API_BASE}/${id}/test`,
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        }
      );
      const result = extractData(response, `测试 Prompt 失败: ${id}`);

      return {
        success: result.success,
        result: result.result,
      };
    } catch (error) {
      logger.error(`测试 Prompt 失败: ${id}`, error);
      return {
        success: false,
        error: error instanceof Error ? error.message : '未知错误',
      };
    }
  }
}

// 导出单例实例
export const llmPromptService = new LLMPromptService();

// 导出便捷方法
export const getPrompts = (params?: PromptQueryParams) => llmPromptService.getPrompts(params);

export const getPrompt = (id: string) => llmPromptService.getPrompt(id);

export const createPrompt = (data: PromptTemplateCreate) => llmPromptService.createPrompt(data);

export const updatePrompt = (id: string, data: PromptTemplateUpdate) =>
  llmPromptService.updatePrompt(id, data);

export const activatePrompt = (id: string) => llmPromptService.activatePrompt(id);

export const rollbackPrompt = (id: string, request: PromptRollbackRequest) =>
  llmPromptService.rollbackPrompt(id, request);

export const getPromptVersions = (id: string) => llmPromptService.getPromptVersions(id);

export const getStatistics = () => llmPromptService.getStatistics();

export const submitFeedback = (data: ExtractionFeedbackCreate) =>
  llmPromptService.submitFeedback(data);

export const getActivePrompt = (docType: DocType, provider?: LLMProvider) =>
  llmPromptService.getActivePrompt(docType, provider);

export const testPrompt = (id: string, testFile?: File) =>
  llmPromptService.testPrompt(id, testFile);
