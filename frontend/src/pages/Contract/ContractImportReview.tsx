/**
 * PDF合同信息确认界面
 */

import React, { useState, useEffect } from 'react';
import {
  Card,
  Form,
  Input,
  Select,
  DatePicker,
  InputNumber,
  Button,
  Space,
  Alert,
  Row,
  Col,
  Tag,
  Typography,
  Tabs,
  message,
  Statistic,
  Switch
} from 'antd';
import {
  SaveOutlined
} from '@ant-design/icons';
import dayjs from 'dayjs';

import {
  type CompleteResult,
  type ConfirmedContractData,
  type ConfirmImportResponse,
  type AssetMatch,
  type OwnershipMatch
} from '../../services/pdfImportService';

const { Title } = Typography;
const { TabPane } = Tabs;
const { TextArea } = Input;

interface ContractImportReviewProps {
  sessionId: string;
  result: CompleteResult;
  onConfirm: (data: ConfirmedContractData) => Promise<ConfirmImportResponse>;
  onCancel: () => void;
  onBack: () => void;
}

const ContractImportReview: React.FC<ContractImportReviewProps> = ({
  result,
  onConfirm,
  onBack
}) => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [modifiedFields, setModifiedFields] = useState<Set<string>>(new Set());
  const [activeTab, setActiveTab] = useState('basic');
  const [showAdvancedFields, setShowAdvancedFields] = useState(false);

  // 初始化表单数据
  useEffect(() => {
    const validatedData = result.validation_result.validated_data;
    const recommendations = result.matching_result.recommendations;

    // 设置表单初始值 - 确保数字字段正确转换
    form.setFieldsValue({
      contract_number: validatedData.contract_number || '',
      asset_id: recommendations.asset_id || '',
      ownership_id: recommendations.ownership_id || '',
      tenant_name: validatedData.tenant_name || '',
      tenant_contact: validatedData.tenant_contact || '',
      sign_date: validatedData.sign_date ? dayjs(String(validatedData.sign_date)) : null,
      start_date: validatedData.start_date ? dayjs(String(validatedData.start_date)) : null,
      end_date: validatedData.end_date ? dayjs(String(validatedData.end_date)) : null,
      rentable_area: validatedData.rentable_area ? parseFloat(String(validatedData.rentable_area)) : undefined,
      monthly_rent: validatedData.monthly_rent ? parseFloat(String(validatedData.monthly_rent)) : undefined,
      total_deposit: validatedData.total_deposit ? parseFloat(String(validatedData.total_deposit)) : 0,
      contract_status: validatedData.contract_status || '有效',
      payment_terms: validatedData.payment_terms || '',
      contract_notes: validatedData.contract_notes || '',
      rent_terms: validatedData.rent_terms || []
    });

  }, [result, form]);

  // 表单字段变更接口
interface FormFieldChange {
  name: string[];
  value: unknown;
  touched?: boolean;
  validating?: boolean;
}

