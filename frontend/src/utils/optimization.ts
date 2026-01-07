// 前端性能优化工具

import React, { useCallback, useMemo, useRef, useEffect, useState } from 'react';

// 防抖Hook
export const useDebounce = <T extends (...args: unknown[]) => unknown>(
  callback: T,
  delay: number
): T => {
  const timeoutRef = useRef<NodeJS.Timeout>();

  return useCallback(
    (...args: Parameters<T>) => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }

      timeoutRef.current = setTimeout(() => {
        callback(...args);
      }, delay);
    },
    [callback, delay]
  ) as T;
};

// 节流Hook
export const useThrottle = <T extends (...args: unknown[]) => unknown>(
  callback: T,
  delay: number
): T => {
  const lastCallRef = useRef<number>(0);

  return useCallback(
    (...args: Parameters<T>) => {
      const now = Date.now();
      if (now - lastCallRef.current >= delay) {
        lastCallRef.current = now;
        callback(...args);
      }
    },
    [callback, delay]
  ) as T;
};

// 虚拟滚动Hook
export const useVirtualScroll = <T>(items: T[], itemHeight: number, containerHeight: number) => {
  const [scrollTop, setScrollTop] = useState(0);

  const visibleItems = useMemo(() => {
    const startIndex = Math.floor(scrollTop / itemHeight);
    const endIndex = Math.min(
      startIndex + Math.ceil(containerHeight / itemHeight) + 1,
      items.length
    );

    return {
      startIndex,
      endIndex,
      items: items.slice(startIndex, endIndex),
      totalHeight: items.length * itemHeight,
      offsetY: startIndex * itemHeight,
    };
  }, [items, itemHeight, containerHeight, scrollTop]);

  const handleScroll = useCallback((e: React.UIEvent<HTMLDivElement>) => {
    setScrollTop(e.currentTarget.scrollTop);
  }, []);

  return {
    ...visibleItems,
    handleScroll,
  };
};

// 图片懒加载Hook
export const useLazyImage = (src: string, options?: IntersectionObserverInit) => {
  const [imageSrc, setImageSrc] = useState<string>();
  const [isLoaded, setIsLoaded] = useState(false);
  const [isError, setIsError] = useState(false);
  const imgRef = useRef<HTMLImageElement>(null);

  useEffect(() => {
    const observer = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) {
        setImageSrc(src);
        observer.disconnect();
      }
    }, options);

    if (imgRef.current) {
      observer.observe(imgRef.current);
    }

    return () => observer.disconnect();
  }, [src, options]);

  const handleLoad = useCallback(() => {
    setIsLoaded(true);
  }, []);

  const handleError = useCallback(() => {
    setIsError(true);
  }, []);

  return {
    imgRef,
    imageSrc,
    isLoaded,
    isError,
    handleLoad,
    handleError,
  };
};

