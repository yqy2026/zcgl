import React, { useEffect, useState } from 'react';
import { Select } from 'antd';
import { useQuery } from '@tanstack/react-query';
import { assetService } from '@/services/assetService';
import type { Asset } from '@/types/asset';
import { buildQueryScopeKey } from '@/utils/queryScope';

const DEFAULT_SEARCH_PAGE_SIZE = 20;
const SEARCH_DEBOUNCE_MS = 300;

interface AssetMultiSelectProps {
  value?: string[];
  onChange?: (ids: string[]) => void;
  projectId?: string;
  disabled?: boolean;
  placeholder?: string;
}

interface AssetOption {
  value: string;
  label: string;
  asset: Asset;
}

const toAssetOption = (asset: Asset): AssetOption => ({
  value: asset.id,
  label:
    asset.address != null && asset.address.trim() !== ''
      ? `${asset.asset_name} - ${asset.address}`
      : asset.asset_name,
  asset,
});

interface DebouncedSearch {
  projectId: string;
  keyword: string;
}

/**
 * 覆盖资产多选选择器：按项目远程搜索（PDF 导入确认页使用）。
 */
const AssetMultiSelect: React.FC<AssetMultiSelectProps> = ({
  value,
  onChange,
  projectId,
  disabled = false,
  placeholder = '请选择覆盖资产（可多选）',
}) => {
  const [keyword, setKeyword] = useState('');
  const normalizedProjectId = projectId?.trim() ?? '';
  const [debouncedSearch, setDebouncedSearch] = useState<DebouncedSearch>({
    projectId: normalizedProjectId,
    keyword: '',
  });
  const debouncedKeyword =
    debouncedSearch.projectId === normalizedProjectId ? debouncedSearch.keyword : '';
  const queryScopeKey = buildQueryScopeKey();

  useEffect(() => {
    setKeyword('');
    setDebouncedSearch({ projectId: normalizedProjectId, keyword: '' });
  }, [normalizedProjectId]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setDebouncedSearch({ projectId: normalizedProjectId, keyword: keyword.trim() });
    }, SEARCH_DEBOUNCE_MS);
    return () => window.clearTimeout(timer);
  }, [keyword, normalizedProjectId]);

  const { data, isFetching, isError } = useQuery({
    queryKey: ['asset-options', queryScopeKey, normalizedProjectId, debouncedKeyword],
    queryFn: () =>
      assetService.searchAssets(debouncedKeyword, {
        page_size: DEFAULT_SEARCH_PAGE_SIZE,
        project_id: normalizedProjectId,
      }),
    enabled: normalizedProjectId !== '',
  });

  return (
    <Select<string[]>
      mode="multiple"
      value={value}
      onChange={next => onChange?.(next)}
      placeholder={placeholder}
      disabled={disabled}
      showSearch
      searchValue={keyword}
      filterOption={false}
      onSearch={setKeyword}
      options={(data?.items ?? []).map(toAssetOption)}
      loading={isFetching}
      status={isError ? 'error' : undefined}
      notFoundContent={isError ? '资产加载失败，请重试' : '暂无数据'}
    />
  );
};

export default AssetMultiSelect;
