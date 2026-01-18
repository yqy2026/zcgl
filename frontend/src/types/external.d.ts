/**
 * Type declarations for optional external dependencies
 */

declare module '@sentry/react' {
  // eslint-disable-next-line @typescript-eslint/no-empty-object-type
  interface BrowserTracingOptions {
    // Add options as needed
  }

  // eslint-disable-next-line @typescript-eslint/no-empty-object-type
  interface ReplayOptions {
    // Add options as needed
  }

  // eslint-disable-next-line @typescript-eslint/no-empty-object-type, @typescript-eslint/no-unsafe-declaration-merging
  interface BrowserTracing {
    new (): unknown;
  }

  // eslint-disable-next-line @typescript-eslint/no-empty-object-type, @typescript-eslint/no-unsafe-declaration-merging
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

  // eslint-disable-next-line @typescript-eslint/no-unsafe-declaration-merging
  export class BrowserTracing implements BrowserTracingOptions {}
  // eslint-disable-next-line @typescript-eslint/no-unsafe-declaration-merging
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
