/**
 * 安全事件相关类型定义
 * 对齐: backend/src/models/security_event.py
 */

/** 安全事件类型枚举 */
export enum SecurityEventType {
  AUTH_FAILURE = 'auth_failure',
  AUTH_SUCCESS = 'auth_success',
  PERMISSION_DENIED = 'permission_denied',
  RATE_LIMIT_EXCEEDED = 'rate_limit_exceeded',
  SUSPICIOUS_ACTIVITY = 'suspicious_activity',
  ACCOUNT_LOCKED = 'account_locked',
}

/** 安全事件类型显示名称 */
export const SecurityEventTypeLabels: Record<SecurityEventType, string> = {
  [SecurityEventType.AUTH_FAILURE]: '认证失败',
  [SecurityEventType.AUTH_SUCCESS]: '认证成功',
  [SecurityEventType.PERMISSION_DENIED]: '权限拒绝',
  [SecurityEventType.RATE_LIMIT_EXCEEDED]: '速率限制',
  [SecurityEventType.SUSPICIOUS_ACTIVITY]: '可疑活动',
  [SecurityEventType.ACCOUNT_LOCKED]: '账户锁定',
};

/** 安全事件严重程度枚举 */
export enum SecuritySeverity {
  LOW = 'low',
  MEDIUM = 'medium',
  HIGH = 'high',
  CRITICAL = 'critical',
}

/** 安全事件严重程度显示名称 */
export const SecuritySeverityLabels: Record<SecuritySeverity, string> = {
  [SecuritySeverity.LOW]: '低',
  [SecuritySeverity.MEDIUM]: '中',
  [SecuritySeverity.HIGH]: '高',
  [SecuritySeverity.CRITICAL]: '严重',
};

/** 安全事件严重程度颜色映射 */
export const SecuritySeverityColors: Record<SecuritySeverity, string> = {
  [SecuritySeverity.LOW]: 'blue',
  [SecuritySeverity.MEDIUM]: 'orange',
  [SecuritySeverity.HIGH]: 'red',
  [SecuritySeverity.CRITICAL]: 'magenta',
};

/** 安全事件接口 */
export interface SecurityEvent {
  id: string;
  event_type: SecurityEventType;
  severity: SecuritySeverity;
  user_id?: string | null;
  ip_address?: string | null;
  event_metadata?: Record<string, any> | null;
  created_at: string;
}

/** 安全事件列表响应 */
export interface SecurityEventListResponse {
  items: SecurityEvent[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}
