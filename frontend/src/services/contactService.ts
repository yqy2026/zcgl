/**
 * 联系人管理服务
 *
 * @description 提供权属方、项目、租户等实体的联系人管理功能
 * @module services
 */

import { apiClient } from '@/api/client';

/**
 * 联系人类型枚举
 */
export enum ContactType {
  PRIMARY = 'primary',
  FINANCE = 'finance',
  OPERATIONS = 'operations',
  LEGAL = 'legal',
  GENERAL = 'general',
}

/**
 * 联系人数据结构
 */
export interface Contact {
  id: string;
  entity_type: string;
  entity_id: string;
  name: string;
  title?: string;
  department?: string;
  phone?: string;
  office_phone?: string;
  email?: string;
  wechat?: string;
  address?: string;
  contact_type: ContactType;
  is_primary: boolean;
  notes?: string;
  preferred_contact_time?: string;
  preferred_contact_method?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  created_by?: string;
  updated_by?: string;
}

/**
 * 创建联系人请求
 */
export interface ContactCreate {
  entity_type: string;
  entity_id: string;
  name: string;
  title?: string;
  department?: string;
  phone?: string;
  office_phone?: string;
  email?: string;
  wechat?: string;
  address?: string;
  contact_type?: ContactType;
  is_primary?: boolean;
  notes?: string;
  preferred_contact_time?: string;
  preferred_contact_method?: string;
}

/**
 * 更新联系人请求
 */
export interface ContactUpdate {
  name?: string;
  title?: string;
  department?: string;
  phone?: string;
  office_phone?: string;
  email?: string;
  wechat?: string;
  address?: string;
  contact_type?: ContactType;
  is_primary?: boolean;
  notes?: string;
  preferred_contact_time?: string;
  preferred_contact_method?: string;
}

/**
 * 联系人列表响应
 */
export interface ContactListResponse {
  items: Contact[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

/**
 * 联系人服务类
 */
class ContactService {
  private readonly basePath = '/contacts';

  private requireData<T>(data: T | null | undefined, errorMessage: string): T {
    if (data == null) {
      throw new Error(errorMessage);
    }
    return data;
  }

  /**
   * 创建联系人
   */
  async createContact(data: ContactCreate): Promise<Contact> {
    const response = await apiClient.post<Contact>(this.basePath, data);
    return this.requireData(response.data, '创建联系人失败');
  }

  /**
   * 获取联系人详情
   */
  async getContact(id: string): Promise<Contact> {
    const response = await apiClient.get<Contact>(`${this.basePath}/${id}`);
    return this.requireData(response.data, '获取联系人失败');
  }

  /**
   * 获取实体的所有联系人
   */
  async getEntityContacts(
    entityType: string,
    entityId: string,
    page = 1,
    pageSize = 10
  ): Promise<ContactListResponse> {
    const response = await apiClient.get<ContactListResponse>(
      `${this.basePath}/entity/${entityType}/${entityId}`,
      { params: { page, page_size: pageSize } }
    );
    return this.requireData(response.data, '获取联系人列表失败');
  }

  /**
   * 获取实体的主要联系人
   */
  async getPrimaryContact(entityType: string, entityId: string): Promise<Contact | null> {
    try {
      const response = await apiClient.get<Contact>(
        `${this.basePath}/entity/${entityType}/${entityId}/primary`
      );
      return response.data ?? null;
    } catch {
      // 404错误表示没有主要联系人
      return null;
    }
  }

  /**
   * 更新联系人
   */
  async updateContact(id: string, data: ContactUpdate): Promise<Contact> {
    const response = await apiClient.put<Contact>(`${this.basePath}/${id}`, data);
    return this.requireData(response.data, '更新联系人失败');
  }

  /**
   * 删除联系人（软删除）
   */
  async deleteContact(id: string): Promise<Contact> {
    const response = await apiClient.delete<Contact>(`${this.basePath}/${id}`);
    return this.requireData(response.data, '删除联系人失败');
  }

  /**
   * 批量创建联系人
   */
  async createContactsBatch(
    entityType: string,
    entityId: string,
    contacts: ContactCreate[]
  ): Promise<Contact[]> {
    const response = await apiClient.post<Contact[]>(
      `${this.basePath}/batch/${entityType}/${entityId}`,
      contacts
    );
    return this.requireData(response.data, '批量创建联系人失败');
  }
}

// 导出单例实例
export const contactService = new ContactService();
