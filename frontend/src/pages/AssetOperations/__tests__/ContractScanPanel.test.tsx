import { expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import ContractScanPanel from '@/pages/AssetOperations/ContractScanPanel';

vi.mock('@/pages/AssetOperations/ArchiveDocumentsPanel', () => ({
  default: ({ targetId, targetType }: { targetId: string; targetType: string }) => (
    <p>
      {targetType}:{targetId}
    </p>
  ),
}));

function show(kind: 'upstream' | 'terminal') {
  render(
    <QueryClientProvider
      client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}
    >
      <ContractScanPanel kind={kind} contractId="contract-1" />
    </QueryClientProvider>
  );
}

it('mounts the archive panel with the upstream scan target', () => {
  show('upstream');
  expect(screen.getByRole('heading', { name: '合同扫描件档案' })).toBeInTheDocument();
  expect(screen.getByText('upstream_contract:contract-1')).toBeInTheDocument();
});

it('mounts the archive panel with the terminal scan target', () => {
  show('terminal');
  expect(screen.getByText('terminal_contract:contract-1')).toBeInTheDocument();
});
