import React, { useState, useCallback } from 'react'
import { Form, Input, InputNumber, Select, Button, Card } from 'antd'
import { CheckCircleOutlined, CloseOutlined } from '@ant-design/icons'
import { MessageManager } from '@/utils/messageManager'

// 表单数据类型
export interface FormData {
  [key: string]: unknown
}

// 验证函数类型
export type ValidationFunction = (value: unknown) => boolean

// 验证规则接口
export interface ValidationRule {
  required?: boolean
  min?: number
  max?: number
  custom?: ValidationFunction
  message: string
}

// 字段配置接口
export interface FieldConfig {
  name: string
  label: string
  type: 'text' | 'number' | 'select' | 'textarea' | 'autocomplete'
  placeholder?: string
  required?: boolean
  maxLength?: number
  validation?: ValidationRule[]
  options?: Array<{ label: string; value: string | number }>
  suffix?: string
  help?: string
}

// 按钮属性接口
export interface ButtonProps {
  icon?: React.ReactNode
  size?: 'small' | 'middle' | 'large'
  type?: 'primary' | 'default' | 'dashed' | 'link' | 'text'
  [key: string]: unknown
}

// 表单优化器属性
interface SmartFormOptimizerProps {
  fields: FieldConfig[]
  onSubmit: (data: FormData) => void | Promise<void>
  initialValues?: FormData
  submitText?: string
  submitButtonProps?: ButtonProps
  disabled?: boolean
  loading?: boolean
  layout?: 'horizontal' | 'vertical' | 'inline'
  size?: 'small' | 'middle' | 'large'
  style?: React.CSSProperties
}

// 智能表单优化器组件
const SmartFormOptimizer: React.FC<SmartFormOptimizerProps> = ({
  fields,
  onSubmit,
  initialValues = {},
  submitText = '提交',
  submitButtonProps = {},
  disabled = false,
  loading = false,
  layout = 'vertical',
  size = 'middle',
  style = {}
}) => {
  const [form] = Form.useForm()
  const [errors, setErrors] = useState<Record<string, string>>({})

  const handleSubmit = useCallback(async (values: Record<string, unknown>) => {
    try {
      const newErrors: Record<string, string> = {}

      // 验证必填字段
      fields.forEach(field => {
        if (field.required && !values[field.name]) {
          newErrors[field.name] = `${field.label}为必填项`
        }
      })

      // 自定义验证
      fields.forEach(field => {
        if (field.validation && values[field.name] !== undefined && values[field.name] !== null) {
          field.validation.forEach(rule => {
            if (rule.required && !values[field.name]) {
              newErrors[field.name] = rule.message
            }
            if (rule.min !== undefined && (values[field.name] as any) < rule.min) {
              newErrors[field.name] = rule.message
            }
            if (rule.max !== undefined && (values[field.name] as any) > rule.max) {
              newErrors[field.name] = rule.message
            }
            if (rule.custom && !rule.custom(values[field.name])) {
              newErrors[field.name] = rule.message
            }
          })
        }
      })

      if (Object.keys(newErrors).length > 0) {
        setErrors(newErrors)
        MessageManager.error('请修正表单错误')
        return
      }

      await onSubmit(values)
      form.resetFields()
      setErrors({})
      MessageManager.success('表单提交成功')
    } catch {
      MessageManager.error('表单提交失败')
    }
  }, [fields, onSubmit, form])

  const renderField = (field: FieldConfig) => {
    const commonProps = {
      placeholder: field.placeholder,
      disabled,
      size
    }

    switch (field.type) {
      case 'number':
        return (
          <InputNumber
            {...commonProps}
            style={{ width: '100%' }}
            min={0}
            max={field.maxLength}
            formatter={value => `${value}${field.suffix || ''}`}
            parser={value => value?.replace(new RegExp(`${field.suffix || ''}$`), '') as any}
          />
        )

      case 'select':
        return (
          <Select
            {...commonProps}
            style={{ width: '100%' }}
            options={field.options}
            allowClear
          />
        )

      case 'textarea':
        return (
          <Input.TextArea
            {...commonProps}
            rows={4}
            maxLength={field.maxLength}
            showCount
          />
        )

      default:
        return (
          <Input
            {...commonProps}
            maxLength={field.maxLength}
          />
        )
    }
  }

  return (
    <Card style={style} size={size as any}>
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
            rules={[
              { required: field.required, message: `${field.label}为必填项` }
            ]}
            help={field.help}
          >
            {renderField(field)}
          </Form.Item>
        ))}

        <Form.Item>
          <Button
            type="primary"
            htmlType="submit"
            loading={loading}
            icon={<CheckCircleOutlined />}
            {...submitButtonProps}
          >
            {submitText}
          </Button>
        </Form.Item>
      </Form>

      {Object.keys(errors).length > 0 && (
        <div style={{ marginTop: 16 }}>
          {errors.general && (
            <div style={{ color: '#ff4d4f', marginBottom: 8 }}>
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
        </div>
      )}
    </Card>
  )
}

// 使用示例组件
interface SmartFormExampleProps {
  onFormSubmit: (data: FormData) => void
}

const SmartFormExample: React.FC<SmartFormExampleProps> = ({ onFormSubmit }) => {
  const exampleFields: FieldConfig[] = [
    {
      name: 'ownership_entity',
      label: '权属方',
      type: 'text',
      placeholder: '请输入权属方',
      required: true,
      help: '支持模糊搜索和自动完成'
    },
    {
      name: 'property_name',
      label: '物业名称',
      type: 'text',
      placeholder: '请输入物业名称',
      required: true,
      maxLength: 200
    },
    {
      name: 'address',
      label: '物业地址',
      type: 'textarea',
      placeholder: '请输入物业地址',
      required: true,
      maxLength: 500
    },
    {
      name: 'actual_property_area',
      label: '实际房产面积',
      type: 'number',
      placeholder: '请输入面积（平方米）',
      required: true,
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
