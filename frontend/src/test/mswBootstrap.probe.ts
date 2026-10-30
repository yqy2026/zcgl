import { expect, it } from 'vitest';

it('loads MSW outside the hook budget and listens before assertions', async () => {
  const { mswServer } = await import('@/mocks/server');
  expect(mswServer.listen).toHaveBeenCalledExactlyOnceWith({ onUnhandledRequest: 'warn' });
});
