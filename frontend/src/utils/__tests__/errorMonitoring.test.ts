import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const runtimeEnvState = vi.hoisted(() => ({
  isProduction: false,
}));

vi.mock('@/utils/runtimeEnv', () => ({
  isProductionMode: () => runtimeEnvState.isProduction,
}));

vi.mock('@/api/config', async () => {
  const actual = await vi.importActual<typeof import('@/api/config')>('@/api/config');
  return {
    ...actual,
    createApiUrl: (path: string) => `http://test.local${path}`,
  };
});

const loadModule = async () => {
  vi.resetModules();
  return import('../errorMonitoring');
};

describe('errorMonitoring', () => {
  beforeEach(() => {
    runtimeEnvState.isProduction = false;
    delete (window as { Sentry?: unknown }).Sentry;
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllEnvs();
    vi.doUnmock('@sentry/react');
    delete (window as { Sentry?: unknown }).Sentry;
  });

  it('initializes once in development mode and registers global handlers', async () => {
    const module = await loadModule();
    const infoSpy = vi.spyOn(console, 'info').mockImplementation(() => {});
    const addListenerSpy = vi.spyOn(window, 'addEventListener');

    module.initErrorMonitoring();
    module.initErrorMonitoring();

    expect(infoSpy).toHaveBeenCalledWith(
      '[ErrorMonitoring] Running in development mode - logging to console'
    );
    expect(addListenerSpy).toHaveBeenCalledWith('unhandledrejection', expect.any(Function));
    expect(addListenerSpy).toHaveBeenCalledWith('error', expect.any(Function));
  });

  it('queues errors and flushes automatically when queue reaches threshold', async () => {
    const module = await loadModule();
    const errorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
    const infoSpy = vi.spyOn(console, 'info').mockImplementation(() => {});
    const fetchMock = vi.fn().mockResolvedValue({ ok: true });
    vi.stubGlobal('fetch', fetchMock);

    for (let i = 0; i < 9; i++) {
      module.captureException(new Error(`e-${i}`), { index: i });
    }
    expect(module.getErrorQueueSize()).toBe(9);

    module.captureException(new Error('e-9'), { index: 9 });
    await Promise.resolve();

    expect(fetchMock).toHaveBeenCalledWith('http://test.local/monitoring/errors', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: expect.stringContaining('"errors"'),
    });
    expect(module.getErrorQueueSize()).toBe(0);
    expect(errorSpy).toHaveBeenCalled();
    expect(infoSpy).toHaveBeenCalledWith('[ErrorMonitoring] Sent 10 errors to server');
  });

  it('requeues errors when flush fails', async () => {
    const module = await loadModule();
    const fetchMock = vi.fn().mockRejectedValue(new Error('network failed'));
    const errorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
    vi.stubGlobal('fetch', fetchMock);

    module.captureException(new Error('queued-1'));
    module.captureException(new Error('queued-2'));
    expect(module.getErrorQueueSize()).toBe(2);

    await module.flushErrorQueue();
    expect(module.getErrorQueueSize()).toBe(2);
    expect(errorSpy).toHaveBeenCalledWith(
      '[ErrorMonitoring] Failed to send errors:',
      expect.any(Error)
    );
  });

  it('uses Sentry APIs when Sentry exists on window', async () => {
    const module = await loadModule();
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
    const sentry = {
      captureException: vi.fn(),
      captureMessage: vi.fn(),
      setUser: vi.fn(),
      init: vi.fn(),
    };
    window.Sentry = sentry;

    const error = new Error('sentry-error');
    module.captureException(error, { page: 'dashboard' });
    module.captureMessage('warning-message', 'warning', { feature: 'asset' });
    module.setUserContext('user-1', 'u@test.local', 'tester');
    module.clearUserContext();

    expect(sentry.captureException).toHaveBeenCalledWith(error, {
      contexts: {
        custom: { page: 'dashboard' },
      },
    });
    expect(sentry.captureMessage).toHaveBeenCalledWith('warning-message', {
      level: 'warning',
      contexts: {
        custom: { feature: 'asset' },
      },
    });
    expect(sentry.setUser).toHaveBeenNthCalledWith(1, {
      id: 'user-1',
      email: 'u@test.local',
      username: 'tester',
    });
    expect(sentry.setUser).toHaveBeenNthCalledWith(2, null);
    expect(module.getErrorQueueSize()).toBe(0);
    expect(consoleErrorSpy).toHaveBeenCalledWith(
      '[ErrorMonitoring]',
      expect.objectContaining({
        message: 'sentry-error',
        context: { page: 'dashboard' },
      })
    );
  });

  it('logs non-error message to console when Sentry is unavailable', async () => {
    const module = await loadModule();
    const infoSpy = vi.spyOn(console, 'info').mockImplementation(() => {});

    module.captureMessage('plain-info', 'info', { from: 'test' });

    expect(infoSpy).toHaveBeenCalledWith('[ErrorMonitoring] [INFO]', 'plain-info', {
      from: 'test',
    });
  });

  it('initializes Sentry in production and applies sanitization hooks', async () => {
    runtimeEnvState.isProduction = true;
    vi.stubEnv('VITE_SENTRY_DSN', 'https://example.sentry.io/1');
    vi.stubEnv('VITE_APP_VERSION', '2.0.0-test');
    vi.stubEnv('MODE', 'production');
    (import.meta.env as Record<string, string>).VITE_SENTRY_DSN = 'https://example.sentry.io/1';

    const module = await loadModule();
    const infoSpy = vi.spyOn(console, 'info').mockImplementation(() => {});

    module.initErrorMonitoring();
    await Promise.resolve();
    await Promise.resolve();

    const sentryModule = (await import('@sentry/react')) as {
      default: {
        init: ReturnType<typeof vi.fn>;
      };
    };
    const initMock = sentryModule.default.init;
    expect(initMock).toHaveBeenCalledTimes(1);

    const config = initMock.mock.calls[0]?.[0] as {
      dsn: string;
      release: string;
      integrations: unknown[];
      beforeSend: (event: {
        request?: { cookies?: unknown; headers?: { authorization?: unknown } };
      }) => unknown;
      beforeBreadcrumb: (breadcrumb: { category?: string }) => unknown;
    };

    expect(config.dsn).toBe('https://example.sentry.io/1');
    expect(config.release).toBe('2.0.0-test');
    expect(config.integrations).toHaveLength(2);

    const event = {
      request: {
        cookies: 'session=abc',
        headers: {
          authorization: 'Bearer token',
        },
      },
    };
    const sanitizedEvent = config.beforeSend(event) as {
      request?: { cookies?: unknown; headers?: { authorization?: unknown } };
    };
    expect(sanitizedEvent.request?.cookies).toBeUndefined();
    expect(sanitizedEvent.request?.headers?.authorization).toBeUndefined();
    expect(config.beforeBreadcrumb({ category: 'xhr' })).toBeNull();
    expect(config.beforeBreadcrumb({ category: 'ui.click' })).toEqual({ category: 'ui.click' });
    expect(infoSpy).toHaveBeenCalledWith('[ErrorMonitoring] Sentry initialized');
  });

  it('captures unhandledrejection and error events through global handlers', async () => {
    const addListenerSpy = vi.spyOn(window, 'addEventListener');
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
    const consoleInfoSpy = vi.spyOn(console, 'info').mockImplementation(() => {});
    const module = await loadModule();
    const fetchMock = vi.fn().mockResolvedValue({ ok: true });
    vi.stubGlobal('fetch', fetchMock);

    module.initErrorMonitoring();

    const unhandledRejectionHandler = addListenerSpy.mock.calls.find(
      ([type]) => type === 'unhandledrejection'
    )?.[1] as ((event: { reason: unknown }) => void) | undefined;
    const errorHandler = addListenerSpy.mock.calls.find(([type]) => type === 'error')?.[1] as
      | ((event: { error?: Error; message: string }) => void)
      | undefined;

    expect(unhandledRejectionHandler).toBeTypeOf('function');
    expect(errorHandler).toBeTypeOf('function');

    unhandledRejectionHandler?.({ reason: 'promise failed' });
    errorHandler?.({ message: 'window crashed' });

    expect(module.getErrorQueueSize()).toBe(2);
    await module.flushErrorQueue();
    const payload = JSON.parse(fetchMock.mock.calls[0]?.[1]?.body as string) as {
      errors: Array<{ message: string; context: { type: string } }>;
    };
    expect(payload.errors[0]?.message).toBe('promise failed');
    expect(payload.errors[0]?.context.type).toBe('unhandledrejection');
    expect(payload.errors[1]?.message).toBe('window crashed');
    expect(payload.errors[1]?.context.type).toBe('uncaughterror');
    expect(consoleErrorSpy).toHaveBeenCalled();
    expect(consoleInfoSpy).toHaveBeenCalledWith(
      '[ErrorMonitoring] Running in development mode - logging to console'
    );
    expect(consoleInfoSpy).toHaveBeenCalledWith('[ErrorMonitoring] Sent 2 errors to server');
  });

  it('supports empty queue flush and no-op user context updates without Sentry', async () => {
    runtimeEnvState.isProduction = true;
    const module = await loadModule();
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

    await module.flushErrorQueue();
    expect(module.getErrorQueueSize()).toBe(0);

    module.setUserContext('no-sentry-user', 'u@example.com', 'tester');
    module.clearUserContext();
    module.captureException(new Error('production-queue-only'));

    expect(module.getErrorQueueSize()).toBe(1);
    expect(consoleErrorSpy).not.toHaveBeenCalled();
  });
});
