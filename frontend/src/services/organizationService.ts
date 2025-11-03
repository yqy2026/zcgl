/**
 * 组织架构管理服务
 */

import { apiClient } from './api';
import {
  Organization,
  OrganizationCreate,
  OrganizationUpdate,
  OrganizationTree,
  OrganizationHistory,
  OrganizationStatistics,
  OrganizationMoveRequest,
  OrganizationBatchRequest,
  OrganizationBatchResult,
  OrganizationMoveResult,
  OrganizationPath,
  OrganizationAdvancedSearch
} from '../types/organization';

class OrganizationService {
  private baseUrl = '/organizations';

  /**
   * 获取组织列表
   */
  async getOrganizations(params?: {
    skip?: number;
    limit?: number;
  }): Promise<Organization[]> {
    try {
      const response = await apiClient.get(this.baseUrl, { params });

      // 确保响应数据存在
      if (!response.data) {
        console.warn('组织API响应为空，返回空数组');
        return [];
      }

      // 如果响应是数组，直接返回；如果是对象，提取data字段
      return Array.isArray(response.data) ? response.data : response.data.data || [];
    } catch (error) {
      console.error('获取组织列表失败:', error);
      return [];
    }
  }

  /**
   * 获取组织树形结构
   */
  async getOrganizationTree(parentId?: string): Promise<OrganizationTree[]> {
    try {
      const params = parentId ? { parent_id: parentId } : {};
      const response = await apiClient.get(`/api/v1tree`, { params });

      // 确保响应数据存在
      if (!response.data) {
        console.warn('组织树API响应为空，返回空数组');
        return [];
      }

      // 如果响应是数组，直接返回；如果是对象，提取data字段
      return Array.isArray(response.data) ? response.data : response.data.data || [];
    } catch (error) {
      console.error('获取组织树失败:', error);
      return [];
    }
  }

  /**
   * 搜索组织
   */
  async searchOrganizations(
    keyword: string,
    params?: { skip?: number; limit?: number }
  ): Promise<Organization[]> {
    const response = await apiClient.get(`/api/v1search`, {
      params: { keyword, ...params }
    });
    return response.data;
  }

  /**
   * 高级搜索组织
   */
  async advancedSearchOrganizations(
    searchRequest: OrganizationAdvancedSearch
  ): Promise<Organization[]> {
    const response = await apiClient.post(`/api/v1advanced-search`, searchRequest);
    return response.data;
  }

  /**
   * 获取组织统计信息
   */
  async getStatistics(): Promise<OrganizationStatistics> {
    const response = await apiClient.get(`/api/v1statistics`);
    return response.data;
  }

  /**
   * 根据ID获取组织详情
   */
  async getOrganization(id: string): Promise<Organization> {
    const response = await apiClient.get(`/api/v1${id}`);
    return response.data;
  }

  /**
   * 获取组织的子组织
   */
  async getOrganizationChildren(
    id: string,
    recursive: boolean = false
  ): Promise<Organization[]> {
    const response = await apiClient.get(`/api/v1${id}/children`, {
      params: { recursive }
    });
    return response.data;
  }

  /**
   * 获取组织到根节点的路径
   */
  async getOrganizationPath(id: string): Promise<OrganizationPath> {
    const response = await apiClient.get(`/api/v1${id}/path`);
    const organizations = response.data;
    const pathString = organizations.map((org: Organization) => org.name).join(' > ');
    return { organizations, path_string: pathString };
  }

  /**
   * 获取组织变更历史
   */
  async getOrganizationHistory(
    id: string,
    params?: { skip?: number; limit?: number }
  ): Promise<OrganizationHistory[]> {
    const response = await apiClient.get(`/api/v1${id}/history`, { params });
    return response.data;
  }

  /**
   * 创建组织
   */
  async createOrganization(organization: OrganizationCreate): Promise<Organization> {
    const response = await apiClient.post(this.baseUrl, organization);
    return response.data;
  }

  /**
   * 更新组织
   */
  async updateOrganization(id: string, organization: OrganizationUpdate): Promise<Organization> {
    const response = await apiClient.put(`/api/v1${id}`, organization);
    return response.data;
  }

