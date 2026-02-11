import React, { useState, useCallback, useMemo } from 'react';
import { Select, Button, Modal, Space, Tooltip, Tag } from 'antd';
import type { SelectProps } from 'antd';
import type { DefaultOptionType } from 'antd/es/select';
import { MessageManager } from '@/utils/messageManager';
import {
  PlusOutlined,
  ReloadOutlined,
  UnorderedListOutlined,
  SearchOutlined,
} from '@ant-design/icons';
import { useOwnershipOptions } from '@/hooks/useOwnership';
import type { Ownership } from '@/types/ownership';
import OwnershipList from './OwnershipList';
import styles from './OwnershipSelect.module.css';

const { Option } = Select;

interface OwnershipSelectProps {
  /** 选中的权属方ID(s) */
  value?: string | string[];
  /** 变化回调 */
  onChange?: (value: string | string[], ownerships?: Ownership | Ownership[]) => void;
  /** 占位符 */
  placeholder?: string;
  /** 是否禁用 */
  disabled?: boolean;
  /** 是否允许清除 */
  allowClear?: boolean;
  /** 样式 */
  style?: React.CSSProperties;
  /** 尺寸 */
  size?: 'large' | 'middle' | 'small';
  /** 选择模式：single | multiple */
  mode?: 'single' | 'multiple';
  /** 是否显示创建按钮 */
  showCreateButton?: boolean;
  /** 是否只显示启用权属方 */
  onlyActive?: boolean;
  /** 是否显示高级选择按钮 */
  showAdvancedSelect?: boolean;
  /** 是否显示弹窗选择按钮 */
  showPickerButton?: boolean;
  /** 是否显示刷新按钮 */
  showRefreshButton?: boolean;
  /** 是否显示搜索框 */
  showSearch?: boolean;
  /** 组件变体 */
  variant?: 'full' | 'compact' | 'selectionOnly';
  /** 最大选择数量（多选模式） */
  maxCount?: number;
  /** 可访问性标签 */
  ariaLabel?: string;
}

type OwnershipSelectValue = string | string[];
interface OwnershipSelectOption extends DefaultOptionType {
  value: string;
  label: React.ReactNode;
}

const OWNERSHIP_SELECT_VARIANTS = {
  full: {
    showCreateButton: true,
    showAdvancedSelect: true,
    showPickerButton: true,
    showRefreshButton: true,
    showSearch: true,
  },
  compact: {
    showCreateButton: false,
    showAdvancedSelect: false,
    showPickerButton: true,
    showRefreshButton: true,
    showSearch: true,
  },
  selectionOnly: {
    showCreateButton: false,
    showAdvancedSelect: false,
    showPickerButton: false,
    showRefreshButton: false,
    showSearch: false,
  },
} as const;

