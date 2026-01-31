import React, { createContext, useContext, useState, useCallback, useEffect, useRef } from 'react';
import debounce from 'lodash/debounce';
import type { AssetSearchParams } from '@/types/asset';
import type { FilterPreset } from '@/types/analytics';
import { UsageStatus, PropertyNature, OwnershipStatus } from '@/types/asset';
import { useSearchHistory } from '@/hooks/useSearchHistory';
import { MessageManager } from '@/utils/messageManager';

// Filter presets configuration
export const FILTER_PRESETS: FilterPreset[] = [
  {
    key: 'all',
    label: '全部资产',
    filters: {},
    description: '显示所有资产数据',
  },
  {
    key: 'rented',
    label: '出租资产',
    filters: { usage_status: UsageStatus.RENTED },
    description: '仅显示已出租的资产',
  },
  {
    key: 'commercial',
    label: '经营性物业',
    filters: { property_nature: PropertyNature.COMMERCIAL },
    description: '仅显示经营性物业',
  },
  {
    key: 'confirmed',
    label: '已确权资产',
    filters: { ownership_status: OwnershipStatus.CONFIRMED },
    description: '仅显示已确权的资产',
  },
  {
    key: 'vacant',
    label: '空置资产',
    filters: { usage_status: UsageStatus.VACANT },
    description: '仅显示空置的资产',
  },
];

export interface AnalyticsFiltersContextValue {
  // Filter state
  filters: AssetSearchParams;
  localFilters: AssetSearchParams;
  setLocalFilters: React.Dispatch<React.SetStateAction<AssetSearchParams>>;
  selectedPreset: string;
  setSelectedPreset: (preset: string) => void;
  searchText: string;
  setSearchText: (text: string) => void;

  // UI state
  showHistory: boolean;
  setShowHistory: (show: boolean) => void;
  saveName: string;
  setSaveName: (name: string) => void;
  loading: boolean;
  showAdvanced: boolean;

  // Handlers
  handleFilterChange: (field: string, value: unknown) => void;
  handleDateRangeChange: (_dates: unknown, dateStrings: [string, string]) => void;
  handleSearch: (value: string) => void;
  handleReset: () => void;
  handleApply: () => void;
  handleSaveFilters: () => void;
  handleApplyHistory: (historyId: string) => void;
  handlePresetSelect: (presetKey: string) => void;

  // Search history
  searchHistory: ReturnType<typeof useSearchHistory>['searchHistory'];
  removeSearchHistory: (id: string) => void;

  // Computed
  activeFiltersCount: number;

  // Callbacks
  onToggleAdvanced?: () => void;
}

const AnalyticsFiltersContext = createContext<AnalyticsFiltersContextValue | null>(null);

export function useAnalyticsFiltersContext(): AnalyticsFiltersContextValue {
  const context = useContext(AnalyticsFiltersContext);
  if (!context) {
    throw new Error('useAnalyticsFiltersContext must be used within AnalyticsFiltersProvider');
  }
  return context;
}

interface AnalyticsFiltersProviderProps {
  filters: AssetSearchParams;
  onFiltersChange: (filters: AssetSearchParams) => void;
  onApplyFilters?: () => void;
  onResetFilters?: () => void;
  onPresetSelect?: (presetKey: string) => void;
  loading?: boolean;
  showAdvanced?: boolean;
  onToggleAdvanced?: () => void;
  realTimeUpdate?: boolean;
  children: React.ReactNode;
}

