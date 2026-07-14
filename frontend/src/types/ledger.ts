export type LedgerPaymentStatus = 'unpaid' | 'paid' | 'partial' | 'voided';
export type ContractLedgerView = 'terminal_collection' | 'operator_income' | 'operator_cost';
export type OperationsLedgerView = ContractLedgerView | 'service_fee_settlement';
export type OperationalPaymentFlowType =
  | 'terminal_rent_receipt'
  | 'service_fee_receipt'
  | 'upstream_cost_payment';
export type PaymentAllocationTargetType = 'contract_ledger_entry' | 'service_fee_ledger';
export type LedgerFollowUpStatus =
  | 'pending_follow_up'
  | 'contacted'
  | 'promised_payment'
  | 'disputed'
  | 'offline_received_pending_entry'
  | 'deferred';

export interface LedgerEntry {
  entry_id: string;
  contract_id: string;
  year_month: string;
  due_date: string;
  amount_due: string | number;
  ledger_views: ContractLedgerView[];
  flow_occurred_on_dates?: string[];
  currency_code: string;
  is_tax_included: boolean;
  tax_rate?: string | number | null;
  payment_status: LedgerPaymentStatus | string;
  paid_amount: string | number;
  follow_up_status?: LedgerFollowUpStatus | null;
  next_follow_up_date?: string | null;
  follow_up_note?: string | null;
  attributed_project_id?: string | null;
  attributed_owner_party_id?: string | null;
  attributed_operator_party_id?: string | null;
  attributed_asset_ids?: string[] | null;
  notes?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface LedgerListParams {
  ledger_view?: ContractLedgerView;
  project_id?: string;
  asset_id?: string;
  party_id?: string;
  contract_id?: string;
  year_month_start?: string;
  year_month_end?: string;
  flow_occurred_on_start?: string;
  flow_occurred_on_end?: string;
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

export interface OperationalPaymentFlowCreate {
  flow_type: OperationalPaymentFlowType;
  occurred_on: string;
  amount: string | number;
  counterparty_id?: string | null;
  voucher_attachment_ids?: string[] | null;
  notes?: string | null;
}

export interface OperationalPaymentFlow {
  flow_id: string;
  flow_type: OperationalPaymentFlowType;
  occurred_on: string;
  amount: string | number;
  registered_by: string;
  counterparty_id?: string | null;
  voucher_attachment_ids?: string[] | null;
  notes?: string | null;
  status: 'active' | 'voided' | 'corrected' | string;
  corrected_from_flow_id?: string | null;
  status_changed_by?: string | null;
  status_changed_at?: string | null;
  status_change_reason?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface PaymentFlowVoidPayload {
  reason: string;
}

export interface PaymentFlowCorrectionPayload {
  reason: string;
  replacement: OperationalPaymentFlowCreate;
  allocations: PaymentAllocationCreate[];
}

export interface PaymentFlowTargetQuery {
  target_type: PaymentAllocationTargetType;
  target_id: string;
}

export interface PaymentVoucherAttachment {
  id: string;
  file_name: string;
  file_type: string;
  file_size: number;
}

export interface PaymentVoucherDownloadAudit {
  log_id: string;
  user_id: string;
  flow_id: string;
  attachment_id: string;
  file_name?: string | null;
  downloaded_at: string;
  result: 'success' | 'not_found';
}

export interface OperationalPaymentFlowDetail extends OperationalPaymentFlow {
  allocations: PaymentAllocation[];
  voucher_attachments: PaymentVoucherAttachment[];
}

export interface PaymentAllocationCreate {
  target_type: PaymentAllocationTargetType;
  target_id: string;
  year_month: string;
  amount: string | number;
}

export interface PaymentAllocation {
  allocation_id: string;
  flow_id: string;
  target_type: PaymentAllocationTargetType;
  target_id: string;
  year_month: string;
  amount: string | number;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface ServiceFeeGeneratePayload {
  contract_group_id: string;
}

export interface ServiceFeeLedger {
  service_fee_entry_id: string;
  contract_group_id: string;
  agency_contract_id: string;
  agency_agreement_contract_id: string;
  source_ledger_ids: string[];
  year_month: string;
  amount_due: string | number;
  paid_amount: string | number;
  payment_status: LedgerPaymentStatus | string;
  currency_code: string;
  service_fee_ratio: string | number;
  calculation_base_amount: string | number;
  attributed_project_id?: string | null;
  attributed_owner_party_id?: string | null;
  attributed_operator_party_id?: string | null;
  attributed_asset_ids?: string[] | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface ServiceFeeLedgerQuery {
  contract_group_id?: string;
  project_id?: string;
}

export interface ServiceFeeSourceReconcilePayload {
  reason: string;
}

export interface ServiceFeeGenerateResult {
  created: number;
  updated: number;
  voided: number;
  source_mismatches: number;
}

export interface LedgerFollowUpUpdatePayload {
  follow_up_status?: LedgerFollowUpStatus | null;
  next_follow_up_date?: string | null;
  follow_up_note?: string | null;
}
