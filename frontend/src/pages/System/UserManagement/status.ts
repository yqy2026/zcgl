import type { StatusMeta, UserStatus } from './types';

export const STATUS_META_MAP: Record<UserStatus, StatusMeta> = {
  active: { label: '活跃', hint: '可登录', tone: 'success' },
  inactive: { label: '停用', hint: '已禁用', tone: 'error' },
  locked: { label: '锁定', hint: '异常冻结', tone: 'warning' },
};

const FALLBACK_STATUS_META: StatusMeta = {
  label: '未知',
  hint: '状态缺失',
  tone: 'neutral',
};

export const resolveStatusMeta = (status: UserStatus | string | null | undefined): StatusMeta => {
  if (status === 'active' || status === 'inactive' || status === 'locked') {
    return STATUS_META_MAP[status];
  }
  return FALLBACK_STATUS_META;
};

export const USER_STATUS_FILTER_OPTIONS: Array<{ value: UserStatus; label: string }> = [
  { value: 'active', label: STATUS_META_MAP.active.label },
  { value: 'inactive', label: STATUS_META_MAP.inactive.label },
  { value: 'locked', label: STATUS_META_MAP.locked.label },
];

export const USER_STATUS_FORM_OPTIONS: Array<{ value: 'active' | 'inactive'; label: string }> = [
  { value: 'active', label: STATUS_META_MAP.active.label },
  { value: 'inactive', label: STATUS_META_MAP.inactive.label },
];
