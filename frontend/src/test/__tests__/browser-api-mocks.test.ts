import { describe, expect, it, vi } from 'vitest';

const formatStderrWrites = (calls: unknown[][]) =>
  calls.map(call => String(call[0] ?? '')).join(' ');

describe('browser api mocks', () => {
  it('allows getComputedStyle pseudo-element calls without console noise', () => {
    const stderrWriteSpy = vi.spyOn(process.stderr, 'write').mockImplementation(() => true);
    const element = document.createElement('div');
    document.body.appendChild(element);

    try {
      const style = window.getComputedStyle(element, '::before');

      expect(style).toBeDefined();
      expect(formatStderrWrites(stderrWriteSpy.mock.calls)).not.toContain(
        "getComputedStyle() method: with pseudo-elements"
      );
    } finally {
      element.remove();
      stderrWriteSpy.mockRestore();
    }
  });
});
