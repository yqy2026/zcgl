import React, { useState, useCallback, useRef, useEffect } from 'react'
import { Form, Input, Select, Button, Card, Space, Typography, Tooltip, AutoComplete } from 'antd'
import {
  InfoCircleOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  CloseOutlined
} from '@ant-design/icons'

const { Text } = Typography

export type ValidationRule = {
  required?: boolean
  min?: number
  max?: number
  pattern?: RegExp
  custom?: (value: any) => string | boolean
  message?: string
}

export type FieldType = 'text' | 'number' | 'select' | 'date' | 'textarea' | 'autocomplete'

interface FieldConfig {
  name: string
  label: string
  type: FieldType
  placeholder?: string
  options?: Array<{ label: string; value: any }>
  validation?: ValidationRule[]
  disabled?: boolean
  required?: boolean
  autoFocus?: boolean
  maxLength?: number
  tooltip?: string
  help?: string
  prefix?: React.ReactNode
  suffix?: React.ReactNode
  icon?: React.ReactNode
}

interface FormData {
  [key: string]: any
}

interface SmartFormProps {
  fields: FieldConfig[]
  initialValues?: FormData
  onSubmit?: (values: FormData) => void
  onChange?: (values: FormData) => void
  onFieldChange?: (fieldName: string, value: any) => void
  validateOnChange?: boolean
  loading?: boolean
  submitText?: string
  submitButtonProps?: any
  layout?: 'horizontal' | 'vertical' | 'inline'
  size?: 'small' | 'middle' | 'large'
  disabled?: boolean
  className?: string
  style?: React.CSSProperties
  autoCompleteFields?: string[]
}

