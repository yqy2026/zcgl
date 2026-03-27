import { describe, expect, it, vi } from 'vitest';
import { renderWithProviders, screen } from '@/test/utils/test-helpers';
import { ErrorState } from '../ErrorState';

const formatConsoleMessages = (calls: unknown[][]) =>
  calls
    .flat()
    .map(value => String(value))
    .join(' ');

describe('ErrorState', () => {
  it('does not emit antd deprecation warnings when showing technical details', () => {
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

    try {
      renderWithProviders(
        <ErrorState
          type="network"
          errorDetails="socket hang up"
          showTechnicalDetails
          primaryAction={{ text: '重试', onClick: vi.fn() }}
          secondaryAction={{ text: '返回', onClick: vi.fn() }}
        />
      );

      expect(screen.getByText('技术详情')).toBeInTheDocument();
      const messages = formatConsoleMessages(consoleErrorSpy.mock.calls);
      expect(messages).not.toContain('[antd: Space]');
      expect(messages).not.toContain('[antd: Alert]');
    } finally {
      consoleErrorSpy.mockRestore();
    }
  });
});
