/**
 * 催缴管理相关类型定义
 * 对齐: backend/src/schemas/collection.py
 */

/** 催缴方式枚举 */
export enum CollectionMethod {
  PHONE = 'phone',
  SMS = 'sms',
  EMAIL = 'email',
  WECOM = 'wecom',
  VISIT = 'visit',
  LETTER = 'letter',
  OTHER = 'other',
}

/** 催缴方式显示名称 */
export const CollectionMethodLabels: Record<CollectionMethod, string> = {
  [CollectionMethod.PHONE]: '电话',
  [CollectionMethod.SMS]: '短信',
  [CollectionMethod.EMAIL]: '邮件',
  [CollectionMethod.WECOM]: '企业微信',
  [CollectionMethod.VISIT]: '上门拜访',
  [CollectionMethod.LETTER]: '信函',
  [CollectionMethod.OTHER]: '其他',
};

/** 催缴状态枚举 */
export enum CollectionStatus {
  PENDING = 'pending',
  IN_PROGRESS = 'in_progress',
  SUCCESS = 'success',
  FAILED = 'failed',
  PARTIAL = 'partial',
}

/** 催缴状态显示名称 */
export const CollectionStatusLabels: Record<CollectionStatus, string> = {
  [CollectionStatus.PENDING]: '待催缴',
  [CollectionStatus.IN_PROGRESS]: '催缴中',
  [CollectionStatus.SUCCESS]: '催缴成功',
  [CollectionStatus.FAILED]: '催缴失败',
  [CollectionStatus.PARTIAL]: '部分成功',
};

/** 催缴状态颜色 */
export const CollectionStatusColors: Record<CollectionStatus, string> = {
  [CollectionStatus.PENDING]: 'default',
  [CollectionStatus.IN_PROGRESS]: 'processing',
  [CollectionStatus.SUCCESS]: 'success',
  [CollectionStatus.FAILED]: 'error',
  [CollectionStatus.PARTIAL]: 'warning',
};

/** 催缴记录基础类型 */
export interface CollectionRecordBase {
  ledger_id: string;
  contract_id: string;
  collection_method: CollectionMethod;
  collection_date: string; // ISO date string
  collection_status: CollectionStatus;
  contacted_person?: string | null;
  contact_phone?: string | null;
  promised_amount?: number | null;
  promised_date?: string | null;
  actual_payment_amount?: number | null;
  collection_notes?: string | null;
  next_follow_up_date?: string | null;
}

/** 创建催缴记录请求 */
export interface CollectionRecordCreate extends CollectionRecordBase {
  operator?: string | null;
  operator_id?: string | null;
}

/** 更新催缴记录请求 */
export interface CollectionRecordUpdate {
  collection_status?: CollectionStatus | null;
  contacted_person?: string | null;
  contact_phone?: string | null;
  promised_amount?: number | null;
  promised_date?: string | null;
  actual_payment_amount?: number | null;
  collection_notes?: string | null;
  next_follow_up_date?: string | null;
}

/** 催缴记录响应 */
export interface CollectionRecord extends CollectionRecordBase {
  id: string;
  operator?: string | null;
  operator_id?: string | null;
  created_at: string;
  updated_at: string;
}

/** 催缴任务汇总 */
export interface CollectionTaskSummary {
  total_overdue_count: number;
  total_overdue_amount: number;
  pending_collection_count: number;
  this_month_collection_count: number;
  collection_success_rate?: number | null;
}

/** 催缴记录列表响应 */
export interface CollectionRecordListResponse {
  items: CollectionRecord[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}
