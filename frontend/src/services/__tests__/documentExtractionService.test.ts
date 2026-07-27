import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('@/api/client', () => ({
  apiClient: {
    post: vi.fn(),
  },
}));

import { apiClient } from '@/api/client';
import {
  documentExtractionService,
  propertyCertificateExtractionService,
} from '../documentExtractionService';

describe('documentExtractionService', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('posts a single contract PDF with only the required extraction context', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({
      data: {
        session_id: 'session-1',
        target_type: 'contract',
        status: 'ready_for_review',
        candidates: { fields: {} },
        errors: [],
      },
    });

    await documentExtractionService.createContractSession(
      new File(['pdf'], 'contract.pdf', { type: 'application/pdf' }),
      {
        project_id: 'project-1',
        revenue_mode: 'lease',
        contract_direction: '\u51fa\u79df',
        group_relation_type: '\u4e0b\u6e38',
      }
    );

    const [path, form, requestConfig] = vi.mocked(apiClient.post).mock.calls[0] ?? [];
    expect(path).toBe('/extraction-sessions');
    expect(form).toBeInstanceOf(FormData);
    expect((form as FormData).get('target_type')).toBe('contract');
    expect((form as FormData).get('project_id')).toBe('project-1');
    expect((form as FormData).get('file')).toBeInstanceOf(File);
    expect(requestConfig).toEqual({ retry: false, timeout: 300000 });
  });

  it('confirms only explicit actions, party identifiers, and asset identifiers', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ data: { contract_id: 'contract-1' } });

    await documentExtractionService.confirm('session-1', {
      actions: [
        {
          field_key: 'contract_number',
          action: 'manual',
          value: 'C-001',
        },
      ],
      party_ids: {
        operator_party_id: 'party-1',
        owner_party_id: 'party-2',
        lessor_party_id: 'party-3',
        lessee_party_id: 'party-4',
      },
      asset_ids: ['asset-1'],
    });

    expect(apiClient.post).toHaveBeenCalledWith('/extraction-sessions/session-1/confirm', {
      actions: [{ field_key: 'contract_number', action: 'manual', value: 'C-001' }],
      party_ids: {
        operator_party_id: 'party-1',
        owner_party_id: 'party-2',
        lessor_party_id: 'party-3',
        lessee_party_id: 'party-4',
      },
      asset_ids: ['asset-1'],
    });
  });

  it('cancels through the terminal session endpoint', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ data: undefined });

    await documentExtractionService.cancel('session-1');

    expect(apiClient.post).toHaveBeenCalledWith('/extraction-sessions/session-1/cancel');
  });
  it('posts a property certificate session with only the selected asset and file', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({
      data: {
        session_id: 'certificate-session-1',
        target_type: 'property_certificate',
        status: 'ready_for_review',
        candidates: { fields: {} },
        errors: [],
      },
    });

    await propertyCertificateExtractionService.createSession(
      new File(['pdf'], 'certificate.pdf', { type: 'application/pdf' }),
      'asset-1'
    );

    const [path, form] = vi.mocked(apiClient.post).mock.calls[0] ?? [];
    expect(path).toBe('/extraction-sessions');
    expect((form as FormData).get('target_type')).toBe('property_certificate');
    expect((form as FormData).get('asset_id')).toBe('asset-1');
    expect((form as FormData).get('file')).toBeInstanceOf(File);
  });
  it('creates an existing attachment review with only asset and attachment references', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({
      data: {
        session_id: 'certificate-session-2',
        target_type: 'property_certificate',
        status: 'ready_for_review',
        candidates: { fields: {} },
        errors: [],
      },
    });

    await propertyCertificateExtractionService.createExistingSession(
      'cert-1',
      'asset-1',
      'attachment-1'
    );

    const [path, form] = vi.mocked(apiClient.post).mock.calls[0] ?? [];
    expect(path).toBe('/extraction-sessions');
    expect((form as FormData).get('target_type')).toBe('property_certificate');
    expect((form as FormData).get('asset_id')).toBe('asset-1');
    expect((form as FormData).get('certificate_id')).toBe('cert-1');
    expect((form as FormData).get('attachment_id')).toBe('attachment-1');
    expect((form as FormData).get('file')).toBeNull();
  });
  it('confirms an existing attachment review through the read-authorized certificate route', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ data: { certificate_id: 'cert-1' } });

    await propertyCertificateExtractionService.confirmExisting('session-2', {
      actions: [
        { field_key: 'certificate_number', action: 'accept_candidate', candidate_value: 'C-001' },
      ],
    });

    expect(apiClient.post).toHaveBeenCalledWith('/extraction-sessions/session-2/confirm', {
      actions: [
        { field_key: 'certificate_number', action: 'accept_candidate', candidate_value: 'C-001' },
      ],
    });
  });
});