export const AnalyticsFiltersProvider: React.FC<AnalyticsFiltersProviderProps> = ({
  filters,
  onFiltersChange,
  onApplyFilters,
  onResetFilters,
  onPresetSelect,
  loading = false,
  showAdvanced = false,
  onToggleAdvanced,
  realTimeUpdate = true,
  children,
}) => {
  const [localFilters, setLocalFilters] = useState<AssetSearchParams>(filters);
  const [selectedPreset, setSelectedPreset] = useState<string>('all');
  const [searchText, setSearchText] = useState<string>('');
  const [showHistory, setShowHistory] = useState<boolean>(false);
  const [saveName, setSaveName] = useState<string>('');

  const { searchHistory, addSearchHistory, removeSearchHistory } = useSearchHistory();

  // Sync localFilters with external filters
  useEffect(() => {
    setLocalFilters(filters);

    const matchingPreset = FILTER_PRESETS.find(
      preset => JSON.stringify(preset.filters) === JSON.stringify(filters)
    );
    if (matchingPreset !== undefined) {
      setSelectedPreset(matchingPreset.key);
    } else if (Object.keys(filters).length === 0) {
      setSelectedPreset('all');
    } else {
      setSelectedPreset('custom');
    }
  }, [filters]);

  // Debounced filter change
  const debouncedFilterChange = useCallback(
    (newFilters: AssetSearchParams) => {
      onFiltersChange(newFilters);
    },
    [onFiltersChange]
  );

  const debouncedFilterChangeRef = useRef(debounce(debouncedFilterChange, 500));

  useEffect(() => {
    debouncedFilterChangeRef.current = debounce(debouncedFilterChange, realTimeUpdate ? 500 : 0);
  }, [debouncedFilterChange, realTimeUpdate]);

  const handleFilterChange = useCallback(
    (field: string, value: unknown) => {
      const newFilters = { ...localFilters, [field]: value };
      setLocalFilters(newFilters);
      debouncedFilterChangeRef.current(newFilters);
    },
    [localFilters]
  );

  const handleDateRangeChange = useCallback(
    (_dates: unknown, dateStrings: [string, string]) => {
      const newFilters = {
        ...localFilters,
        start_date: dateStrings[0] || undefined,
        end_date: dateStrings[1] || undefined,
      };
      setLocalFilters(newFilters);
      debouncedFilterChangeRef.current(newFilters);
    },
    [localFilters]
  );

  const handleSearch = useCallback(
    (value: string) => {
      setSearchText(value);
      const newFilters = { ...localFilters, search_keyword: value || undefined };
      setLocalFilters(newFilters);
      debouncedFilterChange(newFilters);
    },
    [localFilters, debouncedFilterChange]
  );

  const handleReset = useCallback(() => {
    const resetFilters = {};
    setLocalFilters(resetFilters);
    setSelectedPreset('all');
    setSearchText('');
    onResetFilters?.();
    MessageManager.success('筛选条件已重置');
  }, [onResetFilters]);

  const handleApply = useCallback(() => {
    onApplyFilters?.();
    MessageManager.success('筛选条件已应用');
  }, [onApplyFilters]);

  const handleSaveFilters = useCallback(() => {
    if (!saveName.trim()) {
      MessageManager.warning('请输入保存名称');
      return;
    }

    const activeCount = (Object.keys(localFilters) as (keyof AssetSearchParams)[]).filter(key => {
      const val = localFilters[key];
      return val !== undefined && val !== null && val !== '';
    }).length;

    if (activeCount === 0) {
      MessageManager.warning('请先设置筛选条件');
      return;
    }

    addSearchHistory({
      id: Date.now().toString(),
      name: saveName,
      conditions: localFilters,
      createdAt: new Date().toISOString(),
    });

    setSaveName('');
    MessageManager.success('筛选条件已保存');
  }, [saveName, localFilters, addSearchHistory]);

  const handleApplyHistory = useCallback(
    (historyId: string) => {
      const history = searchHistory.find(h => h.id === historyId);
      if (history !== undefined) {
        setLocalFilters(history.conditions);
        onFiltersChange(history.conditions);

        const matchingPreset = FILTER_PRESETS.find(
          preset => JSON.stringify(preset.filters) === JSON.stringify(history.conditions)
        );
        if (matchingPreset !== undefined && matchingPreset !== null) {
          setSelectedPreset(matchingPreset.key);
        } else {
          setSelectedPreset('custom');
        }

        setShowHistory(false);
        MessageManager.success(`已应用历史筛选条件: ${history.name}`);
      }
    },
    [searchHistory, onFiltersChange]
  );

  const handlePresetSelect = useCallback(
    (presetKey: string) => {
      const preset = FILTER_PRESETS.find(p => p.key === presetKey);
      if (preset !== undefined) {
        setLocalFilters(preset.filters);
        setSelectedPreset(presetKey);
        onFiltersChange(preset.filters);

        if (onPresetSelect !== undefined) {
          onPresetSelect(presetKey);
        }
      }
    },
    [onFiltersChange, onPresetSelect]
  );

  const activeFiltersCount = (Object.keys(localFilters) as (keyof AssetSearchParams)[]).filter(
    key => {
      const val = localFilters[key];
      return val !== undefined && val !== null && val !== '';
    }
  ).length;

  const value: AnalyticsFiltersContextValue = {
    filters,
    localFilters,
    setLocalFilters,
    selectedPreset,
    setSelectedPreset,
    searchText,
    setSearchText,
    showHistory,
    setShowHistory,
    saveName,
    setSaveName,
    loading,
    showAdvanced,
    handleFilterChange,
    handleDateRangeChange,
    handleSearch,
    handleReset,
    handleApply,
    handleSaveFilters,
    handleApplyHistory,
    handlePresetSelect,
    searchHistory,
    removeSearchHistory,
    activeFiltersCount,
    onToggleAdvanced,
  };

  return (
    <AnalyticsFiltersContext.Provider value={value}>{children}</AnalyticsFiltersContext.Provider>
  );
};

export default AnalyticsFiltersContext;
