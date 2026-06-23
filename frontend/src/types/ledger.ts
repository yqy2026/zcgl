export type LedgerPaymentStatus = 'unpaid' | 'paid' | 'partial' | 'voided';

export interface LedgerEntry {
  entry_id: string;
  contract_id: string;
  year_month: string;
  due_date: string;
  amount_due: string | number;
  currency_code: string;
  is_tax_included: boolean;
  tax_rate?: string | number | null;
  payment_status: LedgerPaymentStatus | string;
  paid_amount: string | number;
  notes?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface LedgerListParams {
  asset_id?: string;
  party_id?: string;
  contract_id?: string;
  year_month_start?: string;
  year_month_end?: string;
  payment_status?: LedgerPaymentStatus;
  include_voided?: boolean;
  offset?: number;
  limit?: number;
}

export interface LedgerListResponse {
  items: LedgerEntry[];
  total: number;
  offset: number;
  limit: number;
}

export interface LedgerBatchUpdatePayload {
  entry_ids: string[];
  paid_amount?: string | number | null;
  notes?: string | null;
}

export interface LedgerRecalculateSkippedEntry {
  entry_id: string;
  year_month: string;
  payment_status: string;
  reason: string;
}

export interface LedgerRecalculateResult {
  created: number;
  updated: number;
  voided: number;
  skipped_entries: LedgerRecalculateSkippedEntry[];
}
