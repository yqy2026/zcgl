/**
 * 统一字典选择组件
 * 自动从字典服务获取选项数据
 */

import React from 'react'
import { Select, Spin } from 'antd'
import { SelectProps } from 'antd/es/select'
import { useDictionary } from '../../hooks/useDictionary'
import { unifiedDictionaryService } from '../../services/dictionary'

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

  // 调试日志：追踪数据传递
  console.log(`🔍 [${dictType}] DictionarySelect调试信息:`, {
    optionsCount: options.length,
    isLoading: loading,
    hasError: !!error,
    errorMessage: error,
    optionsSample: options.slice(0, 2)
  })

  // 检查字典类型是否可用
  const isAvailable = unifiedDictionaryService.isTypeAvailable(dictType)

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

  // 准备选项数据格式 - Ant Design 5.x最佳实践
  const selectOptions = options.map((option, index) => ({
    key: `${option.value}-${index}`,
    value: option.value,
    label: typeof renderOption(option) === 'string' ? renderOption(option) :
           React.isValidElement(renderOption(option)) ? renderOption(option) : option.label,
    title: option.label,
    disabled: false
  }))

  // 调试日志：追踪最终选项数据
  console.log(`🎯 [${dictType}] 最终选项数据:`, {
    selectOptionsCount: selectOptions.length,
    selectOptionsSample: selectOptions.slice(0, 2),
    firstOptionStructure: selectOptions[0] ? {
      hasKey: !!selectOptions[0].key,
      hasValue: !!selectOptions[0].value,
      hasLabel: !!selectOptions[0].label,
      valueType: typeof selectOptions[0].value,
      labelType: typeof selectOptions[0].label
    } : null
  })

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
                       (option?.label as any)?.props?.children?.toString() || '' :
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
