/**
 * LLM Prompt 管理系统类型定义
 */

/**
 * Prompt 状态枚举
 */
export enum PromptStatus {
  DRAFT = 'DRAFT', // 草稿
  ACTIVE = 'ACTIVE', // 活跃
  ARCHIVED = 'ARCHIVED', // 已归档
}

/**
 * 文档类型枚举
 */
export enum DocType {
  CONTRACT = 'CONTRACT', // 租赁合同
  PROPERTY_CERT = 'PROPERTY_CERT', // 产权证
}

/**
 * LLM 提供商枚举
 */
export enum LLMProvider {
  QWEN = 'qwen', // 阿里通义千问
  HUNYUAN = 'hunyuan', // 腾讯混元
  DEEPSEEK = 'deepseek', // DeepSeek
  GLM = 'glm', // 智谱 GLM
}

export type FewShotExamples = Record<string, unknown>;

/**
 * Prompt 模板
 */
export interface PromptTemplate {
  id: string;
  name: string;
  doc_type: DocType;
  provider: LLMProvider;
  description?: string;
  system_prompt: string;
  user_prompt_template: string;
  few_shot_examples?: FewShotExamples;
  version: string;
  status: PromptStatus;
  tags?: string[];
  avg_accuracy: number;
  avg_confidence: number;
  total_usage: number;
  current_version_id?: string;
  parent_id?: string;
  created_at: string;
  updated_at: string;
  created_by?: string;
}

/**
 * 创建 Prompt 请求
 */
export interface PromptTemplateCreate {
  name: string;
  doc_type: DocType;
  provider: LLMProvider;
  description?: string;
  system_prompt: string;
  user_prompt_template: string;
  few_shot_examples?: FewShotExamples;
  tags?: string[];
}

/**
 * 更新 Prompt 请求
 */
export interface PromptTemplateUpdate {
  name?: string;
  description?: string;
  system_prompt?: string;
  user_prompt_template?: string;
  few_shot_examples?: FewShotExamples;
  tags?: string[];
  change_description?: string;
}

/**
 * Prompt 版本
 */
export interface PromptVersion {
  id: string;
  template_id: string;
  version: string;
  system_prompt: string;
  user_prompt_template: string;
  few_shot_examples?: FewShotExamples;
  change_description?: string;
  change_type?: string;
  auto_generated?: boolean;
  accuracy?: number;
  confidence?: number;
  usage_count: number;
  created_at: string;
  created_by?: string;
}

/**
 * Prompt 列表响应
 */
export interface PromptTemplateListResponse {
  items: PromptTemplate[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

/**
 * Prompt 激活请求
 */
export interface PromptActivationRequest {
  template_id: string;
}

/**
 * Prompt 回滚请求
 */
export interface PromptRollbackRequest {
  version_id: string;
}

/**
 * 提取反馈
 */
export interface ExtractionFeedback {
  id: string;
  template_id: string;
  version_id?: string;
  doc_type: DocType;
  file_path?: string;
  session_id?: string;
  field_name: string;
  original_value?: string;
  corrected_value?: string;
  confidence_before?: number;
  user_action?: string;
  created_at: string;
}

/**
 * 提取反馈创建请求
 */
export interface ExtractionFeedbackCreate {
  template_id: string;
  field_name: string;
  original_value?: string;
  corrected_value?: string;
  confidence_before?: number;
  doc_type: DocType;
  file_path?: string;
  session_id?: string;
  user_action?: string;
}

/**
 * Prompt 统计概览
 */
export interface PromptStatistics {
  total_prompts: number;
  status_distribution: Array<{
    status: PromptStatus;
    count: number;
  }>;
  doc_type_distribution: Array<{
    doc_type: DocType;
    count: number;
  }>;
  provider_distribution: Array<{
    provider: LLMProvider;
    count: number;
  }>;
  overall_avg_accuracy: number;
  overall_avg_confidence: number;
}

/**
 * Prompt 查询参数
 */
export interface PromptQueryParams {
  page?: number;
  pageSize?: number;
  page_size?: number;
  doc_type?: DocType;
  status?: PromptStatus;
  provider?: LLMProvider;
}

/**
 * 优化结果
 */
export interface OptimizationResult {
  success: boolean;
  template_id?: string;
  template_name?: string;
  old_version?: string;
  new_version?: string;
  rules_added?: number;
  feedback_count?: number;
  rules?: string[];
  reason?: string;
}