const SmartFormOptimizer: React.FC<SmartFormProps> = ({
  fields,
  initialValues = {},
  onSubmit,
  onChange,
  onFieldChange,
  validateOnChange = true,
  loading = false,
  submitText = '提交',
  submitButtonProps = {},
  layout = 'vertical',
  size = 'middle',
  disabled = false,
  className,
  style,
  autoCompleteFields = []
}) => {
  const [form] = Form.useForm()
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [validatedFields, setValidatedFields] = useState<Set<string>>(new Set())
  const [autoCompleteOptions, setAutoCompleteOptions] = useState<Record<string, Array<any>>>({})
  const fieldDebounceTimers = useRef<Record<string, NodeJS.Timeout>>({})

  // 验证规则
  const validateField = useCallback((value: any, rules: ValidationRule[], fieldName: string): string => {
    if (!rules || rules.length === 0) return ''

    for (const rule of rules) {
      if (rule.required && (!value || value === '')) {
        return `${fieldName}是必填项`
      }

      if (rule.min && value && Number(value) < rule.min) {
        return `${fieldName}不能小于${rule.min}`
      }

      if (rule.max && value && Number(value) > rule.max) {
        return `${fieldName}不能大于${rule.max}`
      }

      if (rule.pattern && value && !rule.pattern.test(value)) {
        return `${fieldName}格式不正确`
      }

      if (rule.custom) {
        const result = rule.custom(value)
        if (typeof result === 'string') {
          return `${fieldName}: ${result}`
        }
        if (result === false) {
          return `${fieldName}验证失败`
        }
      }

      if (rule.message) {
        return rule.message
      }
    }

    return ''
  }, [])

  // 防抖验证
  const debouncedValidate = useCallback((fieldName: string, value: any, rules: ValidationRule[]) => {
    // 清除之前的定时器
    if (fieldDebounceTimers.current[fieldName]) {
      clearTimeout(fieldDebounceTimers.current[fieldName])
    }

    // 设置新的定时器
    fieldDebounceTimers.current[fieldName] = setTimeout(() => {
      const error = validateField(value, rules, fieldName)
      setErrors(prev => ({ ...prev, [fieldName]: error }))

      if (!error) {
        setValidatedFields(prev => new Set([...prev, fieldName]))
      }
    }, 300)
  }, [validateField])

  // 智能自动完成
  const fetchAutoCompleteOptions = useCallback(async (fieldName: string, searchValue: string) => {
    if (!searchValue || searchValue.length < 2) {
      setAutoCompleteOptions(prev => ({ ...prev, [fieldName]: [] }))
      return
    }

    try {
      // 模拟API调用，实际应该调用后端API
      const response = await mockAutoCompleteAPI(fieldName, searchValue)
      setAutoCompleteOptions(prev => ({ ...prev, [fieldName]: response }))
    } catch (error) {
      console.warn(`自动完成获取失败: ${fieldName}`, error)
      setAutoCompleteOptions(prev => ({ ...prev, [fieldName]: [] }))
    }
  }, [])

  // 模拟自动完成API
  const mockAutoCompleteAPI = async (fieldName: string, searchValue: string) => {
    // 模拟网络延迟
    await new Promise(resolve => setTimeout(resolve, 500))

    // 根据字段类型返回不同的建议
    switch (fieldName) {
      case 'ownership_entity':
        return [
          { label: '广州市人民政府', value: '广州市人民政府' },
          { label: '深圳市国资委', value: '深圳市国资委' },
          { label: '珠海市土地储备中心', value: '珠海市土地储备中心' }
        ]
      case 'property_name':
        return [
          { label: '天河区珠江新城商业中心', value: '天河区珠江新城商业中心' },
          { label: '南山区科技园A座', value: '南山区科技园A座' },
          { label: '福田区CBD写字楼', value: '福田区CBD写字楼' }
        ]
      case 'address':
        return [
          { label: '广州市天河区华夏路10号', value: '广州市天河区华夏路10号' },
          { label: '深圳市南山区科技园南路1号', value: '深圳市南山区科技园南路1号' },
          { label: '佛山市顺德区大良街道凤山路2号', value: '佛山市顺德区大良街道凤山路2号' }
        ]
      default:
        return []
    }
  }

  // 实时验证
  const handleFieldChange = useCallback((fieldName: string, value: any) => {
    const field = fields.find(f => f.name === fieldName)
    if (!field || !validateOnChange) return

    // 清除之前的错误
    setErrors(prev => {
      const newErrors = { ...prev }
      delete newErrors[fieldName]
      return newErrors
    })

    // 防抖验证
    debouncedValidate(fieldName, value, field.validation || [])

    // 触发字段变化回调
    if (onFieldChange) {
      onFieldChange(fieldName, value)
    }

    // 触发整体变化回调
    if (onChange) {
      const currentValues = form.getFieldsValue()
      onChange({ ...currentValues, [fieldName]: value })
    }

    // 自动完成处理
    if (autoCompleteFields.includes(fieldName)) {
      fetchAutoCompleteOptions(fieldName, value)
    }
  }, [fields, validateOnChange, onFieldChange, onChange])

  // 表单提交
  const handleSubmit = useCallback(async (values: FormData) => {
    try {
      // 触发提交回调
      if (onSubmit) {
        await onSubmit(values)
      }
    } catch (error) {
      console.error('表单提交失败:', error)
      setErrors({ general: '提交失败，请重试' })
    }
  }, [onSubmit])

  // 获取字段验证状态
  const getFieldValidationStatus = (fieldName: string): 'valid' | 'invalid' | 'warning' => {
    const field = fields.find(f => f.name === fieldName)
    if (!field || !field.validation) return 'valid'

    const value = form.getFieldValue(fieldName)
    const error = errors[fieldName]

    if (error) return 'invalid'
    if (validatedFields.has(fieldName)) return 'valid'

    // 检查是否有危险数据
    const dangerPatterns = [
      /<script\b[^<]*(?:(?!<script>)<[^<]*)*<\/script>/gi,
      /javascript:/gi,
      /drop\s+table/i,
      /union\s+select/gi
      /insert\s+into/gi
      /delete\s+from/gi,
      /update\s+set/gi
    ]

    for (const pattern of dangerPatterns) {
      if (pattern.test(String(value))) {
        return 'warning'
      }
    }

    return 'valid'
  }

  // 清理函数
  useEffect(() => {
    return () => {
      Object.values(fieldDebounceTimers.current).forEach(timer => {
        if (timer) {
          clearTimeout(timer)
        }
      })
    }
  }, [])

  return (
    <Card
      className={className}
      style={style}
      size={size}
    >
      <Form
        form={form}
        layout={layout}
        size={size}
        initialValues={initialValues}
        onFinish={handleSubmit}
        disabled={disabled || loading}
      >
        {fields.map(field => (
          <Form.Item
            key={field.name}
            name={field.name}
            label={field.label}
            required={field.required}
            help={field.help}
            tooltip={field.tooltip ? {
              title: field.tooltip,
              icon: <InfoCircleOutlined style={{ color: '#1890ff' }} />
            } : undefined}
            hasFeedback={!!errors[field.name]}
            validateStatus={getFieldValidationStatus(field.name)}
          >
            {field.type === 'text' && (
              <Input
                placeholder={field.placeholder}
                maxLength={field.maxLength}
                disabled={field.disabled}
                autoFocus={field.autoFocus}
                prefix={field.prefix}
                suffix={field.suffix}
                addonBefore={field.icon}
                onChange={(e) => handleFieldChange(field.name, e.target.value)}
              />
            )}

            {field.type === 'number' && (
              <Input
                type="number"
                placeholder={field.placeholder}
                disabled={field.disabled}
                min={field.validation?.find(r => r.min)?.min}
                max={field.validation?.find(r => r.max)?.max}
                prefix={field.prefix}
                suffix={field.suffix}
                addonBefore={field.icon}
                onChange={(e) => handleFieldChange(field.name, e.target.value)}
              />
            )}

            {field.type === 'textarea' && (
              <Input.TextArea
                placeholder={field.placeholder}
                maxLength={field.maxLength}
                disabled={field.disabled}
                autoSize={{ minRows: 3, maxRows: 6 }}
                onChange={(e) => handleFieldChange(field.name, e.target.value)}
              />
            )}

            {field.type === 'select' && (
              <Select
                placeholder={field.placeholder}
                disabled={field.disabled}
                options={field.options}
                onChange={(value) => handleFieldChange(field.name, value)}
                showSearch
                filterOption={(input, option) =>
                  option.children?.toString().toLowerCase().includes(input.toLowerCase())
                }
              />
            )}

            {field.type === 'autocomplete' && (
              <AutoComplete
                placeholder={field.placeholder}
                disabled={field.disabled}
                options={autoCompleteOptions[field.name] || []}
                onChange={(value) => handleFieldChange(field.name, value)}
                onSearch={(value) => handleFieldChange(field.name, value)}
                style={{ width: '100%' }}
              />
            )}

            {field.type === 'date' && (
              <Input
                type="date"
                placeholder={field.placeholder}
                disabled={field.disabled}
                onChange={(e) => handleFieldChange(field.name, e.target.value)}
                style={{ width: '100%' }}
              />
            )}
          </Form.Item>
        ))}

        <Form.Item>
          <Space>
            <Button
              type="primary"
              htmlType="submit"
              loading={loading}
              disabled={disabled}
              {...submitButtonProps}
            >
              {submitText}
            </Button>
            {onSubmit && (
              <Button onClick={() => form.submit()} disabled={loading}>
                重置
              </Button>
            )}
          </Space>
        </Form.Item>

        {errors.general && (
          <div style={{ color: '#ff4d4f', textAlign: 'center', marginTop: '16px' }}>
            <ExclamationCircleOutlined style={{ marginRight: '8px' }} />
            {errors.general}
          </div>
        )}

        {Object.keys(errors).filter(key => key !== 'general').map(field => (
          <div key={field} style={{ color: '#ff4d4f', fontSize: '12px', marginTop: '4px' }}>
            <CloseOutlined
              style={{ marginRight: '4px', cursor: 'pointer' }}
              onClick={() => {
                setErrors(prev => {
                  const newErrors = { ...prev }
                  delete newErrors[field]
                  return newErrors
                })
              }}
            />
            {errors[field]}
          </div>
        ))}
      </Card>
    </Card>
  )
}

