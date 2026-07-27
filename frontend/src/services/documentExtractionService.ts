import { apiClient } from '@/api/client';

const EXTRACTION_SESSION_TIMEOUT_MS = 300_000;

export type ExtractionAction =
  | 'accept_candidate'
  | 'correct_candidate'
  | 'manual'
  | 'clear_optional'
  | 'keep_existing';

export interface ExtractionCandidate {
  value: string;
  value_type: 'string' | 'date' | 'decimal';
  confidence: 'high' | 'medium' | 'low';
  evidence: Array<{ page_number: number; text: string }>;
}

export interface ExtractionField {
  conflict: boolean;
  candidates: ExtractionCandidate[];
}

export interface ExtractionSession {
  session_id: string;
  target_type: 'contract' | 'property_certificate';
  status: 'ready_for_review';
  candidates: { fields: Record<string, ExtractionField> };
  errors: string[];
}

export interface ContractPartyIds {
  operator_party_id: string;
  owner_party_id: string;
  lessor_party_id: string;
  lessee_party_id: string;
}

export interface ExtractionConfirmPayload {
  actions: Array<{
    field_key: string;
    action: ExtractionAction;
    candidate_value?: string;
    value?: string;
  }>;
  party_ids: ContractPartyIds;
  asset_ids: string[];
}

export type ExtractionContractDirection = '\u51fa\u79df' | '\u627f\u79df';
export type ExtractionGroupRelationType =
  | '\u4e0a\u6e38'
  | '\u4e0b\u6e38'
  | '\u59d4\u6258'
  | '\u76f4\u79df';

export interface ExtractionUploadContext {
  project_id: string;
  revenue_mode: 'lease' | 'agency';
  contract_direction: ExtractionContractDirection;
  group_relation_type: ExtractionGroupRelationType;
}

export const documentExtractionService = {
  async createContractSession(
    file: File,
    context: ExtractionUploadContext
  ): Promise<ExtractionSession> {
    const form = new FormData();
    form.append('file', file);
    form.append('target_type', 'contract');
    form.append('project_id', context.project_id);
    form.append('revenue_mode', context.revenue_mode);
    form.append('contract_direction', context.contract_direction);
    form.append('group_relation_type', context.group_relation_type);
    const response = await apiClient.post<ExtractionSession>('/extraction-sessions', form, {
      retry: false,
      timeout: EXTRACTION_SESSION_TIMEOUT_MS,
    });
    if (response.data == null) {
      throw new Error('Empty extraction session response');
    }
    return response.data;
  },

  async confirm(
    sessionId: string,
    payload: ExtractionConfirmPayload
  ): Promise<{ contract_id: string }> {
    const response = await apiClient.post<{ contract_id: string }>(
      `/extraction-sessions/${sessionId}/confirm`,
      payload
    );
    if (response.data == null) {
      throw new Error('Empty contract confirmation response');
    }
    return response.data;
  },

  async cancel(sessionId: string): Promise<void> {
    await apiClient.post(`/extraction-sessions/${sessionId}/cancel`);
  },
};
export interface PropertyCertificateExtractionConfirmPayload {
  actions: ExtractionConfirmPayload['actions'];
  certificate_type: 'real_estate' | 'house_ownership' | 'land_use' | 'other';
  holder_party_ids: string[];
  link_existing_certificate_id?: string;
  attach_staged: boolean;
}

export interface PropertyCertificateExistingExtractionConfirmPayload {
  actions: ExtractionConfirmPayload['actions'];
}

export const propertyCertificateExtractionService = {
  async createSession(file: File, assetId: string): Promise<ExtractionSession> {
    const form = new FormData();
    form.append('target_type', 'property_certificate');
    form.append('file', file);
    form.append('asset_id', assetId);
    const response = await apiClient.post<ExtractionSession>('/extraction-sessions', form);
    if (response.data == null) {
      throw new Error('Empty property certificate extraction session response');
    }
    return response.data;
  },

  async createExistingSession(
    certificateId: string,
    assetId: string,
    attachmentId: string
  ): Promise<ExtractionSession> {
    const form = new FormData();
    form.append('target_type', 'property_certificate');
    form.append('asset_id', assetId);
    form.append('certificate_id', certificateId);
    form.append('attachment_id', attachmentId);
    const response = await apiClient.post<ExtractionSession>('/extraction-sessions', form);
    if (response.data == null) {
      throw new Error('Empty existing property certificate review response');
    }
    return response.data;
  },

  async confirm(
    sessionId: string,
    payload: PropertyCertificateExtractionConfirmPayload
  ): Promise<{ certificate_id: string }> {
    const response = await apiClient.post<{ certificate_id: string }>(
      `/extraction-sessions/${sessionId}/confirm`,
      payload
    );
    if (response.data == null) {
      throw new Error('Empty property certificate confirmation response');
    }
    return response.data;
  },

  async confirmExisting(
    sessionId: string,
    payload: PropertyCertificateExistingExtractionConfirmPayload
  ): Promise<{ certificate_id: string }> {
    const response = await apiClient.post<{ certificate_id: string }>(
      `/extraction-sessions/${sessionId}/confirm`,
      payload
    );
    if (response.data == null) {
      throw new Error('Empty existing property certificate confirmation response');
    }
    return response.data;
  },

  async cancel(sessionId: string): Promise<void> {
    await apiClient.post(`/extraction-sessions/${sessionId}/cancel`);
  },
};
