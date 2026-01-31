import { useCallback, useRef, useState } from 'react';

export const useFilters = <T extends Record<string, unknown>>(initialFilters: T) => {
  const initialRef = useRef(initialFilters);
  const [filters, setFilters] = useState<T>(initialRef.current);

  const replaceFilters = useCallback((next: T) => {
    setFilters(next);
  }, []);

  const mergeFilters = useCallback((next: Partial<T>) => {
    setFilters(prev => ({ ...prev, ...next }));
  }, []);

  const resetFilters = useCallback(() => {
    setFilters(initialRef.current);
  }, []);

  return {
    filters,
    setFilters: replaceFilters,
    mergeFilters,
    resetFilters,
  };
};
