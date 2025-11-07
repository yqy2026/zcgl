/**
 * 统一字典选择组件
 * 自动从字典服务获取选项数据
 */

import React from 'react'
import { Select, Spin } from 'antd'
import { SelectProps } from 'antd/es/select'
import { useDictionary } from '../../hooks/useDictionary'
import { unifiedDictionaryService } from '../../services/dictionary'

interface DictionaryOption {
  value: string
  label: string
  color?: string
  icon?: string
}

interface DictionarySelectProps extends SelectProps {
  /** 字典类型 */
  dictType: string
  /** 是否只显示启用的选项 */
  isActive?: boolean
  /** 是否显示颜色标识 */
  showColor?: boolean
  /** 是否显示图标 */
  showIcon?: boolean
  /** 自定义选项渲染 */
  optionRender?: (option: DictionaryOption) => React.ReactNode
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
  const { options, loading, error } = useDictionary(dictType, isActive)

  // Track data flow for debugging

  // 检查字典类型是否可用
  const isAvailable = unifiedDictionaryService.isTypeAvailable(dictType)

  // If dictionary type is not available, show warning

  // If there's an error, show error message

  // 默认选项渲染
  const renderOption = (option: DictionaryOption) => {
    if (optionRender) {
      return optionRender(option)
    }

    return (
      <span style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        {showColor && option.color && (
          <span
            style={{
              width: '12px',
              height: '12px',
              borderRadius: '2px',
              backgroundColor: option.color,
              display: 'inline-block'
            }}
          />
        )}
        {showIcon && option.icon && (
          <span className={option.icon} />
        )}
        <span>{option.label}</span>
      </span>
    )
  }

  // Prepare options data format - Ant Design 5.x best practice

  return (
    <Select
      {...props}
      loading={loading}
      placeholder={placeholder || `请选择${dictType.replace('_', '')}`}
      notFoundContent={loading ? <Spin size="small" /> : '暂无数据'}
      options={selectOptions}
      filterOption={(input, option) => {
        // 处理React元素类型的label
        const label = typeof option?.label === 'string' ? option.label :
                     (React.isValidElement(option?.label) ?
                       (option?.label as React.ReactElement)?.props?.children?.toString() || '' :
                       String(option?.label || ''))
        return label.toLowerCase().includes(input.toLowerCase())
      }}
      virtual
      listHeight={256}
      // 使用label作为显示标签，确保选择后显示用户友好的文本而不是值
      showSearch
    />
  )
}

export default DictionarySelect
