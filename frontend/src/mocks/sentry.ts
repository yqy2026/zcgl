/**
 * Mock for @sentry/react (optional production dependency)
 *
 * This mock is used during tests to avoid requiring the @sentry/react package,
 * which is an optional dependency for production error monitoring.
 */

import { vi } from 'vitest';

// Mock default export - main Sentry SDK
const defaultSentry = {
  init: vi.fn(() => ({})),
  captureException: vi.fn(() => 'test-event-id'),
  captureMessage: vi.fn(() => 'test-message-id'),
  configureScope: vi.fn(),
  addBreadcrumb: vi.fn(),
  setUser: vi.fn(),
  setTag: vi.fn(),
  setContext: vi.fn(),
  setExtras: vi.fn(),
  withScope: vi.fn(),
  startTransaction: vi.fn(() => ({
    startChild: vi.fn(() => ({})),
    finish: vi.fn(),
    toObject: vi.fn(() => ({})),
  })),
  finishTransaction: vi.fn(),
  flush: vi.fn(() => Promise.resolve(true)),
  close: vi.fn(() => Promise.resolve(true)),
};

// Mock named exports for integrations
class BrowserTracing {}
class Replay {}
const integrations: unknown[] = [];

// Export default
export default defaultSentry;

// Export named exports
export { BrowserTracing, Replay, integrations };

// Re-export default as named export for compatibility
export { default as Sentry } from './sentry';
