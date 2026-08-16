import { describe, expect, it, vi } from 'vitest';
import { screen } from '@testing-library/react';
import { ApiError } from '@/api/config';

vi.mock('@/services/documentExtractionService', () => ({
  propertyCertificateExtractionService: {
    createSession: vi.fn(),
    confirm: vi.fn(),
    cancel: vi.fn(),
  },
}));

import { renderWithProviders } from '@/test/utils/test-helpers';
import {
  PropertyCertificateImport,
  isCertificateNumberConflict,
} from '../PropertyCertificateImport';

describe('isCertificateNumberConflict（证号重复精确判定，#78）', () => {
  it('409 + certificate_number_conflict detail 判定为证号重复', () => {
    expect(isCertificateNumberConflict(new ApiError('certificate_number_conflict', 409))).toBe(
      true
    );
  });

  it('409 + 其它 detail（如会话状态错误）不判定为证号重复', () => {
    expect(isCertificateNumberConflict(new ApiError('session_state_error', 409))).toBe(false);
  });

  it('非 409 状态码不判定为证号重复', () => {
    expect(isCertificateNumberConflict(new ApiError('certificate_number_conflict', 403))).toBe(
      false
    );
  });

  it('兼容非 ApiError 的错误对象结构（response.data.detail）', () => {
    expect(
      isCertificateNumberConflict({
        response: { status: 409, data: { detail: 'certificate_number_conflict' } },
      })
    ).toBe(true);
    expect(
      isCertificateNumberConflict({
        response: { status: 409, data: { detail: 'other' } },
      })
    ).toBe(false);
  });
});

describe('PropertyCertificateImport', () => {
  it('requires explicit asset and holder references before a new extraction session', () => {
    renderWithProviders(<PropertyCertificateImport />);

    expect(screen.getByLabelText('资产编号')).toBeInTheDocument();
    expect(screen.getByLabelText('权利人编号')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '开始解析' })).toBeInTheDocument();
  });

  it('does not render the legacy upload or automatic asset-matching workflow', () => {
    renderWithProviders(<PropertyCertificateImport />);

    expect(screen.queryByText('匹配的资产')).not.toBeInTheDocument();
    expect(screen.queryByText('确认并创建产权证')).not.toBeInTheDocument();
  });

  it('uses existing-attachment review mode when the formal attachment is referenced in the route', () => {
    renderWithProviders(<PropertyCertificateImport />, {
      route: '/property-certificates/import?certificate_id=cert-1&attachment_id=attachment-1',
    });

    expect(screen.getByRole('button', { name: '开始复核' })).toBeInTheDocument();
    expect(screen.queryByText('选择产权证 PDF、JPEG 或 PNG')).not.toBeInTheDocument();
  });

  it('guides duplicate certificate numbers into the existing-certificate linkage flow (#78)', async () => {
    const { fireEvent, waitFor } = await import('@testing-library/react');
    const { propertyCertificateExtractionService } =
      await import('@/services/documentExtractionService');
    const certificateNumber = '粤(2026)重复号';

    vi.mocked(propertyCertificateExtractionService.createSession).mockResolvedValue({
      session_id: 'session-1',
      target_type: 'property_certificate',
      status: 'ready_for_review',
      candidates: {
        fields: {
          certificate_number: {
            conflict: false,
            candidates: [
              { value: certificateNumber, value_type: 'string', confidence: 'high', evidence: [] },
            ],
          },
        },
      },
      errors: [],
    } as never);
    vi.mocked(propertyCertificateExtractionService.confirm)
      .mockRejectedValueOnce(new ApiError('certificate_number_conflict', 409))
      .mockResolvedValueOnce({ certificate_id: 'cert-1' } as never);

    // 显式 route：BrowserRouter 全局 history 不随测试重置，避免继承上一用例的 certificate_id query
    renderWithProviders(<PropertyCertificateImport />, {
      route: '/property-certificates/import',
    });
    await new Promise(resolve => setTimeout(resolve, 300));
    const uploadInput = document.querySelector('input[type="file"]');
    expect(uploadInput).not.toBeNull();
    fireEvent.change(uploadInput as Element, {
      target: {
        files: [new File(['pdf'], 'cert.pdf', { type: 'application/pdf' })],
      },
    });
    fireEvent.change(screen.getByLabelText('资产编号'), { target: { value: 'asset-1' } });
    fireEvent.click(screen.getByRole('button', { name: '开始解析' }));

    await waitFor(() => {
      expect(screen.getByText('人工复核')).toBeInTheDocument();
    });
    fireEvent.change(screen.getByLabelText('权利人编号'), { target: { value: 'party-1' } });
    fireEvent.click(screen.getByText(`使用候选：${certificateNumber}`));
    fireEvent.click(screen.getByRole('button', { name: '保存产权证' }));

    // 409 certificate_number_conflict → 维护既有产权证引导出现
    await waitFor(() => {
      expect(screen.getByText('证书编号已存在')).toBeInTheDocument();
    });
    fireEvent.change(screen.getByLabelText('已有产权证 ID'), {
      target: { value: 'cert-existing' },
    });
    fireEvent.click(screen.getByRole('button', { name: '保存产权证' }));

    await waitFor(() => {
      expect(propertyCertificateExtractionService.confirm).toHaveBeenLastCalledWith(
        'session-1',
        expect.objectContaining({
          link_existing_certificate_id: 'cert-existing',
          attach_staged: true,
        })
      );
    });
  });
});
