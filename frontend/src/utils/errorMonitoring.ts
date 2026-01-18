/**
 * Error Monitoring Service
 *
 * Provides error tracking and reporting capabilities.
 * Integrates with Sentry in production, falls back to console logging in development.
 */

interface ErrorContext {
  component?: string
  action?: string
  route?: string
  userId?: string
  [key: string]: unknown
}

interface ErrorReport {
  message: string
  stack?: string
  context: ErrorContext
  timestamp: string
  userAgent: string
  url: string
}

// Error queue for offline/batch reporting
let errorQueue: ErrorReport[] = []
let isInitialized = false

/**
 * Initialize error monitoring service
 */
export function initErrorMonitoring(): void {
  if (isInitialized) {
    return
  }

  // Initialize Sentry if DSN is configured
  if (import.meta.env.VITE_SENTRY_DSN && process.env.NODE_ENV === 'production') {
    initSentry()
  } else {
    console.info('[ErrorMonitoring] Running in development mode - logging to console')
  }

  isInitialized = true

  // Set up global error handlers
  setupGlobalErrorHandlers()
}

/**
 * Initialize Sentry SDK
 */
async function initSentry(): Promise<void> {
  // Dynamic import for optional Sentry dependency
  try {
    const SentryModule = await import('@sentry/react')
    const Sentry = SentryModule.default || SentryModule

    // Type-safe access to Sentry integrations
    const BrowserTracing = (SentryModule as { BrowserTracing?: unknown }).BrowserTracing
    const Replay = (SentryModule as { Replay?: unknown }).Replay

    const integrations: unknown[] = []
    if (BrowserTracing) {
      integrations.push(new (BrowserTracing as new () => unknown)())
    }
    if (Replay) {
      integrations.push(new (Replay as new () => unknown)())
    }

    Sentry.init({
      dsn: import.meta.env.VITE_SENTRY_DSN,
      environment: import.meta.env.MODE,
      release: import.meta.env.VITE_APP_VERSION || '1.0.0',
      integrations: integrations as [],
      tracesSampleRate: 0.1, // 10% of transactions for tracing
      replaysSessionSampleRate: 0.1, // 10% of sessions for replay
      replaysOnErrorSampleRate: 1.0, // 100% of sessions with errors for replay
      beforeSend(event: unknown) {
        // Filter sensitive information
        if (event && typeof event === 'object' && 'request' in event) {
          const req = event as { request: { cookies?: unknown; headers?: { authorization?: unknown } } }
          if (req.request) {
            delete req.request.cookies
            if (req.request.headers) {
              delete req.request.headers.authorization
            }
          }
        }
        return event
      },
      beforeBreadcrumb(breadcrumb: unknown) {
        // Filter sensitive breadcrumbs
        if (breadcrumb && typeof breadcrumb === 'object' && 'category' in breadcrumb) {
          const bc = breadcrumb as { category: string }
          if (bc.category === 'xhr' || bc.category === 'fetch') {
            return null // Don't log API calls
          }
        }
        return breadcrumb
      },
    })
    console.info('[ErrorMonitoring] Sentry initialized')
  } catch (error) {
    // Sentry not installed or failed to load
    // eslint-disable-next-line no-console
    console.warn('[ErrorMonitoring] Sentry not available:', error instanceof Error ? error.message : String(error))
  }
}

/**
 * Set up global error handlers for unhandled errors
 */
function setupGlobalErrorHandlers(): void {
  // Catch unhandled promise rejections
  window.addEventListener('unhandledrejection', event => {
    // eslint-disable-next-line no-console
    console.error('[ErrorMonitoring] Unhandled Promise Rejection:', event.reason)
    captureException(
      event.reason instanceof Error ? event.reason : new Error(String(event.reason)),
      { type: 'unhandledrejection' }
    )
  })

  // Catch uncaught errors
  window.addEventListener('error', event => {
    // eslint-disable-next-line no-console
    console.error('[ErrorMonitoring] Uncaught Error:', event.error)
    captureException(
      event.error ?? new Error(event.message),
      { type: 'uncaughterror' }
    )
  })
}

/**
 * Capture and report an error
 */
export function captureException(error: Error, context: ErrorContext = {}): void {
  const errorReport: ErrorReport = {
    message: error.message,
    stack: error.stack,
    context,
    timestamp: new Date().toISOString(),
    userAgent: navigator.userAgent,
    url: window.location.href,
  }

  // Log to console in development
  if (process.env.NODE_ENV !== 'production') {
    // eslint-disable-next-line no-console
    console.error('[ErrorMonitoring]', errorReport)
  }

  // Send to Sentry if available
  if (window.Sentry) {
    window.Sentry.captureException(error, {
      contexts: {
        custom: context,
      },
    })
  } else {
    // Queue for batch reporting
    errorQueue.push(errorReport)
    if (errorQueue.length >= 10) {
      flushErrorQueue()
    }
  }
}

/**
 * Capture a message (non-error event)
 */
export function captureMessage(message: string, level: 'info' | 'warning' = 'info', context: ErrorContext = {}): void {
  if (window.Sentry) {
    window.Sentry.captureMessage(message, {
      level,
      contexts: {
        custom: context,
      },
    })
  } else {
    console.info(`[ErrorMonitoring] [${level.toUpperCase()}]`, message, context)
  }
}

/**
 * Set user context for error tracking
 */
export function setUserContext(userId: string, email?: string, username?: string): void {
  if (window.Sentry) {
    window.Sentry.setUser({
      id: userId,
      email,
      username,
    })
  }
}

/**
 * Clear user context
 */
export function clearUserContext(): void {
  if (window.Sentry) {
    window.Sentry.setUser(null)
  }
}

/**
 * Flush error queue to server (for custom error reporting)
 */
export async function flushErrorQueue(): Promise<void> {
  if (errorQueue.length === 0) {
    return
  }

  const errorsToSend = [...errorQueue]
  errorQueue = []

  try {
    // Send to custom error reporting endpoint
    await fetch('/api/v1/monitoring/errors', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ errors: errorsToSend }),
    })
    console.info(`[ErrorMonitoring] Sent ${errorsToSend.length} errors to server`)
  } catch (error) {
    // eslint-disable-next-line no-console
    console.error('[ErrorMonitoring] Failed to send errors:', error)
    // Re-queue for retry
    errorQueue.unshift(...errorsToSend)
  }
}

/**
 * Get error queue size
 */
export function getErrorQueueSize(): number {
  return errorQueue.length
}

// Type declarations for Sentry
declare global {
  interface Window {
    Sentry?: {
      captureException(error: Error, context?: unknown): void
      captureMessage(message: string, context?: unknown): void
      setUser(user: null | { id: string; email?: string; username?: string }): void
      init(config: unknown): void
    }
  }
}

export default {
  initErrorMonitoring,
  captureException,
  captureMessage,
  setUserContext,
  clearUserContext,
  flushErrorQueue,
  getErrorQueueSize,
}
