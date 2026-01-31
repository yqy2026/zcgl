/**
 * 字典选择组件
 * 自动从字典服务获取选项数据
 */

import React from 'react';
import { Select, Spin } from 'antd';
import type { SelectProps } from 'antd';
import { useDictionary } from '@/hooks/useDictionary';
import { dictionaryService } from '@/services/dictionary';
import type { DictionaryOption } from '@/services/dictionary';

interface DictionarySelectProps
  extends Omit<SelectProps<string, DictionaryOption>, 'options' | 'optionRender'> {
  /** 字典类型 */
  dictType: string;
  /** 是否只显示启用的选项 */
  isActive?: boolean;
  /** 是否显示颜色标识 */
  showColor?: boolean;
  /** 是否显示图标 */
  showIcon?: boolean;
  /** 自定义选项渲染 */
  optionRender?: (option: DictionaryOption) => React.ReactNode;
}

const DictionarySelect: React.FC<DictionarySelectProps> = ({
  dictType,
  isActive = true,
  showColor = false,
  showIcon = false,
  optionRender,
  placeholder,
  ...props
}) => {
  const { options, isLoading, error: _error } = useDictionary(dictType, isActive);

  // Track data flow for debugging

  // 检查字典类型是否可用
  const _isAvailable = dictionaryService.isTypeAvailable(dictType);

  // If dictionary type is not available, show warning

  // If there's an error, show error message

  // 默认选项渲染
  const _renderOption = (option: DictionaryOption) => {
    if (optionRender !== undefined && optionRender !== null && typeof optionRender === 'function') {
      return optionRender(option);
    }

    return (
      <span style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        {showColor &&
          option.color !== undefined &&
          option.color !== null &&
          option.color !== '' && (
            <span
              style={{
                width: '12px',
                height: '12px',
                borderRadius: '2px',
                backgroundColor: option.color,
                display: 'inline-block',
              }}
            />
          )}
        {showIcon && option.icon !== undefined && option.icon !== null && option.icon !== '' && (
          <span className={option.icon} />
        )}
        <span>{option.label}</span>
      </span>
    );
  };

  // Prepare options data format - Ant Design 5.x best practice

  return (
    <Select
      {...props}
      loading={isLoading}
      placeholder={placeholder ?? (`请选择${dictType.replace('_', '')}` as string)}
      notFoundContent={isLoading ? <Spin size="small" /> : '暂无数据'}
      options={options}
      filterOption={(input, option) => {
        // 处理React元素类型的label
        const label =
          typeof option?.label === 'string'
            ? option.label
            : option?.label !== null &&
                option?.label !== undefined &&
                React.isValidElement(option?.label)
              ? ((
                  option?.label as React.ReactElement<{ children?: string }>
                )?.props?.children?.toString() ?? '')
              : String(option?.label ?? '');
        return label.toLowerCase().includes(input.toLowerCase());
      }}
      virtual
      listHeight={256}
      // 使用label作为显示标签，确保选择后显示用户友好的文本而不是值
      showSearch
    />
  );
};

export default DictionarySelect;