const OwnershipSelect: React.FC<OwnershipSelectProps> = ({
  value,
  onChange,
  placeholder = '请选择权属方',
  disabled = false,
  allowClear = true,
  style,
  size = 'middle',
  mode = 'single',
  showCreateButton,
  onlyActive = true,
  showAdvancedSelect,
  showPickerButton,
  showRefreshButton,
  showSearch,
  variant = 'full',
  maxCount,
  ariaLabel,
}) => {
  const [searchText, setSearchText] = useState('');
  const [selectModalVisible, setSelectModalVisible] = useState(false);

  const variantConfig = OWNERSHIP_SELECT_VARIANTS[variant];
  const resolvedShowCreateButton = showCreateButton ?? variantConfig.showCreateButton;
  const resolvedShowAdvancedSelect = showAdvancedSelect ?? variantConfig.showAdvancedSelect;
  const resolvedShowPickerButton = showPickerButton ?? variantConfig.showPickerButton;
  const resolvedShowRefreshButton = showRefreshButton ?? variantConfig.showRefreshButton;
  const resolvedShowSearch = showSearch ?? variantConfig.showSearch;

  // 使用React Query获取权属方数据
  const { ownerships: allOwnerships, loading, refresh } = useOwnershipOptions(onlyActive);

  // 根据搜索文本过滤权属方
  const filteredOwnerships = useMemo(() => {
    if (searchText == null || searchText.length === 0) return allOwnerships;

    return allOwnerships.filter(
      ownership =>
        ownership.name.toLowerCase().includes(searchText.toLowerCase()) ||
        ownership.code.toLowerCase().includes(searchText.toLowerCase()) ||
        (ownership.short_name != null &&
          ownership.short_name.toLowerCase().includes(searchText.toLowerCase()))
    );
  }, [allOwnerships, searchText]);

  // 当前选中的权属方（单选模式）
  const _selectedOwnership = useMemo(() => {
    if (mode === 'multiple' || value == null) return null;
    const singleValue = Array.isArray(value) ? value[0] : value;
    return (
      allOwnerships.find(o => o.id === singleValue) ??
      filteredOwnerships.find(o => o.name === singleValue) ??
      null
    );
  }, [value, filteredOwnerships, allOwnerships, mode]);

  // 当前选中的权属方（多选模式）
  const _selectedOwnerships = useMemo(() => {
    if (mode === 'single' || value == null) return [];
    const values = Array.isArray(value) ? value : [value];
    const filtered = allOwnerships.filter(o => values.includes(o.id));
    if (filtered.length > 0) return filtered;
    return filteredOwnerships.filter(o => values.includes(o.id));
  }, [value, filteredOwnerships, allOwnerships, mode]);

  // 处理搜索 - 防抖处理
  const handleSearch = useCallback((text: string) => {
    setSearchText(text);
  }, []);

  const handleChange: SelectProps<
    OwnershipSelectValue,
    OwnershipSelectOption
  >['onChange'] = selectedValue => {
    if (selectedValue == null || selectedValue === '') {
      onChange?.(mode === 'multiple' ? [] : '', mode === 'multiple' ? [] : undefined);
      return;
    }

    if (mode === 'multiple') {
      const values = Array.isArray(selectedValue) ? selectedValue : [selectedValue];
      const selectedOwners = allOwnerships.filter(o => values.includes(o.id));
      onChange?.(values, selectedOwners);
      return;
    }

    const valueStr = Array.isArray(selectedValue) ? selectedValue[0] : selectedValue;
    const selected =
      filteredOwnerships.find(o => o.id === valueStr) ||
      filteredOwnerships.find(o => o.name === valueStr);

    if (selected !== undefined && selected !== null) {
      onChange?.(selected.id, selected);
    } else {
      onChange?.(valueStr);
    }
  };

  // 处理清除
  const handleClear = () => {
    onChange?.(mode === 'multiple' ? [] : '', mode === 'multiple' ? [] : undefined);
  };

  // 获取选项标签
  const getOptionLabel = (ownership: Ownership) => (
    <Space>
      <span>{ownership.name}</span>
      {ownership.short_name != null && (
        <span className={styles.shortNameText}>({ownership.short_name})</span>
      )}
      <span className={styles.codeText}>[{ownership.code}]</span>
      {ownership.is_active === false && <Tag color="red">禁用</Tag>}
    </Space>
  );

  // 多选模式下已选权属方的标签渲染
  const tagRender = (props: {
    label: React.ReactNode;
    value: string;
    closable: boolean;
    onClose: () => void;
  }) => {
    const { label: _label, value, closable, onClose } = props;
    const ownership = allOwnerships.find(o => o.id === value);

    return (
      <Tag
        color={ownership?.is_active === true ? 'blue' : 'red'}
        closable={closable}
        onClose={onClose}
        className={styles.selectedTag}
      >
        {ownership?.name ?? value}
      </Tag>
    );
  };

  // 打开选择弹窗
  const openSelectModal = () => {
    setSelectModalVisible(true);
  };

  // 从弹窗中选择权属方
  const handleModalSelect = (ownership: Ownership) => {
    if (mode === 'single') {
      onChange?.(ownership.id, ownership);
    } else {
      // 多选模式下，添加到已选列表
      const currentValues = Array.isArray(value) ? value : value != null ? [value] : [];
      if (!currentValues.includes(ownership.id)) {
        const newValues =
          maxCount != null && maxCount > 0
            ? [...currentValues.slice(-maxCount + 1), ownership.id]
            : [...currentValues, ownership.id];
        const selectedOwners = allOwnerships.filter(o => newValues.includes(o.id));
        onChange?.(newValues, selectedOwners);
      }
    }
    setSelectModalVisible(false);
  };

  // 刷新列表
  const handleRefresh = () => {
    refresh();
  };

  // 创建新权属方
  const handleCreateOwnership = () => {
    // 这里可以跳转到权属方管理页面或打开创建弹窗
    MessageManager.info('创建新权属方功能开发中');
  };

  return (
    <div style={style}>
      <Space.Compact className={styles.compactContainer}>
        <Select<OwnershipSelectValue, OwnershipSelectOption>
          value={value ?? (mode === 'multiple' ? [] : undefined)}
          onChange={handleChange}
          onClear={handleClear}
          placeholder={placeholder}
          disabled={disabled}
          allowClear={allowClear}
          size={size}
          className={styles.ownershipSelect}
          loading={loading}
          showSearch={resolvedShowSearch}
          filterOption={false}
          onSearch={resolvedShowSearch ? handleSearch : undefined}
          notFoundContent={loading ? '加载中...' : '暂无数据'}
          optionLabelProp="children"
          mode={mode === 'multiple' ? 'multiple' : undefined}
          maxCount={maxCount}
          tagRender={mode === 'multiple' ? tagRender : undefined}
          aria-label={ariaLabel}
        >
          {filteredOwnerships.map(ownership => (
            <Option key={ownership.id} value={ownership.id}>
              {getOptionLabel(ownership)}
            </Option>
          ))}
        </Select>

        {resolvedShowPickerButton && (
          <Tooltip title="从列表中选择">
            <Button
              icon={<SearchOutlined />}
              onClick={openSelectModal}
              disabled={disabled}
              size={size}
            />
          </Tooltip>
        )}

        {resolvedShowAdvancedSelect && (
          <Tooltip title="从列表中选择">
            <Button
              icon={<UnorderedListOutlined />}
              onClick={openSelectModal}
              disabled={disabled}
              size={size}
            />
          </Tooltip>
        )}

        {resolvedShowCreateButton && (
          <Tooltip title="创建新权属方">
            <Button
              icon={<PlusOutlined />}
              onClick={handleCreateOwnership}
              disabled={disabled}
              size={size}
            />
          </Tooltip>
        )}

        {resolvedShowRefreshButton && (
          <Tooltip title="刷新">
            <Button
              icon={<ReloadOutlined />}
              onClick={handleRefresh}
              disabled={disabled}
              loading={loading}
              size={size}
            />
          </Tooltip>
        )}
      </Space.Compact>

      {/* 选择弹窗 */}
      <Modal
        title={`选择权属方${mode === 'multiple' ? '（可多选）' : ''}`}
        open={selectModalVisible}
        onCancel={() => setSelectModalVisible(false)}
        footer={null}
        width={1200}
        destroyOnHidden
      >
        <OwnershipList mode="select" onSelectOwnership={handleModalSelect} />
      </Modal>
    </div>
  );
};

export default OwnershipSelect;
