/**
 * 联系人管理服务
 *
 * @description 提供权属方、项目、租户等实体的联系人管理功能
 * @module services
 */

import { enhancedApiClient } from '@/api/client';

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
  limit: number;
  pages: number;
}

/**
 * 联系人服务类
 */
class ContactService {
  private readonly basePath = '/api/v1/contacts';

  /**
   * 创建联系人
   */
  async createContact(data: ContactCreate): Promise<Contact> {
    const response = await enhancedApiClient.post<Contact>(this.basePath, data);
    return response.data!;
  }

  /**
   * 获取联系人详情
   */
  async getContact(id: string): Promise<Contact> {
    const response = await enhancedApiClient.get<Contact>(`${this.basePath}/${id}`);
    return response.data!;
  }

  /**
   * 获取实体的所有联系人
   */
  async getEntityContacts(
    entityType: string,
    entityId: string,
    page = 1,
    limit = 10
  ): Promise<ContactListResponse> {
    const response = await enhancedApiClient.get<ContactListResponse>(
      `${this.basePath}/entity/${entityType}/${entityId}`,
      { params: { page, limit } }
    );
    return response.data!;
  }

  /**
   * 获取实体的主要联系人
   */
  async getPrimaryContact(entityType: string, entityId: string): Promise<Contact | null> {
    try {
      const response = await enhancedApiClient.get<Contact>(
        `${this.basePath}/entity/${entityType}/${entityId}/primary`
      );
      return response.data ?? null;
    } catch (error) {
      // 404错误表示没有主要联系人
      return null;
    }
  }

  /**
   * 更新联系人
   */
  async updateContact(id: string, data: ContactUpdate): Promise<Contact> {
    const response = await enhancedApiClient.put<Contact>(
      `${this.basePath}/${id}`,
      data
    );
    return response.data!;
  }

  /**
   * 删除联系人（软删除）
   */
  async deleteContact(id: string): Promise<Contact> {
    const response = await enhancedApiClient.delete<Contact>(`${this.basePath}/${id}`);
    return response.data!;
  }

  /**
   * 批量创建联系人
   */
  async createContactsBatch(
    entityType: string,
    entityId: string,
    contacts: ContactCreate[]
  ): Promise<Contact[]> {
    const response = await enhancedApiClient.post<Contact[]>(
      `${this.basePath}/batch/${entityType}/${entityId}`,
      contacts
    );
    return response.data!;
  }
}

// 导出单例实例
export const contactService = new ContactService();
