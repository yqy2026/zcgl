import { vi } from 'vitest';

vi.doMock('@/mocks/server', async () => {
  await new Promise(resolve => setTimeout(resolve, 200));
  return {
    mswServer: { listen: vi.fn(), resetHandlers: vi.fn(), close: vi.fn() },
  };
});