// 表单字段变更处理
  const handleFieldChange = (changedFields: FormFieldChange[]) => {
    // 标记已修改的字段
    const newModifiedFields = new Set(modifiedFields);
    changedFields.forEach((field: FormFieldChange) => {
      if (field.name) {
        newModifiedFields.add(field.name[0]);
      }
    });
    setModifiedFields(newModifiedFields);
  };

  // 确认导入
  const handleConfirm = async () => {
    try {
      const values = await form.validateFields();

      // 转换日期格式
      const confirmedData: ConfirmedContractData = {
        ...values,
        sign_date: values.sign_date ? values.sign_date.format('YYYY-MM-DD') : undefined,
        start_date: values.start_date ? values.start_date.format('YYYY-MM-DD') : '',
        end_date: values.end_date ? values.end_date.format('YYYY-MM-DD') : '',
        monthly_rent: values.monthly_rent?.toString() || '',
        total_deposit: values.total_deposit?.toString() || '0'
      };

      setLoading(true);
      const response = await onConfirm(confirmedData);

      if (response.success) {
        message.success('合同导入成功！');
        // 可以在这里添加跳转逻辑
      } else {
        message.error(response.error || '导入失败');
      }
    } catch (error: unknown) {
      console.error('表单验证失败:', error);
      const _errorMessage = error instanceof Error ? error.message : '表单验证失败';
      message.error('请检查表单填写是否正确');
    } finally {
      setLoading(false);
    }
  };

  // 获取置信度颜色
  const getConfidenceColor = (score: number): string => {
    if (score >= 0.9) return '#52c41a';
    if (score >= 0.7) return '#faad14';
    return '#ff4d4f';
  };

  
  // 基本信息表单
  const BasicInfoForm = () => (
    <Form
      form={form}
      layout="vertical"
      onValuesChange={handleFieldChange}
    >
      <Row gutter={16}>
        <Col span={12}>
          <Form.Item
            label={
              <Space>
                <span>合同编号</span>
                {!!result.extraction_result.data.contract_number && (
                  <Tag color="blue">自动提取</Tag>
                )}
              </Space>
            }
            name="contract_number"
            rules={[{ required: true, message: '请输入合同编号' }]}
          >
            <Input placeholder="请输入合同编号" />
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item
            label={
              <Space>
                <span>承租方名称</span>
                {!!result.extraction_result.data.tenant_name && (
                  <Tag color="blue">自动提取</Tag>
                )}
              </Space>
            }
            name="tenant_name"
            rules={[{ required: true, message: '请输入承租方名称' }]}
          >
            <Input placeholder="请输入承租方名称" />
          </Form.Item>
        </Col>
      </Row>

      <Row gutter={16}>
        <Col span={12}>
          <Form.Item
            label={
              <Space>
                <span>承租方联系方式</span>
                {!!result.extraction_result.data.tenant_contact && (
                  <Tag color="blue">自动提取</Tag>
                )}
              </Space>
            }
            name="tenant_contact"
          >
            <Input placeholder="请输入承租方联系方式" />
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item
            label={
              <Space>
                <span>合同状态</span>
                {!!result.extraction_result.data.contract_status && (
                  <Tag color="blue">自动提取</Tag>
                )}
              </Space>
            }
            name="contract_status"
          >
            <Select placeholder="请选择合同状态">
              <Select.Option value="有效">有效</Select.Option>
              <Select.Option value="生效">生效</Select.Option>
              <Select.Option value="到期">到期</Select.Option>
              <Select.Option value="终止">终止</Select.Option>
              <Select.Option value="暂停">暂停</Select.Option>
            </Select>
          </Form.Item>
        </Col>
      </Row>
    </Form>
  );

  // 日期和金额表单
  const DateAmountForm = () => (
    <Form
      form={form}
      layout="vertical"
      onValuesChange={handleFieldChange}
    >
      <Row gutter={16}>
        <Col span={8}>
          <Form.Item
            label={
              <Space>
                <span>签订日期</span>
                {!!result.extraction_result.data.sign_date && (
                  <Tag color="blue">自动提取</Tag>
                )}
              </Space>
            }
            name="sign_date"
          >
            <DatePicker style={{ width: '100%' }} placeholder="请选择签订日期" />
          </Form.Item>
        </Col>
        <Col span={8}>
          <Form.Item
            label={
              <Space>
                <span>开始日期</span>
                {!!result.extraction_result.data.start_date && (
                  <Tag color="blue">自动提取</Tag>
                )}
              </Space>
            }
            name="start_date"
            rules={[{ required: true, message: '请选择开始日期' }]}
          >
            <DatePicker style={{ width: '100%' }} placeholder="请选择开始日期" />
          </Form.Item>
        </Col>
        <Col span={8}>
          <Form.Item
            label={
              <Space>
                <span>结束日期</span>
                {!!result.extraction_result.data.end_date && (
                  <Tag color="blue">自动提取</Tag>
                )}
              </Space>
            }
            name="end_date"
            rules={[{ required: true, message: '请选择结束日期' }]}
          >
            <DatePicker style={{ width: '100%' }} placeholder="请选择结束日期" />
          </Form.Item>
        </Col>
      </Row>

      <Row gutter={16}>
        <Col span={8}>
          <Form.Item
            label={
              <Space>
                <span>租赁面积(㎡)</span>
                {!!result.extraction_result.data.rentable_area && (
                  <Tag color="blue">自动提取</Tag>
                )}
              </Space>
            }
            name="rentable_area"
          >
            <InputNumber
              style={{ width: '100%' }}
              placeholder="请输入租赁面积"
              min={0}
              precision={2}
              formatter={(value) => `${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
            />
          </Form.Item>
        </Col>
        <Col span={8}>
          <Form.Item
            label={
              <Space>
                <span>月租金(元)</span>
                {!!result.extraction_result.data.monthly_rent && (
                  <Tag color="blue">自动提取</Tag>
                )}
              </Space>
            }
            name="monthly_rent"
            rules={[{ required: true, message: '请输入月租金' }]}
          >
            <InputNumber
              style={{ width: '100%' }}
              placeholder="请输入月租金"
              min={0}
              precision={2}
              formatter={(value) => `${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
            />
          </Form.Item>
        </Col>
        <Col span={8}>
          <Form.Item
            label={
              <Space>
                <span>押金(元)</span>
                {!!result.extraction_result.data.total_deposit && (
                  <Tag color="blue">自动提取</Tag>
                )}
              </Space>
            }
            name="total_deposit"
          >
            <InputNumber
              style={{ width: '100%' }}
              placeholder="请输入押金金额"
              min={0}
              precision={2}
              defaultValue={0}
              formatter={(value) => `${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
            />
          </Form.Item>
        </Col>
      </Row>
    </Form>
  );

  // 匹配结果表单
  const MatchingForm = () => (
    <div>
      {/* 资产匹配 */}
      <div style={{ marginBottom: 16 }}>
        <Title level={5}>
          资产匹配
          {result.matching_result.matched_assets.length > 0 && (
            <Tag color="green" style={{ marginLeft: 8 }}>
              找到 {result.matching_result.matched_assets.length} 个匹配项
            </Tag>
          )}
        </Title>

        {result.matching_result.matched_assets.length > 0 ? (
          <Form.Item
            label="选择资产"
            name="asset_id"
            rules={[{ required: true, message: '请选择关联的资产' }]}
          >
            <Select
              placeholder="请选择匹配的资产"
              showSearch
              filterOption={(input, option) =>
                String(option?.children || '').toLowerCase().includes(input.toLowerCase())
              }
            >
              {result.matching_result.matched_assets.map((asset: AssetMatch) => (
                <Select.Option key={asset.id} value={asset.id}>
                  <div>
                    <Space>
                      <span>{asset.property_name}</span>
                      <Tag color={asset.similarity >= 80 ? 'green' : asset.similarity >= 60 ? 'orange' : 'red'}>
                        相似度: {asset.similarity}%
                      </Tag>
                    </Space>
                    <div style={{ fontSize: 12, color: '#666', marginTop: 4 }}>
                      {asset.address}
                    </div>
                  </div>
                </Select.Option>
              ))}
            </Select>
          </Form.Item>
        ) : (
          <Alert
            message="未找到匹配的资产"
            description="请手动选择或创建新的资产记录"
            type="warning"
            showIcon
          />
        )}
      </div>

      {/* 权属方匹配 */}
      <div>
        <Title level={5}>
          权属方匹配
          {result.matching_result.matched_ownerships.length > 0 && (
            <Tag color="green" style={{ marginLeft: 8 }}>
              找到 {result.matching_result.matched_ownerships.length} 个匹配项
            </Tag>
          )}
        </Title>

        {result.matching_result.matched_ownerships.length > 0 ? (
          <Form.Item
            label="选择权属方"
            name="ownership_id"
            rules={[{ required: true, message: '请选择关联的权属方' }]}
          >
            <Select
              placeholder="请选择匹配的权属方"
              showSearch
              filterOption={(input, option) =>
                String(option?.children || '').toLowerCase().includes(input.toLowerCase())
              }
            >
              {result.matching_result.matched_ownerships.map((ownership: OwnershipMatch) => (
                <Select.Option key={ownership.id} value={ownership.id}>
                  <Space>
                    <span>{ownership.ownership_name}</span>
                    <Tag color={ownership.similarity >= 80 ? 'green' : ownership.similarity >= 60 ? 'orange' : 'red'}>
                      相似度: {ownership.similarity}%
                    </Tag>
                  </Space>
                </Select.Option>
              ))}
            </Select>
          </Form.Item>
        ) : (
          <Alert
            message="未找到匹配的权属方"
            description="请手动选择或创建新的权属方记录"
            type="warning"
            showIcon
          />
        )}
      </div>
    </div>
  );

  // 高级字段表单
  const AdvancedForm = () => (
    <Form
      form={form}
      layout="vertical"
      onValuesChange={handleFieldChange}
    >
      <Form.Item
        label={
          <Space>
            <span>支付条款</span>
            {!!result.extraction_result.data.payment_terms && (
              <Tag color="blue">自动提取</Tag>
            )}
          </Space>
        }
        name="payment_terms"
      >
        <TextArea rows={3} placeholder="请输入支付条款" />
      </Form.Item>

      <Form.Item
        label={
          <Space>
            <span>合同备注</span>
            {!!result.extraction_result.data.contract_notes && (
              <Tag color="blue">自动提取</Tag>
            )}
          </Space>
        }
        name="contract_notes"
      >
        <TextArea rows={3} placeholder="请输入合同备注" />
      </Form.Item>
    </Form>
  );

  return (
    <div className="contract-import-review">
      {/* 头部统计 */}
      <Card style={{ marginBottom: 16 }}>
        <Row gutter={16}>
          <Col span={6}>
            <Statistic
              title="提取可信度"
              value={result.summary.extraction_confidence}
              precision={2}
              suffix="%"
              valueStyle={{ color: getConfidenceColor(result.summary.extraction_confidence) }}
            />
          </Col>
          <Col span={6}>
            <Statistic
              title="验证评分"
              value={result.summary.validation_score}
              precision={2}
              suffix="%"
              valueStyle={{ color: getConfidenceColor(result.summary.validation_score) }}
            />
          </Col>
          <Col span={6}>
            <Statistic
              title="匹配置信度"
              value={result.summary.match_confidence}
              precision={2}
              suffix="%"
              valueStyle={{ color: getConfidenceColor(result.summary.match_confidence) }}
            />
          </Col>
          <Col span={6}>
            <Statistic
              title="总体评分"
              value={result.summary.total_confidence}
              precision={2}
              suffix="%"
              valueStyle={{ color: getConfidenceColor(result.summary.total_confidence) }}
            />
          </Col>
        </Row>
      </Card>

      {/* 建议信息 */}
      {result.recommendations.length > 0 && (
        <Alert
          message="系统建议"
          description={
            <ul>
              {result.recommendations.map((recommendation, index) => (
                <li key={index}>{recommendation}</li>
              ))}
            </ul>
          }
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
        />
      )}

      {/* 验证错误和警告 */}
      {result.validation_result.errors.length > 0 && (
        <Alert
          message="验证错误"
          description={
            <ul>
              {result.validation_result.errors.map((error, index) => (
                <li key={index}>{error}</li>
              ))}
            </ul>
          }
          type="error"
          showIcon
          style={{ marginBottom: 16 }}
        />
      )}

      {result.validation_result.warnings.length > 0 && (
        <Alert
          message="验证警告"
          description={
            <ul>
              {result.validation_result.warnings.map((warning, index) => (
                <li key={index}>{warning}</li>
              ))}
            </ul>
          }
          type="warning"
          showIcon
          style={{ marginBottom: 16 }}
        />
      )}

      {/* 主表单 */}
      <Card title="合同信息确认">
        <Tabs activeKey={activeTab} onChange={setActiveTab}>
          <TabPane tab="基本信息" key="basic">
            <BasicInfoForm />
          </TabPane>
          <TabPane tab="日期和金额" key="dates">
            <DateAmountForm />
          </TabPane>
          <TabPane tab="数据匹配" key="matching">
            <MatchingForm />
          </TabPane>
          <TabPane tab={`高级字段${showAdvancedFields ? '' : ' (展开)'}`} key="advanced">
            <div style={{ marginBottom: 16 }}>
              <Switch
                checked={showAdvancedFields}
                onChange={setShowAdvancedFields}
                checkedChildren="显示高级字段"
                unCheckedChildren="隐藏高级字段"
              />
            </div>
            {showAdvancedFields && <AdvancedForm />}
          </TabPane>
        </Tabs>
      </Card>

      {/* 操作按钮 */}
      <div style={{ textAlign: 'center', marginTop: 24 }}>
        <Space size="large">
          <Button size="large" onClick={onBack}>
            返回
          </Button>
          <Button
            size="large"
            type="primary"
            icon={<SaveOutlined />}
            loading={loading}
            onClick={handleConfirm}
            disabled={result.validation_result.errors.length > 0}
          >
            确认导入
          </Button>
        </Space>
      </div>
    </div>
  );
};

export default ContractImportReview;