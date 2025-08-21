import React, { useState, useEffect } from 'react'
import { 
  Form, 
  Input, 
  Select, 
  InputNumber, 
  DatePicker, 
  Button, 
  Space, 
  Card, 
  Row, 
  Col,
  Progress,
  Divider,
  Typography,
  Switch,
  message
} from 'antd'
import { SaveOutlined, ReloadOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'

const { Option } = Select
const { TextArea } = Input
const { Title, Text } = Typography

interface AssetFormProps {
  initialData?: any
  onSubmit: (data: any) => Promise<void>
  onCancel: () => void
  loading?: boolean
  mode?: 'create' | 'edit'
}

const AssetForm: React.FC<AssetFormProps> = ({
  initialData,
  onSubmit,
  onCancel,
  loading = false,
  mode = 'create'
}) => {
  const [form] = Form.useForm()
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [completionRate, setCompletionRate] = useState(0)

  // 监听表单值变化，计算完成度
  const handleValuesChange = (changedValues: any, allValues: any) => {
    const requiredFields = [
      'property_name',
      'ownership_entity', 
      'address',
      'ownership_status',
      'property_nature',
      'usage_status'
    ]
    
    const filledFields = requiredFields.filter(field => allValues[field])
    const rate = (filledFields.length / requiredFields.length) * 100
    setCompletionRate(rate)

    // 自动计算逻辑
    if (changedValues.rentable_area || changedValues.rented_area) {
      const rentableArea = allValues.rentable_area || 0
      const rentedArea = allValues.rented_area || 0
      
      if (rentableArea > 0) {
        const occupancyRate = (rentedArea / rentableArea * 100).toFixed(2)
        const unrentedArea = rentableArea - rentedArea
        
        form.setFieldsValue({
          occupancy_rate: `${occupancyRate}%`,
          unrented_area: unrentedArea
        })
      }
    }
  }

  // 初始化表单数据
  useEffect(() => {
    if (initialData) {
      const formData = {
        ...initialData,
        current_contract_start_date: initialData.current_contract_start_date 
          ? dayjs(initialData.current_contract_start_date) 
          : undefined,
        current_contract_end_date: initialData.current_contract_end_date 
          ? dayjs(initialData.current_contract_end_date) 
          : undefined,
        agreement_start_date: initialData.agreement_start_date 
          ? dayjs(initialData.agreement_start_date) 
          : undefined,
        agreement_end_date: initialData.agreement_end_date 
          ? dayjs(initialData.agreement_end_date) 
          : undefined,
      }
      form.setFieldsValue(formData)
    }
  }, [initialData, form])

  const handleSubmit = async (values: any) => {
    try {
      // 处理日期字段
      const submitData = {
        ...values,
        current_contract_start_date: values.current_contract_start_date?.format('YYYY-MM-DD'),
        current_contract_end_date: values.current_contract_end_date?.format('YYYY-MM-DD'),
        agreement_start_date: values.agreement_start_date?.format('YYYY-MM-DD'),
        agreement_end_date: values.agreement_end_date?.format('YYYY-MM-DD'),
      }
      
      await onSubmit(submitData)
    } catch (error) {
      message.error('提交失败，请重试')
    }
  }

  const handleReset = () => {
    form.resetFields()
    setCompletionRate(0)
  }

  return (
    <div>
      {/* 完成度指示器 */}
      <Card style={{ marginBottom: '16px' }}>
        <Row justify="space-between" align="middle">
          <Col>
            <Text>表单完成度</Text>
          </Col>
          <Col flex="auto" style={{ marginLeft: '16px' }}>
            <Progress 
              percent={completionRate} 
              size="small"
              strokeColor={completionRate === 100 ? '#52c41a' : '#1890ff'}
            />
          </Col>
          <Col>
            <Text strong>{completionRate.toFixed(0)}%</Text>
          </Col>
        </Row>
      </Card>

      <Form
        form={form}
        layout="vertical"
        onFinish={handleSubmit}
        onValuesChange={handleValuesChange}
      >
        {/* 基本信息 */}
        <Card title="基本信息" style={{ marginBottom: '16px' }}>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="物业名称"
                name="property_name"
                rules={[{ required: true, message: '请输入物业名称' }]}
              >
                <Input placeholder="请输入物业名称" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="权属方"
                name="ownership_entity"
                rules={[{ required: true, message: '请输入权属方' }]}
              >
                <Input placeholder="请输入权属方" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="经营管理方"
                name="management_entity"
              >
                <Input placeholder="请输入经营管理方" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="权属类别"
                name="ownership_category"
              >
                <Input placeholder="请输入权属类别" />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            label="所在地址"
            name="address"
            rules={[{ required: true, message: '请输入所在地址' }]}
          >
            <Input placeholder="请输入详细地址" />
          </Form.Item>
        </Card>

        {/* 面积信息 */}
        <Card title="面积信息" style={{ marginBottom: '16px' }}>
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item
                label="土地面积(㎡)"
                name="land_area"
              >
                <InputNumber 
                  placeholder="请输入土地面积" 
                  style={{ width: '100%' }}
                  min={0}
                />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                label="实际房产面积(㎡)"
                name="actual_property_area"
              >
                <InputNumber 
                  placeholder="请输入实际房产面积" 
                  style={{ width: '100%' }}
                  min={0}
                />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                label="非经营物业面积(㎡)"
                name="non_commercial_area"
              >
                <InputNumber 
                  placeholder="请输入非经营物业面积" 
                  style={{ width: '100%' }}
                  min={0}
                />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item
                label="可出租面积(㎡)"
                name="rentable_area"
              >
                <InputNumber 
                  placeholder="请输入可出租面积" 
                  style={{ width: '100%' }}
                  min={0}
                />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                label="已出租面积(㎡)"
                name="rented_area"
              >
                <InputNumber 
                  placeholder="请输入已出租面积" 
                  style={{ width: '100%' }}
                  min={0}
                />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                label="未出租面积(㎡)"
                name="unrented_area"
              >
                <InputNumber 
                  placeholder="自动计算" 
                  style={{ width: '100%' }}
                  disabled
                />
              </Form.Item>
            </Col>
          </Row>
        </Card>

        {/* 状态信息 */}
        <Card title="状态信息" style={{ marginBottom: '16px' }}>
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item
                label="物业性质"
                name="property_nature"
                rules={[{ required: true, message: '请选择物业性质' }]}
              >
                <Select placeholder="请选择物业性质">
                  <Option value="经营类">经营类</Option>
                  <Option value="非经营类">非经营类</Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                label="使用状态"
                name="usage_status"
                rules={[{ required: true, message: '请选择使用状态' }]}
              >
                <Select placeholder="请选择使用状态">
                  <Option value="出租">出租</Option>
                  <Option value="闲置">闲置</Option>
                  <Option value="自用">自用</Option>
                  <Option value="公房">公房</Option>
                  <Option value="其他">其他</Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                label="确权状态"
                name="ownership_status"
                rules={[{ required: true, message: '请选择确权状态' }]}
              >
                <Select placeholder="请选择确权状态">
                  <Option value="已确权">已确权</Option>
                  <Option value="未确权">未确权</Option>
                  <Option value="部分确权">部分确权</Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item
                label="证载用途"
                name="certificated_usage"
              >
                <Input placeholder="请输入证载用途" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                label="实际用途"
                name="actual_usage"
              >
                <Input placeholder="请输入实际用途" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                label="业态类别"
                name="business_category"
              >
                <Input placeholder="请输入业态类别" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item
                label="是否涉诉"
                name="is_litigated"
              >
                <Select placeholder="请选择是否涉诉">
                  <Option value={false}>否</Option>
                  <Option value={true}>是</Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                label="出租率"
                name="occupancy_rate"
              >
                <Input placeholder="自动计算" disabled />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                label="是否计入出租率"
                name="include_in_occupancy_rate"
              >
                <Select placeholder="请选择">
                  <Option value={true}>是</Option>
                  <Option value={false}>否</Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>
        </Card>

        {/* 高级选项 */}
        <Card 
          title={
            <Space>
              <span>高级选项</span>
              <Switch 
                checked={showAdvanced}
                onChange={setShowAdvanced}
                size="small"
              />
            </Space>
          }
          style={{ marginBottom: '16px' }}
        >
          {showAdvanced && (
            <>
              {/* 合同信息 */}
              <Title level={5}>合同信息</Title>
              <Row gutter={16}>
                <Col span={8}>
                  <Form.Item
                    label="承租合同"
                    name="lease_contract"
                  >
                    <Input placeholder="请输入承租合同编号" />
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item
                    label="租户名称"
                    name="tenant_name"
                  >
                    <Input placeholder="请输入租户名称" />
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item
                    label="经营模式"
                    name="business_model"
                  >
                    <Input placeholder="请输入经营模式" />
                  </Form.Item>
                </Col>
              </Row>

              <Row gutter={16}>
                <Col span={12}>
                  <Form.Item
                    label="合同开始日期"
                    name="current_contract_start_date"
                  >
                    <DatePicker style={{ width: '100%' }} />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item
                    label="合同结束日期"
                    name="current_contract_end_date"
                  >
                    <DatePicker style={{ width: '100%' }} />
                  </Form.Item>
                </Col>
              </Row>

              <Divider />

              {/* 项目信息 */}
              <Title level={5}>项目信息</Title>
              <Row gutter={16}>
                <Col span={8}>
                  <Form.Item
                    label="五羊项目名称"
                    name="wuyang_project_name"
                  >
                    <Input placeholder="请输入五羊项目名称" />
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item
                    label="协议开始日期"
                    name="agreement_start_date"
                  >
                    <DatePicker style={{ width: '100%' }} />
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item
                    label="协议结束日期"
                    name="agreement_end_date"
                  >
                    <DatePicker style={{ width: '100%' }} />
                  </Form.Item>
                </Col>
              </Row>

              <Divider />

              {/* 备注信息 */}
              <Title level={5}>备注信息</Title>
              <Row gutter={16}>
                <Col span={12}>
                  <Form.Item
                    label="说明"
                    name="description"
                  >
                    <TextArea 
                      rows={4} 
                      placeholder="请输入资产说明" 
                    />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item
                    label="其他备注"
                    name="notes"
                  >
                    <TextArea 
                      rows={4} 
                      placeholder="请输入其他备注信息" 
                    />
                  </Form.Item>
                </Col>
              </Row>
            </>
          )}
        </Card>

        {/* 操作按钮 */}
        <Card>
          <Space>
            <Button 
              type="primary" 
              htmlType="submit" 
              loading={loading}
              icon={<SaveOutlined />}
            >
              {mode === 'create' ? '创建资产' : '更新资产'}
            </Button>
            <Button onClick={onCancel}>
              取消
            </Button>
            <Button 
              icon={<ReloadOutlined />} 
              onClick={handleReset}
            >
              重置
            </Button>
          </Space>
        </Card>
      </Form>
    </div>
  )
}

export default AssetForm