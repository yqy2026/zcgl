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
  Statistic,
  Switch,
  Popover,
} from 'antd';
import { SaveOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import { MessageManager } from '@/utils/messageManager';

import {
  type CompleteResult,
  type ConfirmedContractData,
  type ConfirmImportResponse,
  type AssetMatch,
  type OwnershipMatch,
} from '@/services/pdfImportService';
import { ContractStatus, ContractStatusLabels } from '@/types/rentContract';
import { COLORS } from '@/styles/colorMap';

const { Title, Text } = Typography;
const { TabPane } = Tabs;
const { TextArea } = Input;

interface ContractImportReviewProps {
  sessionId: string;
  result: CompleteResult;
  onConfirm: (data: ConfirmedContractData) => Promise<ConfirmImportResponse>;
  onCancel: () => void;
  onBack: () => void;
}

interface FormValues {
  contract_number: string;
  asset_id?: string;
  ownership_id?: string;
  tenant_name: string;
  tenant_contact?: string;
  tenant_phone?: string;
  tenant_address?: string;
  sign_date?: dayjs.Dayjs;
  start_date?: dayjs.Dayjs;
  end_date?: dayjs.Dayjs;
  rentable_area?: number;
  monthly_rent?: number;
  total_deposit?: number;
  contract_status?: string;
  payment_terms?: string;
  contract_notes?: string;
  rent_terms?: Array<{
    start_date: string;
    end_date: string;
    monthly_rent: string;
    rent_description?: string;
  }>;
}

interface EvidenceSnippet {
  snippet?: string;
  match?: string;
  match_type?: string;
  source?: string;
}

const ContractImportReview: React.FC<ContractImportReviewProps> = ({
  result,
  onConfirm,
  onBack,
}) => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [modifiedFields, setModifiedFields] = useState<Set<string>>(new Set());
  const [activeTab, setActiveTab] = useState('basic');
  const [showAdvancedFields, setShowAdvancedFields] = useState(false);

  const fieldEvidence = result.extraction_result.field_evidence ?? undefined;
  const fieldSources = result.extraction_result.field_sources ?? undefined;

  const hasExtractedValue = (fieldKey: string): boolean => {
    const value = (result.extraction_result.data as Record<string, unknown>)[fieldKey];
    if (value == null) {
      return false;
    }
    if (typeof value === 'string') {
      return value.trim() !== '';
    }
    if (Array.isArray(value)) {
      return value.length > 0;
    }
    return true;
  };

  const getEvidenceSnippet = (fieldKey: string): EvidenceSnippet | null => {
    if (fieldEvidence == null) {
      return null;
    }
    const rawEvidence = (fieldEvidence as Record<string, unknown>)[fieldKey];
    if (rawEvidence == null || Array.isArray(rawEvidence) || typeof rawEvidence !== 'object') {
      return null;
    }
    return rawEvidence as EvidenceSnippet;
  };

  const resolveSourceLabel = (sourceKey?: string): string => {
    if (sourceKey == null || sourceKey.trim() === '') {
      return '未知';
    }
    const labels: Record<string, string> = {
      ocr_llm: 'OCR+大模型',
      ocr_regex: 'OCR+正则',
      vision: '视觉模型',
      regex: '正则',
      text: '文本解析',
      smart: '智能合并',
    };
    return labels[sourceKey] ?? sourceKey;
  };

  const renderEvidenceTag = (fieldKey: string) => {
    const evidence = getEvidenceSnippet(fieldKey);
    const evidenceSource = evidence?.source;
    const mappedSource = fieldSources != null ? (fieldSources as Record<string, unknown>)[fieldKey] : undefined;
    const sourceKey =
      typeof evidenceSource === 'string' && evidenceSource.trim() !== ''
        ? evidenceSource
        : typeof mappedSource === 'string' && mappedSource.trim() !== ''
          ? mappedSource
          : undefined;
    const snippet = evidence?.snippet;
    const hasSnippet = typeof snippet === 'string' && snippet.trim() !== '';
    const matchValue = evidence?.match;
    const hasMatch = matchValue != null && String(matchValue).trim() !== '';

    if (!hasSnippet && !hasMatch && sourceKey == null) {
      return null;
    }

    const content = (
      <div style={{ maxWidth: 420 }}>
        <Text type="secondary" style={{ display: 'block', marginBottom: 4 }}>
          来源: {resolveSourceLabel(sourceKey)}
        </Text>
        {hasSnippet ? (
          <Text style={{ whiteSpace: 'pre-wrap' }}>{snippet}</Text>
        ) : (
          <Text type="secondary">未提供原文片段</Text>
        )}
        {hasMatch && (
          <Text type="secondary" style={{ display: 'block', marginTop: 8 }}>
            匹配: {String(matchValue)}
          </Text>
        )}
        {evidence?.match_type != null && String(evidence.match_type).trim() !== '' && (
          <Text type="secondary" style={{ display: 'block' }}>
            匹配类型: {String(evidence.match_type)}
          </Text>
        )}
      </div>
    );

    return (
      <Popover content={content} title="提取证据" placement="topLeft">
        <Tag color="geekblue">证据</Tag>
      </Popover>
    );
  };

  const renderFieldLabel = (label: string, fieldKey: string) => (
    <Space size={6} wrap>
      <span>{label}</span>
      {hasExtractedValue(fieldKey) && <Tag color="blue">自动提取</Tag>}
      {renderEvidenceTag(fieldKey)}
    </Space>
  );

  // 初始化表单数据
  useEffect(() => {
    const validatedData = result.validation_result.validated_data;
    const recommendations = result.matching_result.recommendations;

    // 设置表单初始值 - 确保数字字段正确转换
    form.setFieldsValue({
      contract_number: validatedData.contract_number ?? '',
      asset_id: recommendations.asset_id ?? '',
      ownership_id: recommendations.ownership_id ?? '',
      tenant_name: validatedData.tenant_name ?? '',
      tenant_contact: validatedData.tenant_contact ?? '',
      sign_date: validatedData.sign_date != null ? dayjs(String(validatedData.sign_date)) : null,
      start_date: validatedData.start_date != null ? dayjs(String(validatedData.start_date)) : null,
      end_date: validatedData.end_date != null ? dayjs(String(validatedData.end_date)) : null,
      rentable_area:
        validatedData.rentable_area != null
          ? parseFloat(String(validatedData.rentable_area))
          : undefined,
      monthly_rent:
        validatedData.monthly_rent != null
          ? parseFloat(String(validatedData.monthly_rent))
          : undefined,
      total_deposit:
        validatedData.total_deposit != null ? parseFloat(String(validatedData.total_deposit)) : 0,
      contract_status: validatedData.contract_status ?? ContractStatus.ACTIVE,
      payment_terms: validatedData.payment_terms ?? '',
      contract_notes: validatedData.contract_notes ?? '',
      rent_terms: validatedData.rent_terms ?? [],
    });
  }, [result, form]);

  // 表单字段变更处理
  const handleFieldChange = (changedValues: Record<string, unknown>) => {
    // 标记已修改的字段
    const newModifiedFields = new Set(modifiedFields);
    Object.keys(changedValues).forEach((fieldName: string) => {
      newModifiedFields.add(fieldName);
    });
    setModifiedFields(newModifiedFields);
  };

  // 确认导入
  const handleConfirm = async () => {
    try {
      const values = (await form.validateFields()) as FormValues;

      // 转换日期格式
      const confirmedData: ConfirmedContractData = {
        contract_number: values.contract_number,
        asset_id: values.asset_id,
        ownership_id: values.ownership_id,
        tenant_name: values.tenant_name,
        tenant_contact: values.tenant_contact,
        tenant_phone: values.tenant_phone,
        tenant_address: values.tenant_address,
        sign_date: values.sign_date != null ? values.sign_date.format('YYYY-MM-DD') : undefined,
        start_date: values.start_date != null ? values.start_date.format('YYYY-MM-DD') : '',
        end_date: values.end_date != null ? values.end_date.format('YYYY-MM-DD') : '',
        monthly_rent_base: values.monthly_rent?.toString() ?? '',
        total_deposit: values.total_deposit?.toString() ?? '0',
        contract_status: values.contract_status,
        payment_terms: values.payment_terms,
        contract_notes: values.contract_notes,
        rent_terms:
          values.rent_terms?.map(term => ({
            start_date: term.start_date,
            end_date: term.end_date,
            monthly_rent: term.monthly_rent,
            rent_description: term.rent_description,
          })) ?? [],
      };

      setLoading(true);
      const response = await onConfirm(confirmedData);

      if (response.success) {
        MessageManager.success('合同导入成功！');
        // 可以在这里添加跳转逻辑
      } else {
        MessageManager.error(response.error ?? '导入失败');
      }
    } catch (error: unknown) {
      // eslint-disable-next-line no-console
      console.error('表单验证失败:', error);
      const _errorMessage = error instanceof Error ? error.message : '表单验证失败';
      MessageManager.error('请检查表单填写是否正确');
    } finally {
      setLoading(false);
    }
  };

  // 获取置信度颜色
  const getConfidenceColor = (score: number): string => {
    if (score >= 0.9) return COLORS.success;
    if (score >= 0.7) return COLORS.warning;
    return COLORS.error;
  };

  // 基本信息表单
  const BasicInfoForm = () => (
    <Form form={form} layout="vertical" onValuesChange={handleFieldChange}>
      <Row gutter={16}>
        <Col span={12}>
          <Form.Item
            label={renderFieldLabel('合同编号', 'contract_number')}
            name="contract_number"
            rules={[{ required: true, message: '请输入合同编号' }]}
          >
            <Input placeholder="请输入合同编号" />
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item
            label={renderFieldLabel('承租方名称', 'tenant_name')}
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
            label={renderFieldLabel('承租方联系方式', 'tenant_contact')}
            name="tenant_contact"
          >
            <Input placeholder="请输入承租方联系方式" />
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item
            label={renderFieldLabel('合同状态', 'contract_status')}
            name="contract_status"
          >
            <Select placeholder="请选择合同状态">
              {Object.values(ContractStatus).map(status => (
                <Select.Option key={status} value={status}>
                  {ContractStatusLabels[status]}
                </Select.Option>
              ))}
            </Select>
          </Form.Item>
        </Col>
      </Row>
    </Form>
  );

  // 日期和金额表单
  const DateAmountForm = () => (
    <Form form={form} layout="vertical" onValuesChange={handleFieldChange}>
      <Row gutter={16}>
        <Col span={8}>
          <Form.Item
            label={renderFieldLabel('签订日期', 'sign_date')}
            name="sign_date"
          >
            <DatePicker style={{ width: '100%' }} placeholder="请选择签订日期" />
          </Form.Item>
        </Col>
        <Col span={8}>
          <Form.Item
            label={renderFieldLabel('开始日期', 'start_date')}
            name="start_date"
            rules={[{ required: true, message: '请选择开始日期' }]}
          >
            <DatePicker style={{ width: '100%' }} placeholder="请选择开始日期" />
          </Form.Item>
        </Col>
        <Col span={8}>
          <Form.Item
            label={renderFieldLabel('结束日期', 'end_date')}
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
            label={renderFieldLabel('租赁面积(㎡)', 'rentable_area')}
            name="rentable_area"
          >
            <InputNumber
              style={{ width: '100%' }}
              placeholder="请输入租赁面积"
              min={0}
              precision={2}
              formatter={value => `${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
            />
          </Form.Item>
        </Col>
        <Col span={8}>
          <Form.Item
            label={renderFieldLabel('月租金(元)', 'monthly_rent')}
            name="monthly_rent"
            rules={[{ required: true, message: '请输入月租金' }]}
          >
            <InputNumber
              style={{ width: '100%' }}
              placeholder="请输入月租金"
              min={0}
              precision={2}
              formatter={value => `${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
            />
          </Form.Item>
        </Col>
        <Col span={8}>
          <Form.Item
            label={renderFieldLabel('押金(元)', 'total_deposit')}
            name="total_deposit"
          >
            <InputNumber
              style={{ width: '100%' }}
              placeholder="请输入押金金额"
              min={0}
              precision={2}
              defaultValue={0}
              formatter={value => `${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
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
                String(option?.children || '')
                  .toLowerCase()
                  .includes(input.toLowerCase())
              }
            >
              {result.matching_result.matched_assets.map((asset: AssetMatch) => (
                <Select.Option key={asset.id} value={asset.id}>
                  <div>
                    <Space>
                      <span>{asset.property_name}</span>
                      <Tag
                        color={
                          asset.similarity >= 80
                            ? 'green'
                            : asset.similarity >= 60
                              ? 'orange'
                              : 'red'
                        }
                      >
                        相似度: {asset.similarity}%
                      </Tag>
                    </Space>
                    <div style={{ fontSize: 12, color: COLORS.textSecondary, marginTop: 4 }}>
                      {asset.address}
                    </div>
                  </div>
                </Select.Option>
              ))}
            </Select>
          </Form.Item>
        ) : (
          <Alert
            title="未找到匹配的资产"
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
                String(option?.children || '')
                  .toLowerCase()
                  .includes(input.toLowerCase())
              }
            >
              {result.matching_result.matched_ownerships.map((ownership: OwnershipMatch) => (
                <Select.Option key={ownership.id} value={ownership.id}>
                  <Space>
                    <span>{ownership.ownership_name}</span>
                    <Tag
                      color={
                        ownership.similarity >= 80
                          ? 'green'
                          : ownership.similarity >= 60
                            ? 'orange'
                            : 'red'
                      }
                    >
                      相似度: {ownership.similarity}%
                    </Tag>
                  </Space>
                </Select.Option>
              ))}
            </Select>
          </Form.Item>
        ) : (
          <Alert
            title="未找到匹配的权属方"
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
    <Form form={form} layout="vertical" onValuesChange={handleFieldChange}>
      <Form.Item
        label={renderFieldLabel('支付条款', 'payment_terms')}
        name="payment_terms"
      >
        <TextArea rows={3} placeholder="请输入支付条款" />
      </Form.Item>

      <Form.Item
        label={renderFieldLabel('合同备注', 'contract_notes')}
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
              styles={{ content: { color: getConfidenceColor(result.summary.extraction_confidence) } }}
            />
          </Col>
          <Col span={6}>
            <Statistic
              title="验证评分"
              value={result.summary.validation_score}
              precision={2}
              suffix="%"
              styles={{ content: { color: getConfidenceColor(result.summary.validation_score) } }}
            />
          </Col>
          <Col span={6}>
            <Statistic
              title="匹配置信度"
              value={result.summary.match_confidence}
              precision={2}
              suffix="%"
              styles={{ content: { color: getConfidenceColor(result.summary.match_confidence) } }}
            />
          </Col>
          <Col span={6}>
            <Statistic
              title="总体评分"
              value={result.summary.total_confidence}
              precision={2}
              suffix="%"
              styles={{ content: { color: getConfidenceColor(result.summary.total_confidence) } }}
            />
          </Col>
        </Row>
      </Card>

      {/* 建议信息 */}
      {result.recommendations.length > 0 && (
        <Alert
          title="系统建议"
          description={
            <ul>
              {result.recommendations.map(recommendation => (
                <li key={recommendation}>{recommendation}</li>
              ))}
            </ul>
          }
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
        />
      )}

      {result.extraction_result.warnings != null &&
        result.extraction_result.warnings.length > 0 && (
          <Alert
            title="提取警告"
            description={
              <ul>
                {result.extraction_result.warnings.map(warning => (
                  <li key={warning}>{warning}</li>
                ))}
              </ul>
            }
            type="warning"
            showIcon
            style={{ marginBottom: 16 }}
          />
        )}

      {/* 验证错误和警告 */}
      {result.validation_result.errors.length > 0 && (
        <Alert
          title="验证错误"
          description={
            <ul>
              {result.validation_result.errors.map(error => (
                <li key={error}>{error}</li>
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
          title="验证警告"
          description={
            <ul>
              {result.validation_result.warnings.map(warning => (
                <li key={warning}>{warning}</li>
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
