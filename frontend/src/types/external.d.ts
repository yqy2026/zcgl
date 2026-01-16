/**
 * Type declarations for optional external dependencies
 */

declare module '@sentry/react' {
  interface BrowserTracingOptions {
    // Add options as needed
  }

  interface ReplayOptions {
    // Add options as needed
  }

  interface BrowserTracing {
    new (): unknown;
  }

  interface Replay {
    new (): unknown;
  }

  interface SentryInitOptions {
    dsn?: string;
    environment?: string;
    release?: string;
    integrations?: unknown[];
    tracesSampleRate?: number;
    replaysSessionSampleRate?: number;
    replaysOnErrorSampleRate?: number;
    beforeSend?: (event: unknown) => unknown;
    beforeBreadcrumb?: (breadcrumb: unknown) => unknown;
  }

  interface SentryCaptureOptions {
    contexts?: {
      custom?: Record<string, unknown>;
    };
    level?: string;
  }

  interface SentryUser {
    id?: string;
    email?: string;
    username?: string;
  }

  export class BrowserTracing implements BrowserTracingOptions {}
  export class Replay implements ReplayOptions {}

  export interface SentryType {
    init: (options: SentryInitOptions) => void;
    captureException: (error: Error, options?: SentryCaptureOptions) => void;
    captureMessage: (message: string, options?: SentryCaptureOptions) => void;
    setUser: (user: SentryUser | null) => void;
    BrowserTracing: typeof BrowserTracing;
    Replay: typeof Replay;
  }

  const Sentry: SentryType;
  export default Sentry;
}
