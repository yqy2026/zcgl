import type { User } from '@/services/systemService';

export type Tone = 'primary' | 'success' | 'warning' | 'error' | 'neutral';
export type UserStatus = User['status'];

export interface StatusMeta {
  label: string;
  hint: string;
  tone: Tone;
}

export interface UserStatistics {
  total: number;
  active: number;
  inactive: number;
  locked: number;
  by_role: Record<string, number>;
  by_organization: Record<string, number>;
}

export interface UserFilters {
  keyword: string;
  status: string;
  roleId: string;
  organizationId: string;
}

export interface UsersQueryResult {
  items: User[];
  total: number;
}

export interface UserPaginationState {
  current: number;
  pageSize: number;
}
