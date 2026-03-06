/**
 * 项目相关服务 - 统一响应处理版本
 *
 * @description 项目管理核心服务，提供项目CRUD、搜索、统计等完整功能
 * @author Claude Code
 */

import { apiClient } from '@/api/client';
import { ApiErrorHandler } from '@/utils/responseExtractor';
import { API_ENDPOINTS } from '@/constants/api';
import { createLogger } from '@/utils/logger';

const projectLogger = createLogger('Project');
import type {
  Project,
  ProjectActiveAssetsResponse,
  ProjectCreate,
  ProjectUpdate,
  ProjectListResponse,
  ProjectSearchRequest,
  ProjectStatisticsResponse,
  ProjectDeleteResponse,
  ProjectSearchParams,
  ProjectDropdownOption,
} from '@/types/project';

export class ProjectService {
  private baseUrl = API_ENDPOINTS.PROJECT.LIST;

  // ==================== 基础CRUD操作 ====================

  /**
   * 搜索项目
   */
  async searchProjects(searchParams: ProjectSearchRequest): Promise<ProjectListResponse> {
    try {
      const result = await apiClient.post<ProjectListResponse>(
        `${this.baseUrl}/search`,
        searchParams,
        {
          retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
          smartExtract: true,
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
      const result = await apiClient.get<Project>(API_ENDPOINTS.PROJECT.DETAIL(id), {
        cache: true,
        retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
        smartExtract: true,
      });

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
   * 获取项目有效关联资产（基于 project_assets 当前有效关系）
   */
  async getProjectAssets(projectId: string): Promise<ProjectActiveAssetsResponse> {
    try {
      const result = await apiClient.get<ProjectActiveAssetsResponse>(
        API_ENDPOINTS.PROJECT.ASSETS(projectId),
        {
          cache: true,
          retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
          smartExtract: true,
        }
      );

      if (!result.success) {
        throw new Error(`获取项目关联资产失败: ${result.error}`);
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
        page: params?.page ?? 1,
        page_size: params?.page_size ?? 10,
        ...(params?.keyword != null && params.keyword.trim() !== '' ? { keyword: params.keyword } : {}),
        ...(params?.status != null && params.status.trim() !== '' ? { status: params.status } : {}),
        ...(params?.owner_party_id != null && params.owner_party_id.trim() !== ''
          ? { owner_party_id: params.owner_party_id }
          : {}),
      };

      const result = await apiClient.get<ProjectListResponse>(this.baseUrl, {
        params: requestParams,
        cache: true,
        retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
        smartExtract: true,
      });

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
      const result = await apiClient.post<Project>(this.baseUrl, data, {
        retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
        smartExtract: true,
      });

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
      const result = await apiClient.put<Project>(API_ENDPOINTS.PROJECT.UPDATE(id), data, {
        retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
        smartExtract: true,
      });

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
      const result = await apiClient.delete<ProjectDeleteResponse>(
        API_ENDPOINTS.PROJECT.DELETE(id),
        {
          retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
          smartExtract: true,
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
      const result = await apiClient.put<Project>(
        `${this.baseUrl}/${id}/status`,
        {},
        {
          retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
          smartExtract: true,
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
      const result = await apiClient.get<ProjectStatisticsResponse>(
        `${this.baseUrl}/stats/overview`,
        {
          cache: true,
          retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
          smartExtract: true,
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
  async getProjectOptions(status: string = 'active'): Promise<ProjectDropdownOption[]> {
    try {
      const normalizedStatus = status.trim();
      const params =
        normalizedStatus !== ''
          ? {
              status: normalizedStatus,
            }
          : undefined;
      const result = await apiClient.get<ProjectDropdownOption[]>(
        `${this.baseUrl}/dropdown-options`,
        {
          params,
          cache: true,
          retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
          smartExtract: true,
        }
      );

      if (!result.success) {
        throw new Error(`获取项目选项失败: ${result.error}`);
      }

      // 确保返回数组格式
      const data = result.data!;
      if (Array.isArray(data)) return data;
      const possibleData = (data as Record<string, unknown>).data;
      return Array.isArray(possibleData) ? (possibleData as ProjectDropdownOption[]) : [];
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
      return projects.filter(project => {
        if (project == null) {
          return false;
        }
        if (project.data_status != null && project.data_status !== '正常') {
          return false;
        }
        return true;
      });
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      projectLogger.error('批量获取项目信息失败:', undefined, { error: enhancedError.message });
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
      return !result.items.some(item => item.project_code === code && item.id !== excludeId);
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      projectLogger.error('验证项目编码失败:', undefined, { error: enhancedError.message });
      return false;
    }
  }

  /**
   * 验证项目名称唯一性
   */
  async validateProjectName(name: string, excludeId?: string): Promise<boolean> {
    try {
      const result = await this.getProjects({ keyword: name });
      return !result.items.some(item => item.project_name === name && item.id !== excludeId);
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      projectLogger.error('验证项目名称失败:', undefined, { error: enhancedError.message });
      return false;
    }
  }

  // ==================== 查询功能 ====================

  /**
   * 根据条件获取项目数量
   */
  async getProjectCount(params?: ProjectSearchParams): Promise<number> {
    try {
      const result = await this.getProjects({ ...params, page_size: 1 });
      return result.total;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      projectLogger.error('获取项目数量失败:', undefined, { error: enhancedError.message });
      return 0;
    }
  }

  /**
   * 检查项目是否可以删除
   */
  async canDeleteProject(id: string): Promise<{ canDelete: boolean; reason?: string }> {
    try {
      const project = await this.getProject(id);
      if (project == null) {
        return { canDelete: false, reason: '项目不存在' };
      }

      if (project.asset_count != null && project.asset_count > 0) {
        return {
          canDelete: false,
          reason: `该项目还有 ${project.asset_count} 个关联资产，无法删除`,
        };
      }

      return { canDelete: true };
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      projectLogger.error('检查项目删除条件失败:', undefined, { error: enhancedError.message });
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
        label: `${option.project_name} (${option.project_code})`,
      }));
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      projectLogger.error('获取项目选择选项失败:', undefined, { error: enhancedError.message });
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
      projectLogger.error('关键词搜索项目失败:', undefined, { error: enhancedError.message });
      return [];
    }
  }

  /**
   * 根据权属方获取项目列表
   */
  async getProjectsByOwnerParty(ownerPartyId: string): Promise<Project[]> {
    try {
      const result = await this.getProjects({ owner_party_id: ownerPartyId });
      return result.items;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      projectLogger.error('根据主体获取项目失败:', undefined, { error: enhancedError.message });
      return [];
    }
  }

  /**
   * 获取活跃项目列表
   */
  async getActiveProjects(): Promise<Project[]> {
    try {
      const result = await this.getProjects({ status: 'active' });
      return result.items;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      projectLogger.error('获取活跃项目失败:', undefined, { error: enhancedError.message });
      return [];
    }
  }

  /**
   * 获取非活跃项目列表
   */
  async getInactiveProjects(): Promise<Project[]> {
    try {
      const result = await this.getProjects({ status: 'terminated' });
      return result.items;
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      projectLogger.error('获取非活跃项目失败:', undefined, { error: enhancedError.message });
      return [];
    }
  }

  // ==================== 高级功能 ====================

  /**
   * 项目数据导出
   */
  async exportProjects(
    format: 'excel' | 'csv' = 'excel',
    filters?: ProjectSearchParams
  ): Promise<Blob> {
    try {
      const result = await apiClient.get<Blob>(`${this.baseUrl}/export`, {
        params: { format, ...filters },
        responseType: 'blob',
        retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
      });

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

      const result = await apiClient.post<{
        success: boolean;
        message: string;
        imported?: number;
        errors?: string[];
      }>(`${this.baseUrl}/import`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        retry: { maxAttempts: 3, delay: 1000, backoffMultiplier: 2 },
        smartExtract: true,
      });

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
      const project = await this.getProject(id);
      const assetCount = project.asset_count ?? 0;
      const totalArea = 0;

      return {
        project,
        assetCount,
        totalArea,
        lastUpdated: project.updated_at,
      };
    } catch (error) {
      const enhancedError = ApiErrorHandler.handleError(error);
      throw new Error(`获取项目完整信息失败: ${enhancedError.message}`);
    }
  }
}

// 创建单例实例
export const projectService = new ProjectService();
