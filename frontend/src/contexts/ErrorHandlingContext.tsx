/**
 * Error Handling Context
 *
 * Provides global error retry functionality for the application.
 */

import React, { createContext, useContext, useState, useCallback, ReactNode } from 'react';

interface RetryAction {
  id: string;
  fn: () => Promise<void>;
  description: string;
  retryCount?: number;
}

interface ErrorHandlingContextValue {
  retryActions: Map<string, RetryAction>;
  registerRetry: (id: string, fn: () => Promise<void>, description: string) => void;
  executeRetry: (id: string) => Promise<void>;
  clearRetry: (id: string) => void;
  clearAllRetries: () => void;
}

const ErrorHandlingContext = createContext<ErrorHandlingContextValue | null>(null);

interface ErrorHandlingProviderProps {
  children: ReactNode;
}

export function ErrorHandlingProvider({ children }: ErrorHandlingProviderProps) {
  const [retryActions, setRetryActions] = useState(new Map<string, RetryAction>());

  const registerRetry = useCallback((id: string, fn: () => Promise<void>, description: string) => {
    setRetryActions(prev => {
      const next = new Map(prev);
      next.set(id, { id, fn, description, retryCount: 0 });
      return next;
    });
  }, []);

  const executeRetry = useCallback(
    async (id: string) => {
      const action = retryActions.get(id);
      if (!action) {
        // eslint-disable-next-line no-console
        console.warn(`[ErrorHandlingContext] No retry action found for id: ${id}`);
        return;
      }

      try {
        // eslint-disable-next-line no-console
        console.log(`[ErrorHandlingContext] Executing retry for: ${action.description}`);
        await action.fn();

        // Increment retry count
        setRetryActions(prev => {
          const next = new Map(prev);
          const existing = next.get(id);
          if (existing) {
            next.set(id, { ...existing, retryCount: (existing.retryCount ?? 0) + 1 });
          }
          return next;
        });

        // eslint-disable-next-line no-console
        console.log(`[ErrorHandlingContext] Retry successful for: ${action.description}`);
      } catch (error) {
        // eslint-disable-next-line no-console
        console.error(`[ErrorHandlingContext] Retry failed for: ${action.description}`, error);
        throw error; // Re-throw to allow caller to handle
      }
    },
    [retryActions]
  );

  const clearRetry = useCallback((id: string) => {
    setRetryActions(prev => {
      const next = new Map(prev);
      next.delete(id);
      return next;
    });
  }, []);

  const clearAllRetries = useCallback(() => {
    setRetryActions(new Map());
  }, []);

  const value: ErrorHandlingContextValue = {
    retryActions,
    registerRetry,
    executeRetry,
    clearRetry,
    clearAllRetries,
  };

  return <ErrorHandlingContext.Provider value={value}>{children}</ErrorHandlingContext.Provider>;
}

export function useErrorHandling(): ErrorHandlingContextValue {
  const context = useContext(ErrorHandlingContext);
  if (!context) {
    throw new Error('useErrorHandling must be used within ErrorHandlingProvider');
  }
  return context;
}

export default ErrorHandlingProvider;
