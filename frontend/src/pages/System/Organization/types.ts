import type { Organization } from '@/types/organization';

export interface OrganizationFormData {
  name: string;
  code: string;
  type: string;
  parent_id?: string;
  description?: string;
  status: string;
  sort_order?: number;
}

export interface OrganizationFilters {
  keyword: string;
}

export interface OrganizationListQueryResult {
  items: Organization[];
  total: number;
}

export interface OrganizationPaginationState {
  current: number;
  pageSize: number;
}

export interface OrganizationSelectOption {
  value: string;
  label: string;
  color?: string;
}

export type Tone = 'primary' | 'success' | 'warning' | 'error' | 'neutral';

export interface HistoryActionMeta {
  label: string;
  tone: Tone;
}
