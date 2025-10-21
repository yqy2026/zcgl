/**
 * 项目相关服务
 */

import { apiClient } from './api';
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
  private baseUrl = '/projects';

  /**
   * 获取项目列表
   */
  async getProjects(params?: ProjectSearchParams): Promise<ProjectListResponse> {
    const response = await apiClient.get(this.baseUrl, { params });
    return response.data || response as ProjectListResponse;
  }

  /**
   * 搜索项目
   */
  async searchProjects(searchParams: ProjectSearchRequest): Promise<ProjectListResponse> {
    const response = await apiClient.post(`${this.baseUrl}/search`, searchParams);
    return response.data;
  }

  /**
   * 获取项目详情
   */
  async getProject(id: string): Promise<Project> {
    const response = await apiClient.get(`${this.baseUrl}/${id}`);
    return response.data;
  }

  /**
   * 创建项目
   */
  async createProject(data: ProjectCreate): Promise<Project> {
    const response = await apiClient.post(this.baseUrl, data);
    return response.data;
  }

  /**
   * 更新项目
   */
  async updateProject(id: string, data: ProjectUpdate): Promise<Project> {
    const response = await apiClient.put(`${this.baseUrl}/${id}`, data);
    return response.data;
  }

  /**
   * 删除项目
   */
  async deleteProject(id: string): Promise<ProjectDeleteResponse> {
    const response = await apiClient.delete(`${this.baseUrl}/${id}`);
    return response.data;
  }

  /**
   * 切换项目状态
   */
  async toggleProjectStatus(id: string): Promise<Project> {
    const response = await apiClient.post(`${this.baseUrl}/${id}/toggle-status`);
    return response.data;
  }

  /**
   * 获取项目统计信息
   */
  async getProjectStatistics(): Promise<ProjectStatisticsResponse> {
    const response = await apiClient.get(`${this.baseUrl}/statistics/summary`);
    return response.data || response as ProjectStatisticsResponse;
  }

  /**
   * 获取项目选项列表
   */
  async getProjectOptions(isActive: boolean = true): Promise<ProjectDropdownOption[]> {
    const response = await apiClient.get(`${this.baseUrl}/dropdown-options?is_active=${isActive}`);
    // 处理响应数据格式，确保返回数组
    const data = response.data;
    return Array.isArray(data) ? data : (data?.data || []);
  }

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
      console.error('验证项目编码失败:', error);
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
      console.error('验证项目名称失败:', error);
      return false;
    }
  }

  /**
   * 批量获取项目信息
   */
  async getProjectsByIds(ids: string[]): Promise<Project[]> {
    try {
      const promises = ids.map(id => this.getProject(id));
      const projects = await Promise.all(promises);
      return projects.filter(project => project && project.is_active);
    } catch (error) {
      console.error('批量获取项目信息失败:', error);
      return [];
    }
  }

  /**
   * 根据条件获取项目数量
   */
  async getProjectCount(params?: ProjectSearchParams): Promise<number> {
    try {
      const result = await this.getProjects({ ...params, size: 1 });
      return result.total;
    } catch (error) {
      console.error('获取项目数量失败:', error);
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
      console.error('检查项目删除条件失败:', error);
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
      console.error('获取项目选择选项失败:', error);
      return [];
    }
  }
}

// 创建单例实例
export const projectService = new ProjectService();