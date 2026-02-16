import React from 'react';
import { act, render, renderHook, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const runtimeEnvState = vi.hoisted(() => ({
  isDevelopment: true,
}));

vi.mock('@/utils/runtimeEnv', () => ({
  isDevelopmentMode: () => runtimeEnvState.isDevelopment,
}));

import {
  preloadResource,
  preloadResources,
  useBatchUpdate,
  useCache,
  useDebounce,
  useMemoryLeakDetection,
  useRenderPerformance,
  useThrottle,
  useVirtualScroll,
  useWebWorker,
  withPerformanceMonitoring,
} from '../optimization';

describe('optimization utils', () => {
  beforeEach(() => {
    runtimeEnvState.isDevelopment = true;
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('useDebounce triggers callback once after delay', () => {
    vi.useFakeTimers();
    const callback = vi.fn();
    const { result } = renderHook(() => useDebounce(callback, 100));

    act(() => {
      result.current('first');
      result.current('second');
    });

    expect(callback).not.toHaveBeenCalled();

    vi.advanceTimersByTime(100);

    expect(callback).toHaveBeenCalledTimes(1);
    expect(callback).toHaveBeenCalledWith('second');
  });

  it('useThrottle throttles calls within delay window', () => {
    const callback = vi.fn();
    const nowSpy = vi.spyOn(Date, 'now');
    nowSpy.mockReturnValueOnce(101);
    nowSpy.mockReturnValueOnce(150);
    nowSpy.mockReturnValueOnce(220);

    const { result } = renderHook(() => useThrottle(callback, 100));

    act(() => {
      result.current('a');
      result.current('b');
      result.current('c');
    });

    expect(callback).toHaveBeenCalledTimes(2);
    expect(callback).toHaveBeenNthCalledWith(1, 'a');
    expect(callback).toHaveBeenNthCalledWith(2, 'c');
  });

  it('useVirtualScroll computes range and responds to scroll', () => {
    const items = Array.from({ length: 20 }, (_, i) => i);
    const { result } = renderHook(() => useVirtualScroll(items, 10, 30));

    expect(result.current.startIndex).toBe(0);
    expect(result.current.endIndex).toBe(4);
    expect(result.current.items).toEqual([0, 1, 2, 3]);

    act(() => {
      result.current.handleScroll({
        currentTarget: { scrollTop: 25 },
      } as React.UIEvent<HTMLDivElement>);
    });

    expect(result.current.startIndex).toBe(2);
    expect(result.current.endIndex).toBe(6);
    expect(result.current.offsetY).toBe(20);
    expect(result.current.items).toEqual([2, 3, 4, 5]);
  });

  it('useCache reuses cached value until deps change', () => {
    const factory = vi.fn(() => ({ id: Math.random() }));

    const { result, rerender } = renderHook(
      ({ dep }) => {
        return useCache('asset-cache', factory, [dep]);
      },
      {
        initialProps: { dep: 1 },
      }
    );

    const first = result.current;

    rerender({ dep: 1 });
    expect(result.current).toBe(first);
    expect(factory).toHaveBeenCalledTimes(1);

    rerender({ dep: 2 });
    expect(factory).toHaveBeenCalledTimes(2);
    expect(result.current).not.toBe(first);
  });

  it('useBatchUpdate merges queued updates into a single flush', () => {
    vi.useFakeTimers();
    const { result } = renderHook(() => useBatchUpdate(0));

    act(() => {
      result.current[1](prev => prev + 1);
      result.current[1](prev => prev + 2);
    });

    expect(result.current[0]).toBe(0);

    act(() => {
      vi.runAllTimers();
    });

    expect(result.current[0]).toBe(3);
  });

  it('useWebWorker handles message, error, and cleanup', async () => {
    const workerInstances: Array<{
      onerror: ((event: { message: string }) => void) | null;
      onmessage: ((event: { data: unknown }) => void) | null;
      postMessage: ReturnType<typeof vi.fn>;
      terminate: ReturnType<typeof vi.fn>;
    }> = [];

    class WorkerMock {
      onerror: ((event: { message: string }) => void) | null = null;
      onmessage: ((event: { data: unknown }) => void) | null = null;
      postMessage = vi.fn((data: unknown) => {
        this.onmessage?.({ data: { echoed: data } });
      });
      terminate = vi.fn();

      constructor(_script: string) {
        workerInstances.push(this);
      }
    }

    vi.stubGlobal('Worker', WorkerMock as unknown as typeof Worker);

    const { result, unmount } = renderHook(() => useWebWorker('/worker.js'));
    const messageCallback = vi.fn();

    act(() => {
      result.current.onMessage(messageCallback);
      result.current.postMessage({ id: 1 });
    });

    await waitFor(() => {
      expect(messageCallback).toHaveBeenCalledWith({ echoed: { id: 1 } });
    });
    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    act(() => {
      workerInstances[0]?.onerror?.({ message: 'worker failed' });
    });

    await waitFor(() => {
      expect(result.current.error?.message).toBe('worker failed');
    });

    unmount();
    expect(workerInstances[0]?.terminate).toHaveBeenCalledTimes(1);
  });

  it('preloadResource supports script/style/image and errors', async () => {
    const appendSpy = vi.spyOn(document.head, 'appendChild');
    const createSpy = vi.spyOn(document, 'createElement');

    const scriptPromise = preloadResource('/bundle.js', 'script');
    const scriptElement = appendSpy.mock.calls[0]?.[0] as HTMLScriptElement;
    scriptElement.onload?.(new Event('load'));
    await expect(scriptPromise).resolves.toBe(scriptElement);

    const stylePromise = preloadResource('/app.css', 'style');
    const styleElement = appendSpy.mock.calls[1]?.[0] as HTMLLinkElement;
    styleElement.onload?.(new Event('load'));
    await expect(stylePromise).resolves.toBe(styleElement);

    const imagePromise = preloadResource('/logo.png', 'image');
    const imageElement = createSpy.mock.results
      .map(entry => entry.value)
      .find(
        value =>
          value instanceof HTMLImageElement ||
          (value as HTMLElement).tagName?.toLowerCase() === 'img'
      ) as HTMLImageElement;
    imageElement.onload?.(new Event('load'));
    await expect(imagePromise).resolves.toBe(imageElement);

    const errorPromise = preloadResource('/broken.css', 'style');
    const errorElement = appendSpy.mock.calls[2]?.[0] as HTMLLinkElement;
    errorElement.onerror?.(new Event('error') as Event & string);
    await expect(errorPromise).rejects.toBeDefined();
  });

  it('preloadResources returns allSettled results', async () => {
    const appendSpy = vi.spyOn(document.head, 'appendChild');

    const resultsPromise = preloadResources([
      { url: '/ok.js', type: 'script' },
      { url: '/bad.css', type: 'style' },
    ]);

    const scriptElement = appendSpy.mock.calls[0]?.[0] as HTMLScriptElement;
    const styleElement = appendSpy.mock.calls[1]?.[0] as HTMLLinkElement;

    scriptElement.onload?.(new Event('load'));
    styleElement.onerror?.(new Event('error') as Event & string);

    const results = await resultsPromise;

    expect(results[0]?.status).toBe('fulfilled');
    expect(results[1]?.status).toBe('rejected');
  });

  it('useMemoryLeakDetection cleans listeners on unmount', () => {
    vi.useFakeTimers();
    const addListenerSpy = vi.spyOn(window, 'addEventListener');
    const removeListenerSpy = vi.spyOn(window, 'removeEventListener');
    const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});

    const { result, unmount } = renderHook(() => useMemoryLeakDetection('LeakComp'));
    const listener = vi.fn() as unknown as EventListener;

    act(() => {
      result.current.addTimer(setTimeout(() => {}, 1000) as unknown as NodeJS.Timeout);
      result.current.addInterval(setInterval(() => {}, 1000) as unknown as NodeJS.Timeout);
      result.current.addListener('click', listener);
    });

    expect(addListenerSpy).toHaveBeenCalledWith('click', listener);

    unmount();

    expect(removeListenerSpy).toHaveBeenCalledWith('click', listener);
    expect(warnSpy).toHaveBeenCalledWith(expect.stringContaining('Component LeakComp had'));
  });

  it('useRenderPerformance warns when render interval is slow in development', async () => {
    runtimeEnvState.isDevelopment = true;
    const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
    let tick = 0;
    vi.spyOn(performance, 'now').mockImplementation(() => {
      tick += 40;
      return tick;
    });

    const { rerender } = renderHook(() => useRenderPerformance('RenderComp'));
    rerender();
    rerender();

    await waitFor(() => {
      expect(warnSpy).toHaveBeenCalledWith(
        expect.stringContaining('Slow render detected in RenderComp')
      );
    });
  });

  it('withPerformanceMonitoring wraps component and exposes displayName', () => {
    const Base = ({ text }: { text: string }) => <div data-testid="base">{text}</div>;
    const Wrapped = withPerformanceMonitoring(Base, 'Base');

    render(<Wrapped text="hello" />);

    expect(screen.getByTestId('base')).toHaveTextContent('hello');
    expect(Wrapped.displayName).toBe('withPerformanceMonitoring(Base)');
  });
});