// 内存泄漏检测
export const useMemoryLeakDetection = (componentName: string) => {
  const mountTimeRef = useRef<number>();
  const timersRef = useRef<Set<NodeJS.Timeout>>(new Set());
  const intervalsRef = useRef<Set<NodeJS.Timeout>>(new Set());
  const listenersRef = useRef<Map<string, EventListener>>(new Map());

  useEffect(() => {
    mountTimeRef.current = Date.now();

    return () => {
      const unmountTime = Date.now();
      const _lifeTime = unmountTime - (mountTimeRef.current ?? 0);

      // 清理定时器 - capture ref values to avoid stale closure issues
      const timers = timersRef.current;
      const intervals = intervalsRef.current;
      const listeners = listenersRef.current;

      timers.forEach(timer => clearTimeout(timer));
      intervals.forEach(interval => clearInterval(interval));

      // 清理事件监听器
      listeners.forEach((listener, event) => {
        window.removeEventListener(event, listener);
      });

      // 在开发环境下记录组件生命周期
      if (process.env.NODE_ENV === 'development') {
        // Component unmounted

        if (timers.size > 0) {
          console.warn(`Component ${componentName} had ${timers.size} uncleaned timers`);
        }

        if (listeners.size > 0) {
          console.warn(`Component ${componentName} had ${listeners.size} uncleaned listeners`);
        }
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [componentName]);

  const addTimer = useCallback((timer: NodeJS.Timeout) => {
    timersRef.current.add(timer);
    return timer;
  }, []);

  const addInterval = useCallback((interval: NodeJS.Timeout) => {
    intervalsRef.current.add(interval);
    return interval;
  }, []);

  const addListener = useCallback((event: string, listener: EventListener) => {
    listenersRef.current.set(event, listener);
    window.addEventListener(event, listener);
  }, []);

  return {
    addTimer,
    addInterval,
    addListener,
  };
};

// 组件渲染性能监控
export const useRenderPerformance = (componentName: string) => {
  const renderCountRef = useRef(0);
  const lastRenderTimeRef = useRef<number>();

  useEffect(() => {
    renderCountRef.current++;
    const now = performance.now();

    if (lastRenderTimeRef.current !== null && lastRenderTimeRef.current !== undefined) {
      const renderTime = now - lastRenderTimeRef.current;

      if (process.env.NODE_ENV === 'development' && renderTime > 16) {
        console.warn(`Slow render detected in ${componentName}: ${renderTime.toFixed(2)}ms`);
      }
    }

    lastRenderTimeRef.current = now;
  });

  useEffect(() => {
    return () => {
      if (process.env.NODE_ENV === 'development') {
        // Component rendered
      }
    };
  }, [componentName]);

  return renderCountRef.current;
};

// 缓存Hook
export const useCache = <T>(key: string, factory: () => T, deps: unknown[] = []): T => {
  const cache = useRef<Map<string, T>>(new Map());

  // Convert deps to a stable string for dependency tracking
  // We use a stable key based on the deps array
  const depsKey = useMemo(() => {
    return JSON.stringify(deps);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  const cacheKey = `${key}_${depsKey}`;

  return useMemo(() => {
    if (cache.current.has(cacheKey)) {
      return cache.current.get(cacheKey)!;
    }

    const value = factory();
    cache.current.set(cacheKey, value);

    // 限制缓存大小
    if (cache.current.size > 100) {
      const firstKey = cache.current.keys().next().value;
      if (firstKey !== null && firstKey !== undefined) {
        cache.current.delete(firstKey);
      }
    }

    return value;
  }, [cacheKey, factory]);
};

// 批量更新Hook
export const useBatchUpdate = <T>(initialValue: T) => {
  const [value, setValue] = useState(initialValue);
  const pendingUpdatesRef = useRef<Array<(prev: T) => T>>([]);
  const timeoutRef = useRef<NodeJS.Timeout>();

  const batchUpdate = useCallback((updater: (prev: T) => T) => {
    pendingUpdatesRef.current.push(updater);

    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }

    timeoutRef.current = setTimeout(() => {
      setValue(prev => {
        return pendingUpdatesRef.current.reduce((acc, update) => update(acc), prev);
      });
      pendingUpdatesRef.current = [];
    }, 0);
  }, []);

  return [value, batchUpdate] as const;
};

// Web Worker Hook
export const useWebWorker = (workerScript: string) => {
  const workerRef = useRef<Worker>();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error>();

  useEffect(() => {
    try {
      workerRef.current = new Worker(workerScript);

      workerRef.current.onerror = error => {
        setError(new Error(error.message));
        setIsLoading(false);
      };

      return () => {
        workerRef.current?.terminate();
      };
    } catch (error) {
      setError(error as Error);
    }
  }, [workerScript]);

  const postMessage = useCallback((data: unknown) => {
    if (workerRef.current) {
      setIsLoading(true);
      setError(undefined);
      workerRef.current.postMessage(data);
    }
  }, []);

  const onMessage = useCallback((callback: (data: unknown) => void) => {
    if (workerRef.current) {
      workerRef.current.onmessage = event => {
        setIsLoading(false);
        callback(event.data);
      };
    }
  }, []);

  return {
    postMessage,
    onMessage,
    isLoading,
    error,
  };
};

// 资源预加载
export const preloadResource = (url: string, type: 'script' | 'style' | 'image' = 'script') => {
  return new Promise((resolve, reject) => {
    let element: HTMLElement;

    switch (type) {
      case 'script':
        element = document.createElement('script');
        (element as HTMLScriptElement).src = url;
        break;
      case 'style':
        element = document.createElement('link');
        (element as HTMLLinkElement).rel = 'stylesheet';
        (element as HTMLLinkElement).href = url;
        break;
      case 'image':
        element = document.createElement('img');
        (element as HTMLImageElement).src = url;
        break;
    }

    element.onload = () => resolve(element);
    element.onerror = reject;

    if (type !== 'image') {
      document.head.appendChild(element);
    }
  });
};

// 批量预加载资源
export const preloadResources = async (
  resources: Array<{ url: string; type?: 'script' | 'style' | 'image' }>
) => {
  const promises = resources.map(({ url, type = 'script' }) => preloadResource(url, type));
  return Promise.allSettled(promises);
};

// 性能监控装饰器
export const withPerformanceMonitoring = <P extends object>(
  Component: React.ComponentType<P>,
  componentName: string
) => {
  const MemoizedComponent = React.memo((props: P) => {
    useRenderPerformance(componentName);
    useMemoryLeakDetection(componentName);

    return React.createElement(Component, props);
  });

  MemoizedComponent.displayName = `withPerformanceMonitoring(${componentName})`;

  return MemoizedComponent;
};

export default {
  useDebounce,
  useThrottle,
  useVirtualScroll,
  useLazyImage,
  useMemoryLeakDetection,
  useRenderPerformance,
  useCache,
  useBatchUpdate,
  useWebWorker,
  preloadResource,
  preloadResources,
  withPerformanceMonitoring,
};
