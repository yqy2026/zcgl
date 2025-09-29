/**
 * 统一字典选择组件
 * 自动从字典服务获取选项数据
 */

import React from 'react'
import { Select, Spin } from 'antd'
import { SelectProps } from 'antd/es/select'
import { useDictionary } from '../../hooks/useDictionary'
import { dictionaryService } from '../../services/dictionary'

const { Option } = Select

interface DictionarySelectProps extends Omit<SelectProps, 'options' | 'loading'> {
  /** 字典类型 */
  dictType: string
  /** 是否只显示启用的选项 */
  isActive?: boolean
  /** 是否显示颜色标识 */
  showColor?: boolean
  /** 是否显示图标 */
  showIcon?: boolean
  /** 自定义选项渲染 */
  optionRender?: (option: any) => React.ReactNode
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

  // 检查字典类型是否可用
  const isAvailable = dictionaryService.isTypeAvailable(dictType)

  // 如果字典类型不可用，显示警告
  if (!isAvailable) {
    console.warn(`字典类型不存在 [${dictType}]`)
  }

  // 如果有错误，显示错误信息
  if (error) {
    console.error(`字典加载失败 [${dictType}]:`, error)
  }

  // 默认选项渲染
  const renderOption = (option: any) => {
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

  return (
    <Select
      {...props}
      loading={loading}
      placeholder={placeholder || `请选择${dictType.replace('_', '')}`}
      notFoundContent={loading ? <Spin size="small" /> : '暂无数据'}
      filterOption={(input, option) => {
        const label = option?.children?.toString() || ''
        return label.toLowerCase().includes(input.toLowerCase())
      }}
    >
      {options.map(option => (
        <Option 
          key={option.value} 
          value={option.value}
          title={option.label}
        >
          {renderOption(option)}
        </Option>
      ))}
    </Select>
  )
}

export default DictionarySelect