import React, { useState, useCallback, useMemo } from 'react';
import {
  Select,
  Button,
  Modal,
  message,
  Space,
  Tooltip,
  Tag
} from 'antd';
import {
  PlusOutlined,
  ReloadOutlined,
  UnorderedListOutlined,
  SearchOutlined
} from '@ant-design/icons';
import { useOwnershipOptions } from '@/hooks/useOwnership';
import type { Ownership } from '@/types/ownership';
import OwnershipList from './OwnershipList';

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
  /** 是否显示搜索框 */
  showSearch?: boolean;
  /** 最大选择数量（多选模式） */
  maxCount?: number;
}

const OwnershipSelect: React.FC<OwnershipSelectProps> = ({
  value,
  onChange,
  placeholder = '请选择权属方',
  disabled = false,
  allowClear = true,
  style = {},
  size = 'middle',
  mode = 'single',
  showCreateButton = true,
  onlyActive = true,
  showAdvancedSelect = true,
  showSearch = true,
  maxCount
}) => {
  const [searchText, setSearchText] = useState('');
  const [selectModalVisible, setSelectModalVisible] = useState(false);

  // 使用React Query获取权属方数据
  const { ownerships: allOwnerships, loading, refresh } = useOwnershipOptions(onlyActive);

  // 根据搜索文本过滤权属方
  const filteredOwnerships = useMemo(() => {
    if (!searchText) return allOwnerships;

    return allOwnerships.filter(ownership =>
      ownership.name.toLowerCase().includes(searchText.toLowerCase()) ||
      ownership.code.toLowerCase().includes(searchText.toLowerCase()) ||
      ownership.short_name?.toLowerCase().includes(searchText.toLowerCase())
    );
  }, [allOwnerships, searchText]);

  // 当前选中的权属方（单选模式）
  const _selectedOwnership = useMemo(() => {
    if (mode === 'multiple' || !value) return null;
    const singleValue = Array.isArray(value) ? value[0] : value;
    return allOwnerships.find(o => o.id === singleValue) ||
           filteredOwnerships.find(o => o.name === singleValue) ||
           null;
  }, [value, filteredOwnerships, allOwnerships, mode]);

  // 当前选中的权属方（多选模式）
  const _selectedOwnerships = useMemo(() => {
    if (mode === 'single' || !value) return [];
    const values = Array.isArray(value) ? value : value ? [value] : [];
    return allOwnerships.filter(o => values.includes(o.id)) ||
           filteredOwnerships.filter(o => values.includes(o.id));
  }, [value, filteredOwnerships, allOwnerships, mode]);

  // 处理搜索 - 防抖处理
  const handleSearch = useCallback((text: string) => {
    setSearchText(text);
  }, []);

  // 处理单选
  const handleSingleChange = (selectedValue: string | { value: string; label: React.ReactNode }) => {
    // 处理labelInValue模式
    let valueStr: string;
    if (typeof selectedValue === 'object' && selectedValue !== null) {
      valueStr = selectedValue.value;
    } else {
      valueStr = selectedValue;
    }

    const selected = filteredOwnerships.find(o => o.id === valueStr) ||
                    filteredOwnerships.find(o => o.name === valueStr);

    if (selected) {
      onChange?.(selected.id, selected);
    } else {
      onChange?.(valueStr);
    }
  };

  // 处理多选
  const handleMultipleChange = (selectedValues: string[]) => {
    const selectedOwners = allOwnerships.filter(o => selectedValues.includes(o.id));
    onChange?.(selectedValues, selectedOwners);
  };

  // 处理清除
  const handleClear = () => {
    onChange?.(mode === 'multiple' ? [] : '', mode === 'multiple' ? [] : undefined);
  };

  // 获取选项标签
  const getOptionLabel = (ownership: Ownership) => (
    <Space>
      <span>{ownership.name}</span>
      {ownership.short_name && (
        <span style={{ color: '#999', fontSize: '12px' }}>
          ({ownership.short_name})
        </span>
      )}
      <span style={{ color: '#666', fontSize: '12px' }}>
        [{ownership.code}]
      </span>
      {!ownership.is_active && (
        <Tag color="red">禁用</Tag>
      )}
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
        color={ownership?.is_active ? 'blue' : 'red'}
        closable={closable}
        onClose={onClose}
        style={{ marginRight: 3 }}
      >
        {ownership?.name || value}
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
      const currentValues = Array.isArray(value) ? value : value ? [value] : [];
      if (!currentValues.includes(ownership.id)) {
        const newValues = maxCount ? [...currentValues.slice(-maxCount + 1), ownership.id] : [...currentValues, ownership.id];
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
    message.info('创建新权属方功能开发中');
  };

  return (
    <div style={style}>
      <Space.Compact style={{ width: '100%' }}>
        <Select
          value={value || (mode === 'multiple' ? [] : undefined) as any}
          onChange={mode === 'multiple' ? handleMultipleChange : handleSingleChange as any}
          onClear={handleClear}
          placeholder={placeholder}
          disabled={disabled}
          allowClear={allowClear}
          size={size}
          style={{ flex: 1 }}
          loading={loading}
          showSearch={showSearch}
          filterOption={false}
          onSearch={showSearch ? handleSearch : undefined}
          notFoundContent={loading ? '加载中...' : '暂无数据'}
          optionLabelProp="children"
          mode={mode === 'multiple' ? 'multiple' : undefined}
          maxCount={maxCount}
          tagRender={mode === 'multiple' ? tagRender : undefined}
        >
          {filteredOwnerships.map(ownership => (
            <Option key={ownership.id} value={ownership.id}>
              {getOptionLabel(ownership)}
            </Option>
          ))}
        </Select>

        <Tooltip title="从列表中选择">
          <Button
            icon={<SearchOutlined />}
            onClick={openSelectModal}
            disabled={disabled}
            size={size}
          />
        </Tooltip>

        {showAdvancedSelect && (
          <Tooltip title="从列表中选择">
            <Button
              icon={<UnorderedListOutlined />}
              onClick={openSelectModal}
              disabled={disabled}
              size={size}
            />
          </Tooltip>
        )}

        {showCreateButton && (
          <Tooltip title="创建新权属方">
            <Button
              icon={<PlusOutlined />}
              onClick={handleCreateOwnership}
              disabled={disabled}
              size={size}
            />
          </Tooltip>
        )}

        <Tooltip title="刷新">
          <Button
            icon={<ReloadOutlined />}
            onClick={handleRefresh}
            disabled={disabled}
            loading={loading}
            size={size}
          />
        </Tooltip>
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
        <OwnershipList
          mode="select"
          onSelectOwnership={handleModalSelect}
        />
      </Modal>
    </div>
  );
};

export default OwnershipSelect;