  /**
   * 删除组织
   */
  async deleteOrganization(id: string, deletedBy?: string): Promise<void> {
    const params = deletedBy ? { deleted_by: deletedBy } : {};
    await apiClient.delete(`/api/v1${id}`, { params });
  }

  /**
   * 移动组织
   */
  async moveOrganization(
    id: string,
    moveRequest: OrganizationMoveRequest
  ): Promise<OrganizationMoveResult> {
    const response = await apiClient.post(`/api/v1${id}/move`, moveRequest);
    return response.data;
  }

  /**
   * 批量操作组织
   */
  async batchOrganizationOperation(
    batchRequest: OrganizationBatchRequest
  ): Promise<OrganizationBatchResult> {
    const response = await apiClient.post(`/api/v1batch`, batchRequest);
    return response.data;
  }



  /**
   * 批量删除组织
   */
  async batchDeleteOrganizations(
    organizationIds: string[],
    deletedBy?: string
  ): Promise<OrganizationBatchResult> {
    return this.batchOrganizationOperation({
      organization_ids: organizationIds,
      action: 'delete',
      updated_by: deletedBy
    });
  }





  /**
   * 构建组织树形数据
   */
  buildOrganizationTreeData(organizations: Organization[]) {
    const treeData: any[] = [];
    const organizationMap = new Map<string, Organization>();
    
    // 创建组织映射
    organizations.forEach(org => {
      organizationMap.set(org.id, org);
    });

    // 构建树形结构
    organizations.forEach(org => {
      const treeNode = {
        key: org.id,
        value: org.id,
        title: org.name,
        children: []
      };

      if (!org.parent_id) {
        treeData.push(treeNode);
      } else {
        const parent = organizationMap.get(org.parent_id);
        if (parent) {
          // 找到父节点并添加子节点
          this.addChildToTreeNode(treeData, org.parent_id, treeNode);
        }
      }
    });

    return treeData;
  }

  /**
   * 向树节点添加子节点
   */
  private addChildToTreeNode(treeData: any[], parentId: string, childNode: any) {
    for (const node of treeData) {
      if (node.key === parentId) {
        node.children = node.children || [];
        node.children.push(childNode);
        return true;
      }
      if (node.children && this.addChildToTreeNode(node.children, parentId, childNode)) {
        return true;
      }
    }
    return false;
  }

  /**
   * 获取组织层级路径
   */
  getOrganizationLevelPath(organization: Organization, allOrganizations: Organization[]): string[] {
    const path: string[] = [];
    let current: Organization | null = organization;

    while (current) {
      path.unshift(current.name);
      if (current.parent_id) {
        const parentOrg = allOrganizations.find(org => org.id === current!.parent_id);
        current = parentOrg || null;
      } else {
        break;
      }
    }

    return path;
  }

  /**
   * 检查是否可以移动组织（避免循环引用）
   */
  canMoveOrganization(
    organizationId: string,
    targetParentId: string,
    allOrganizations: Organization[]
  ): boolean {
    if (organizationId === targetParentId) {
      return false;
    }

    // 检查目标父组织是否是当前组织的子组织
    const isDescendant = (parentId: string, childId: string): boolean => {
      const children = allOrganizations.filter(org => org.parent_id === parentId);
      for (const child of children) {
        if (child.id === childId || isDescendant(child.id, childId)) {
          return true;
        }
      }
      return false;
    };

    return !isDescendant(organizationId, targetParentId);
  }

  /**
   * 格式化组织显示名称
   */
  formatOrganizationDisplayName(organization: Organization): string {
    return organization.name;
  }

  /**
   * 导出组织数据
   */
  async exportOrganizations(format: 'excel' | 'csv' = 'excel'): Promise<Blob> {
    const response = await apiClient.get(`/api/v1export`, {
      params: { format },
      responseType: 'blob'
    });
    return response.data;
  }

  /**
   * 导入组织数据
   */
  async importOrganizations(file: File): Promise<any> {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await apiClient.post(`/api/v1import`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    });
    return response.data;
  }
}

export const organizationService = new OrganizationService();