// 使用示例组件
interface SmartFormExampleProps {
  onFormSubmit: (data: any) => void
}

const SmartFormExample: React.FC<SmartFormExampleProps> = ({ onFormSubmit }) => {
  const exampleFields: FieldConfig[] = [
    {
      name: 'ownership_entity',
      label: '权属方',
      type: 'autocomplete',
      placeholder: '请输入或选择权属方',
      required: true,
      help: '支持模糊搜索和自动完成'
    },
    {
      name: 'property_name',
      label: '物业名称',
      type: 'text',
      placeholder: '请输入物业名称',
      required: true,
      maxLength: 200,
      validation: [
        { required: true, message: '物业名称为必填项' },
        { min: 2, message: '物业名称至少2个字符' }
      ]
    },
    {
      name: 'address',
      label: '物业地址',
      type: 'textarea',
      placeholder: '请输入物业地址',
      required: true,
      maxLength: 500,
      validation: [
        { required: true, message: '物业地址为必填项' },
        { custom: (value: string) => {
          // 简单的地址格式验证
          const addressRegex = /^.{5,}$/  // 至少5个字符
          return addressRegex.test(value)
        }, message: '请输入有效的地址' }
      ]
    },
    {
      name: 'actual_property_area',
      label: '实际房产面积',
      type: 'number',
      placeholder: '请输入面积（平方米）',
      required: true,
      validation: [
        { required: true, message: '面积为必填项' },
        { min: 1, message: '面积必须大于0' },
        { max: 100000, message: '面积不能超过100000平方米' }
      ],
      suffix: 'm²'
    },
    {
      name: 'usage_status',
      label: '使用状态',
      type: 'select',
      placeholder: '请选择使用状态',
      options: [
        { label: '已出租', value: '已出租' },
        { label: '空置', value: '空置' },
        { label: '自用', value: '自用' },
        { label: '装修中', value: '装修中' }
      ],
      required: true
    }
  ]

  return (
    <Card title="智能表单示例" style={{ margin: '24px' }}>
      <SmartFormOptimizer
        fields={exampleFields}
        onSubmit={onFormSubmit}
        submitText="保存资产信息"
        submitButtonProps={{ icon: <CheckCircleOutlined /> }}
      />
    </Card>
  )
}

export default SmartFormOptimizer
export { SmartFormExample }