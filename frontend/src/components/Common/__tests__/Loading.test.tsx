import { describe, expect, it, vi } from 'vitest';
import { renderWithProviders } from '@/test/utils/test-helpers';
import { SkeletonLoading } from '../Loading';

const formatConsoleMessages = (calls: unknown[][]) =>
  calls
    .flat()
    .map(value => String(value))
    .join(' ');

describe('Loading', () => {
  it('does not emit antd space deprecation warnings for skeleton variants', () => {
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

    try {
      renderWithProviders(<SkeletonLoading type="card" count={2} />);

      expect(formatConsoleMessages(consoleErrorSpy.mock.calls)).not.toContain('[antd: Space]');
    } finally {
      consoleErrorSpy.mockRestore();
    }
  });
});
