import { describe, expect, it, vi } from 'vitest';
import { screen } from '@testing-library/react';

vi.mock('@/services/documentExtractionService', () => ({
  propertyCertificateExtractionService: {
    createSession: vi.fn(),
    confirm: vi.fn(),
    cancel: vi.fn(),
  },
}));

import { renderWithProviders } from '@/test/utils/test-helpers';
import { PropertyCertificateImport } from '../PropertyCertificateImport';

describe('PropertyCertificateImport', () => {
  it('requires explicit asset and holder references before a new extraction session', () => {
    renderWithProviders(<PropertyCertificateImport />);

    expect(screen.getByLabelText('资产 ID')).toBeInTheDocument();
    expect(screen.getByLabelText('权利人 ID')).toBeInTheDocument();
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
});
