import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Select } from 'antd';
import { assetService } from '@/services/assetService';
import type { Asset } from '@/types/asset';

const DEFAULT_SEARCH_LIMIT = 20;

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
  const [options, setOptions] = useState<AssetOption[]>([]);
  const [loading, setLoading] = useState(false);
  const requestIdRef = useRef(0);

  const loadOptions = useCallback(
    async (query: string) => {
      requestIdRef.current += 1;
      const currentRequestId = requestIdRef.current;
      setLoading(true);
      try {
        const result = await assetService.searchAssets(query, {
          limit: DEFAULT_SEARCH_LIMIT,
          project_id: projectId,
        });
        if (currentRequestId !== requestIdRef.current) {
          return;
        }
        setOptions(result.items.map(toAssetOption));
      } catch (error) {
        // 失败不静默：保留日志便于定位（搜索框降级为空列表）
        console.error('资产搜索失败:', error);
        if (currentRequestId === requestIdRef.current) {
          setOptions([]);
        }
      } finally {
        if (currentRequestId === requestIdRef.current) {
          setLoading(false);
        }
      }
    },
    [projectId]
  );

  useEffect(() => {
    void loadOptions('');
  }, [loadOptions]);

  return (
    <Select<string[]>
      mode="multiple"
      value={value}
      onChange={next => onChange?.(next)}
      placeholder={placeholder}
      disabled={disabled}
      showSearch
      filterOption={false}
      onSearch={query => {
        void loadOptions(query);
      }}
      options={options}
      loading={loading}
    />
  );
};

export default AssetMultiSelect;
