/**
 * 统一字典选择组件
 * 自动从字典服务获取选项数据
 */

import React from 'react';
import { Select, Spin } from 'antd';
import { useDictionary } from '../../hooks/useDictionary';

interface DictionaryOption {
  value: string;
  label: string;
  color?: string;
  icon?: string;
}

interface DictionarySelectProps extends Omit<React.ComponentProps<typeof Select>, 'options'> {
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
  const { options, loading } = useDictionary(dictType, isActive);

  // 默认选项渲染
  const _renderOption = (option: DictionaryOption) => {
    if (optionRender) {
      return optionRender(option);
    }

    return (
      <span style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        {showColor && option.color != null && (
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
        {showIcon && option.icon != null && <span className={option.icon} />}
        <span>{option.label}</span>
      </span>
    );
  };

  // Prepare options data format - Ant Design 5.x best practice

  return (
    <Select
      {...props}
      loading={loading}
      placeholder={placeholder ?? `请选择${dictType.replace('_', '')}`}
      notFoundContent={loading ? <Spin size="small" /> : '暂无数据'}
      options={options}
      filterOption={(input, option) => {
        if (option === null || option === undefined) {
          return false;
        }
        const rawLabel = option.label;
        if (rawLabel === null || rawLabel === undefined) {
          return false;
        }
        // Convert label to string safely
        let label: string;
        if (typeof rawLabel === 'string') {
          label = rawLabel;
        } else if (React.isValidElement(rawLabel)) {
          const props = rawLabel.props as Record<string, unknown> | undefined;
          const children = props?.children;
          label =
            typeof children === 'string'
              ? children
              : children !== null && children !== undefined
                ? typeof children === 'string'
                  ? children
                  : JSON.stringify(children)
                : '';
        } else {
          label = String(rawLabel);
        }
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
