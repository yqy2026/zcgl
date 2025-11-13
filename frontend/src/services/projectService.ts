/**
 * 项目相关服务 - 统一响应处理版本
 *
 * @description 项目管理核心服务，提供项目CRUD、搜索、统计等完整功能
 * @author Claude Code
 * @updated 2025-11-10
 */

import { enhancedApiClient } from './enhancedApiClient';
import { ApiErrorHandler } from '../utils/responseExtractor';
import { API_CONFIG, API_ENDPOINTS } from '@/constants/api';
import type {
  Project,
  ProjectCreate,
  ProjectUpdate,
  ProjectListResponse,
  ProjectSearchRequest,
  ProjectStatisticsResponse,
  ProjectDeleteResponse,
  ProjectSearchParams,
  ProjectDropdownOption
} from '@/types/project';

export class ProjectService {
  private baseUrl = API_ENDPOINTS.PROJECT.LIST.replace(/^\//, '');

  // ==================== 基础CRUD操作 ====================

  /**
   * 搜索项目
   */
  async searchProjects(searchParams: ProjectSearchRequest): Promise<ProjectListResponse> {
    try {
      const result = await enhancedApiClient.post<ProjectListResponse>(
        'search',
        searchParams,
        {
          retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
          smartExtract: true
        }
      );

      if (!result.success) {
        throw new Error(`搜索项目失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  /**
   * 获取项目详情
   */
  async getProject(id: string): Promise<Project> {
    try {
      const result = await enhancedApiClient.get<Project>(
        `${this.baseUrl}/${id}`,
        {
          cache: true,
          retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
          smartExtract: true
        }
      );

      if (!result.success) {
        throw new Error(`获取项目详情失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  /**
   * 获取项目列表
   */
  async getProjects(params?: ProjectSearchParams): Promise<ProjectListResponse> {
    try {
      // 确保提供必需的分页参数
      const requestParams = {
        page: params?.page || 1,
        size: params?.size || 10,
        keyword: params?.keyword,
        is_active: params?.is_active,
        ownership_id: params?.ownership_id,
      };

      const result = await enhancedApiClient.get<ProjectListResponse>(
        this.baseUrl,
        {
          params: requestParams,
          cache: true,
          retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
          smartExtract: true
        }
      );

      if (!result.success) {
        throw new Error(`获取项目列表失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  /**
   * 创建项目
   */
  async createProject(data: ProjectCreate): Promise<Project> {
    try {
      const result = await enhancedApiClient.post<Project>(
        this.baseUrl,
        data,
        {
          retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
          smartExtract: true
        }
      );

      if (!result.success) {
        throw new Error(`创建项目失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  /**
   * 更新项目
   */
  async updateProject(id: string, data: ProjectUpdate): Promise<Project> {
    try {
      const result = await enhancedApiClient.put<Project>(
        `${this.baseUrl}/${id}`,
        data,
        {
          retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
          smartExtract: true
        }
      );

      if (!result.success) {
        throw new Error(`更新项目失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  /**
   * 删除项目
   */
  async deleteProject(id: string): Promise<ProjectDeleteResponse> {
    try {
      const result = await enhancedApiClient.delete<ProjectDeleteResponse>(
        `${this.baseUrl}/${id}`,
        {
          retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
          smartExtract: true
        }
      );

      if (!result.success) {
        throw new Error(`删除项目失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  // ==================== 项目操作 ====================

  /**
   * 切换项目状态
   */
  async toggleProjectStatus(id: string): Promise<Project> {
    try {
      const result = await enhancedApiClient.post<Project>(
        `${this.baseUrl}/${id}/toggle-status`,
        {},
        {
          retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
          smartExtract: true
        }
      );

      if (!result.success) {
        throw new Error(`切换项目状态失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  /**
   * 获取项目统计信息
   */
  async getProjectStatistics(): Promise<ProjectStatisticsResponse> {
    try {
      const result = await enhancedApiClient.get<ProjectStatisticsResponse>(
        'statistics/summary',
        {
          cache: true,
          retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
          smartExtract: true
        }
      );

      if (!result.success) {
        throw new Error(`获取项目统计失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  /**
   * 获取项目选项列表
   */
  async getProjectOptions(isActive: boolean = true): Promise<ProjectDropdownOption[]> {
    try {
      const result = await enhancedApiClient.get<ProjectDropdownOption[]>(
        `${this.baseUrl}/dropdown-options?is_active=${isActive}`,
        {
          cache: true,
          retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
          smartExtract: true
        }
      );

      if (!result.success) {
        throw new Error(`获取项目选项失败: ${result.error}`);
      }

      // 确保返回数组格式
      const data = result.data!;
      return Array.isArray(data) ? data : (data as any)?.data || [];
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  // ==================== 批量操作 ====================

  /**
   * 批量获取项目信息
   */
  async getProjectsByIds(ids: string[]): Promise<Project[]> {
    try {
      const promises = ids.map(id => this.getProject(id));
      const projects = await Promise.all(promises);
      return projects.filter(project => project && project.is_active);
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      console.error('批量获取项目信息失败:', enhancedError.message);
      return [];
    }
  }

  /**
   * 批量删除项目
   */
  async batchDeleteProjects(ids: string[]): Promise<{ deleted: number; errors: string[] }> {
    const errors: string[] = [];
    let deleted = 0;

    for (const id of ids) {
      try {
        await this.deleteProject(id);
        deleted++;
      } catch (error) {
        const enhancedError = ApiErrorHandler.handleError(error);
        errors.push(`项目 ${id}: ${enhancedError.message}`);
      }
    }

    return { deleted, errors };
  }

  // ==================== 验证功能 ====================

  /**
   * 验证项目编码唯一性
   */
  async validateProjectCode(code: string, excludeId?: string): Promise<boolean> {
    try {
      const result = await this.getProjects({ keyword: code });
      return !result.items.some(item =>
        item.code === code && item.id !== excludeId
      );
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      console.error('验证项目编码失败:', enhancedError.message);
      return false;
    }
  }

  /**
   * 验证项目名称唯一性
   */
  async validateProjectName(name: string, excludeId?: string): Promise<boolean> {
    try {
      const result = await this.getProjects({ keyword: name });
      return !result.items.some(item =>
        item.name === name && item.id !== excludeId
      );
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      console.error('验证项目名称失败:', enhancedError.message);
      return false;
    }
  }

  // ==================== 查询功能 ====================

  /**
   * 根据条件获取项目数量
   */
  async getProjectCount(params?: ProjectSearchParams): Promise<number> {
    try {
      const result = await this.getProjects({ ...params, size: 1 });
      return result.total;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      console.error('获取项目数量失败:', enhancedError.message);
      return 0;
    }
  }

  /**
   * 检查项目是否可以删除
   */
  async canDeleteProject(id: string): Promise<{ canDelete: boolean; reason?: string }> {
    try {
      const project = await this.getProject(id);
      if (!project) {
        return { canDelete: false, reason: '项目不存在' };
      }

      if (project.asset_count && project.asset_count > 0) {
        return {
          canDelete: false,
          reason: `该项目还有 ${project.asset_count} 个关联资产，无法删除`
        };
      }

      return { canDelete: true };
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      console.error('检查项目删除条件失败:', enhancedError.message);
      return { canDelete: false, reason: '检查失败，请稍后重试' };
    }
  }

  /**
   * 获取项目下拉选项（简化版）
   */
  async getProjectSelectOptions(): Promise<Array<{ value: string; label: string }>> {
    try {
      const options = await this.getProjectOptions();
      return options.map(option => ({
        value: option.id,
        label: `${option.name} (${option.code})`
      }));
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      console.error('获取项目选择选项失败:', enhancedError.message);
      return [];
    }
  }

  /**
   * 根据关键词搜索项目
   */
  async searchProjectsByKeyword(keyword: string): Promise<Project[]> {
    try {
      const result = await this.searchProjects({ keyword });
      return result.items;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      console.error('关键词搜索项目失败:', enhancedError.message);
      return [];
    }
  }

  /**
   * 根据权属方获取项目列表
   */
  async getProjectsByOwnership(ownershipId: string): Promise<Project[]> {
    try {
      const result = await this.getProjects({ ownership_id: ownershipId });
      return result.items;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      console.error('根据权属方获取项目失败:', enhancedError.message);
      return [];
    }
  }

  /**
   * 获取活跃项目列表
   */
  async getActiveProjects(): Promise<Project[]> {
    try {
      const result = await this.getProjects({ is_active: true });
      return result.items;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      console.error('获取活跃项目失败:', enhancedError.message);
      return [];
    }
  }

  /**
   * 获取非活跃项目列表
   */
  async getInactiveProjects(): Promise<Project[]> {
    try {
      const result = await this.getProjects({ is_active: false });
      return result.items;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      console.error('获取非活跃项目失败:', enhancedError.message);
      return [];
    }
  }

  // ==================== 高级功能 ====================

  /**
   * 项目数据导出
   */
  async exportProjects(format: 'excel' | 'csv' = 'excel', filters?: ProjectSearchParams): Promise<Blob> {
    try {
      const result = await enhancedApiClient.get<Blob>(
        `${this.baseUrl}/export`,
        {
          params: { format, ...filters },
          responseType: 'blob',
          retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 }
        }
      );

      if (!result.success) {
        throw new Error(`导出项目数据失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  /**
   * 项目数据导入
   */
  async importProjects(file: File): Promise<{
    success: boolean;
    message: string;
    imported?: number;
    errors?: string[];
  }> {
    try {
      const formData = new FormData();
      formData.append('file', file);

      const result = await enhancedApiClient.post<{
        success: boolean;
        message: string;
        imported?: number;
        errors?: string[];
      }>(
        `${this.baseUrl}/import`,
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data'
          },
          retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
          smartExtract: true
        }
      );

      if (!result.success) {
        throw new Error(`导入项目数据失败: ${result.error}`);
      }

      return result.data!;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(enhancedError.message);
    }
  }

  /**
   * 获取项目详情完整信息（包含关联数据）
   */
  async getProjectFullDetails(id: string): Promise<{
    project: Project;
    assetCount: number;
    totalArea: number;
    lastUpdated: string;
  }> {
    try {
      const [project, statistics] = await Promise.all([
        this.getProject(id),
        this.getProjectStatistics()
      ]);

      // 从统计中查找当前项目的数据
      const projectStats = statistics.projects?.find(p => p.id === id) || {
        asset_count: 0,
        total_area: 0
      };

      return {
        project,
        assetCount: projectStats.asset_count || 0,
        totalArea: projectStats.total_area || 0,
        lastUpdated: project.updated_at
      };
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(`获取项目完整信息失败: ${enhancedError.message}`);
    }
  }
}

// 创建单例实例
export const projectService = new ProjectService();