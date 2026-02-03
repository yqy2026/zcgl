import { useCallback, useEffect, useRef, useState } from 'react';
import { useFilters } from './useFilters';

export interface ListResponse<T> {
  items?: T[];
  total?: number;
  pages?: number;
}

export interface ListPagination {
  current: number;
  pageSize: number;
  total: number;
  pages?: number;
}

export interface LoadListOptions<TFilters> {
  page?: number;
  pageSize?: number;
  filters?: Partial<TFilters>;
  replaceFilters?: boolean;
}

export interface UseListDataOptions<T, TFilters extends object> {
  fetcher: (params: { page: number; pageSize: number } & TFilters) => Promise<ListResponse<T>>;
  initialFilters: TFilters;
  initialPage?: number;
  initialPageSize?: number;
  onError?: (error: unknown) => void;
}

export const useListData = <T, TFilters extends object>(
  options: UseListDataOptions<T, TFilters>
) => {
  const {
    fetcher,
    initialFilters,
    initialPage = 1,
    initialPageSize = 10,
    onError,
  } = options;

  const initialFiltersRef = useRef(initialFilters);
  const { filters, setFilters, resetFilters } = useFilters<TFilters>(initialFilters);
  const [data, setData] = useState<T[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [pagination, setPagination] = useState<ListPagination>({
    current: initialPage,
    pageSize: initialPageSize,
    total: 0,
  });

  const filtersRef = useRef(filters);
  const paginationRef = useRef(pagination);
  const onErrorRef = useRef(onError);

  useEffect(() => {
    filtersRef.current = filters;
  }, [filters]);

  useEffect(() => {
    paginationRef.current = pagination;
  }, [pagination]);

  useEffect(() => {
    onErrorRef.current = onError;
  }, [onError]);

  const loadList = useCallback(
    async (loadOptions?: LoadListOptions<TFilters>) => {
      setLoading(true);
      setError(null);
      try {
        const optionsValue = loadOptions ?? {};
        const currentPagination = paginationRef.current;
        const currentFilters = filtersRef.current;
        const page = optionsValue.page ?? currentPagination.current;
        const pageSize = optionsValue.pageSize ?? currentPagination.pageSize;
        const nextFilters = optionsValue.replaceFilters
          ? ((optionsValue.filters ?? currentFilters) as TFilters)
          : ({ ...currentFilters, ...(optionsValue.filters ?? {}) } as TFilters);

        const response = await fetcher({ page, pageSize, ...nextFilters });

        if (response == null) {
          throw new Error('List response is empty');
        }

        const items = Array.isArray(response.items) ? response.items : [];

        setData(items);
        setPagination(prev => ({
          ...prev,
          current: page,
          pageSize,
          total: response.total ?? 0,
          pages: response.pages ?? prev.pages,
        }));

        if (optionsValue.filters != null) {
          setFilters(nextFilters);
        }
      } catch (error) {
        setData([]);
        setError(error);
        if (onErrorRef.current != null) {
          onErrorRef.current(error);
        }
      } finally {
        setLoading(false);
      }
    },
    [fetcher, setFilters]
  );

  const applyFilters = useCallback(
    (nextFilters: TFilters) => {
      setFilters(nextFilters);
      setPagination(prev => ({ ...prev, current: 1 }));
      void loadList({ page: 1, filters: nextFilters, replaceFilters: true });
    },
    [loadList, setFilters]
  );

  const resetAllFilters = useCallback(() => {
    resetFilters();
    setPagination(prev => ({ ...prev, current: 1 }));
    void loadList({
      page: 1,
      filters: initialFiltersRef.current,
      replaceFilters: true,
    });
  }, [loadList, resetFilters]);

  const updatePagination = useCallback(
    (next: { current?: number; pageSize?: number }) => {
      const current = next.current ?? pagination.current;
      const pageSize = next.pageSize ?? pagination.pageSize;
      setPagination(prev => ({ ...prev, current, pageSize }));
      void loadList({ page: current, pageSize });
    },
    [loadList, pagination.current, pagination.pageSize]
  );

  return {
    data,
    loading,
    error,
    pagination,
    filters,
    loadList,
    applyFilters,
    resetFilters: resetAllFilters,
    updatePagination,
  };
};
