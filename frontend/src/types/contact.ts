/**
 * 联系人相关类型定义
 * 对齐: backend/src/schemas/contact.py
 */

/** 联系人类型枚举 */
export enum ContactType {
  PRIMARY = 'primary',
  FINANCE = 'finance',
  OPERATIONS = 'operations',
  LEGAL = 'legal',
  GENERAL = 'general',
}

/** 联系人类型显示名称 */
export const ContactTypeLabels: Record<ContactType, string> = {
  [ContactType.PRIMARY]: '主要联系人',
  [ContactType.FINANCE]: '财务联系人',
  [ContactType.OPERATIONS]: '运营联系人',
  [ContactType.LEGAL]: '法务联系人',
  [ContactType.GENERAL]: '一般联系人',
};

/** 联系人基础类型 */
export interface ContactBase {
  name: string;
  title?: string | null;
  department?: string | null;
  phone?: string | null;
  office_phone?: string | null;
  email?: string | null;
  wechat?: string | null;
  address?: string | null;
  contact_type: ContactType;
  is_primary: boolean;
  notes?: string | null;
  preferred_contact_time?: string | null;
  preferred_contact_method?: string | null;
}

/** 创建联系人请求 */
export interface ContactCreate extends ContactBase {
  entity_type: 'ownership' | 'project' | 'tenant';
  entity_id: string;
}

/** 更新联系人请求 */
export interface ContactUpdate {
  name?: string | null;
  title?: string | null;
  department?: string | null;
  phone?: string | null;
  office_phone?: string | null;
  email?: string | null;
  wechat?: string | null;
  address?: string | null;
  contact_type?: ContactType | null;
  is_primary?: boolean | null;
  notes?: string | null;
  preferred_contact_time?: string | null;
  preferred_contact_method?: string | null;
}

/** 联系人响应 */
export interface Contact extends ContactBase {
  id: string;
  entity_type: string;
  entity_id: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  created_by?: string | null;
  updated_by?: string | null;
}

/** 联系人列表响应 */
export interface ContactListResponse {
  items: Contact[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

/** 主要联系人简要信息 */
export interface PrimaryContact {
  id: string;
  name: string;
  title?: string | null;
  phone?: string | null;
  email?: string | null;
  wechat?: string | null;
  preferred_contact_method?: string | null;
}
