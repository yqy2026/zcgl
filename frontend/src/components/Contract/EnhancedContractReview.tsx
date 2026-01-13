/**
 * 增强版合同审核组件
 * 提供智能化的数据审核和编辑功能
 */

import React, { useState, useEffect, useMemo } from 'react';
import {
  Card,
  Form,
  Input,
  Button,
  Space,
  Row,
  Col,
  Tag,
  Table,
  Select,
  DatePicker,
  InputNumber,
  Switch,
  Tooltip,
  Badge,
  Progress,
  Statistic,
  Tabs,
  Typography,
} from 'antd';
import { MessageManager } from '@/utils/messageManager';
import {
  EditOutlined,
  SaveOutlined,
  CheckCircleOutlined,
  SearchOutlined,
  SyncOutlined,
  StarFilled
} from '@ant-design/icons';
import dayjs from 'dayjs';

const { Text } = Typography;
const { TabPane } = Tabs;

// 字段配置类型
interface FieldConfigItem {
  label: string;
  type: 'text' | 'number' | 'phone' | 'date' | 'select';
  required: boolean;
  unit?: string;
}

type FieldConfig = Record<string, FieldConfigItem>;

// 验证结果类型
interface FieldValidation {
  is_valid: boolean;
  errors?: string[];
}

interface ValidationResults {
  validation_results?: Record<string, FieldValidation>;
}

// 匹配结果类型
interface MatchingResults {
  matched_assets?: AssetMatch[];
  matched_ownerships?: {
    landlords?: OwnershipMatch[];
    tenants?: OwnershipMatch[];
  };
}

interface FieldReview {
  fieldName: string;
  label: string;
  value: unknown;
  confidence: number;
  validationStatus: 'valid' | 'warning' | 'error';
  validationMessage?: string;
  suggestedValue?: unknown;
  editMode: boolean;
}

interface AssetMatch {
  id: string;
  property_name: string;
  address: string;
  similarity: number;
  match_reason: string;
}

interface OwnershipMatch {
  id: string;
  ownership_name: string;
  credit_code?: string;
  similarity: number;
  match_reason: string;
}

interface EnhancedContractReviewProps {
  sessionData: Record<string, unknown>;
  onConfirm: (confirmedData: Record<string, unknown>) => void;
  onCancel: () => void;
  onFieldChange?: (fieldName: string, value: unknown) => void;
}

const EnhancedContractReview: React.FC<EnhancedContractReviewProps> = ({
  sessionData,
  onConfirm,
  onCancel,
  onFieldChange
}) => {
  const [form] = Form.useForm();
  const [editingField, setEditingField] = useState<string | null>(null);
  const [fieldReviews, setFieldReviews] = useState<FieldReview[]>([]);
  const [selectedAsset, setSelectedAsset] = useState<string>('');
  const [selectedOwnership, setSelectedOwnership] = useState<string>('');
  const [autoSaveEnabled, setAutoSaveEnabled] = useState(true);
  const [validationSummary, setValidationSummary] = useState<ValidationResults>({});

  useEffect(() => {
    if (sessionData?.extracted_data) {
      initializeFieldReviews();
    }
  }, [sessionData]);

  useEffect(() => {
    if (sessionData?.validation_results) {
      setValidationSummary(sessionData.validation_results);
    }
  }, [sessionData?.validation_results]);

  const initializeFieldReviews = () => {
    const fields: FieldReview[] = [];
    const fieldConfig = getFieldConfig();

    Object.entries(sessionData.extracted_data || {}).forEach(([key, value]) => {
      const config = fieldConfig[key as keyof FieldConfig];
      if (config) {
        fields.push({
          fieldName: key,
          label: config.label,
          value: value,
          confidence: calculateFieldConfidence(key, value, sessionData),
          validationStatus: getValidationStatus(key, value, validationSummary),
          validationMessage: getValidationMessage(key, validationSummary),
          suggestedValue: getSuggestedValue(key, value, sessionData.matching_results as MatchingResults | undefined),
          editMode: false
        });
      }
    });

    setFieldReviews(fields);
  };

  const calculateFieldConfidence = (fieldName: string, value: unknown, sessionData: Record<string, unknown>): number => {
    // 基础置信度
    let confidence = (sessionData.confidence_score as number) || 0.8;

    // 根据字段重要性调整
    const importantFields = ['tenant_name', 'landlord_name', 'monthly_rent', 'property_address'];
    if (importantFields.includes(fieldName)) {
      confidence += 0.1;
    }

    // 根据值的质量调整
    if (value && typeof value === 'string' && value.length > 5) {
      confidence += 0.05;
    }

    return Math.min(confidence, 1.0);
  };

  const getValidationStatus = (fieldName: string, value: unknown, validation: ValidationResults): 'valid' | 'warning' | 'error' => {
    const fieldValidation = validation?.validation_results?.[fieldName];
    if (!fieldValidation) return 'valid';

    if (!fieldValidation.is_valid) {
      return 'error';
    } else if (fieldValidation.errors && fieldValidation.errors.length > 0) {
      return 'warning';
    } else {
      return 'valid';
    }
  };

  const getValidationMessage = (fieldName: string, validation: ValidationResults): string | undefined => {
    const fieldValidation = validation?.validation_results?.[fieldName];
    return fieldValidation?.errors?.[0];
  };

  const getSuggestedValue = (fieldName: string, currentValue: unknown, matching: MatchingResults | undefined): unknown => {
    // 从匹配结果中获取建议值
    if (fieldName === 'property_address' && matching?.matched_assets && matching.matched_assets.length > 0) {
      return matching.matched_assets[0].address;
    }
    if (fieldName === 'landlord_name' && matching?.matched_ownerships?.landlords && matching.matched_ownerships.landlords.length > 0) {
      return matching.matched_ownerships.landlords[0].ownership_name;
    }
    return currentValue;
  };

  const getFieldConfig = (): FieldConfig => ({
    contract_number: { label: '合同编号', type: 'text', required: true },
    landlord_name: { label: '出租方', type: 'text', required: true },
    landlord_legal_rep: { label: '出租方法定代表人', type: 'text', required: false },
    landlord_contact: { label: '出租方联系人', type: 'text', required: false },
    landlord_phone: { label: '出租方电话', type: 'phone', required: true },
    landlord_address: { label: '出租方地址', type: 'text', required: false },
    tenant_name: { label: '承租方', type: 'text', required: true },
    tenant_id: { label: '承租方身份证号', type: 'text', required: true },
    tenant_phone: { label: '承租方电话', type: 'phone', required: true },
    tenant_address: { label: '承租方地址', type: 'text', required: false },
    property_address: { label: '物业地址', type: 'text', required: true },
    property_area: { label: '建筑面积', type: 'number', required: true, unit: '㎡' },
    property_certificate: { label: '权属证号', type: 'text', required: false },
    lease_start_date: { label: '租赁开始日期', type: 'date', required: true },
    lease_end_date: { label: '租赁结束日期', type: 'date', required: true },
    lease_duration_years: { label: '租赁年限', type: 'number', required: true, unit: '年' },
    monthly_rent: { label: '月租金', type: 'number', required: true, unit: '元' },
    security_deposit: { label: '保证金', type: 'number', required: false, unit: '元' },
    management_fee: { label: '管理费', type: 'number', required: false, unit: '元' },
    annual_rent: { label: '年租金', type: 'number', required: false, unit: '元' },
    payment_method: { label: '支付方式', type: 'text', required: false },
    payment_frequency: { label: '支付频率', type: 'select', required: false },
    contract_date: { label: '签订日期', type: 'date', required: true }
  });

  const handleFieldEdit = (fieldName: string) => {
    setEditingField(editingField === fieldName ? null : fieldName);
    setFieldReviews(prev => prev.map(field =>
      field.fieldName === fieldName ? { ...field, editMode: !field.editMode } : field
    ));
  };

  const handleFieldChange = (fieldName: string, value: unknown) => {
    setFieldReviews(prev => prev.map(field =>
      field.fieldName === fieldName ? { ...field, value } : field
    ));

    if (onFieldChange) {
      onFieldChange(fieldName, value);
    }

    // 自动保存
    if (autoSaveEnabled) {
      const timer = setTimeout(() => {
        // 触发自动保存逻辑
        // Auto-save field value
      }, 1000);
      return () => clearTimeout(timer);
    }
  };

  const handleAssetSelection = (assetId: string) => {
    setSelectedAsset(assetId);
    // 更新字段值
    const matchingResults = sessionData.matching_results as MatchingResults | undefined;
    const selectedAssetData = matchingResults?.matched_assets?.find((asset: AssetMatch) => asset.id === assetId);
    if (selectedAssetData) {
      handleFieldChange('property_address', selectedAssetData.address);
    }
  };

  const handleOwnershipSelection = (ownershipId: string, type: 'landlord' | 'tenant') => {
    if (type === 'landlord') {
      setSelectedOwnership(ownershipId);
      const matchingResults = sessionData.matching_results as MatchingResults | undefined;
      const selectedOwnershipData = matchingResults?.matched_ownerships?.landlords?.find((ownership: OwnershipMatch) => ownership.id === ownershipId);
      if (selectedOwnershipData) {
        handleFieldChange('landlord_name', selectedOwnershipData.ownership_name);
      }
    }
  };

  const handleConfirm = () => {
    // 构建确认的数据
    const confirmedData: Record<string, unknown> = {
      ...(sessionData.extracted_data as Record<string, unknown>),
      asset_id: selectedAsset,
      ownership_id: selectedOwnership
    };

    // 验证必填字段
    const requiredFields = ['tenant_name', 'landlord_name', 'monthly_rent', 'property_address'];
    const missingFields = requiredFields.filter(field => !confirmedData[field]);

    if (missingFields.length > 0) {
      MessageManager.error(`请填写必填字段：${missingFields.join(', ')}`);
      return;
    }

    onConfirm(confirmedData);
  };

  // 统计信息
  const statistics = useMemo(() => {
    const totalFields = fieldReviews.length;
    const validFields = fieldReviews.filter(f => f.validationStatus === 'valid').length;
    const warningFields = fieldReviews.filter(f => f.validationStatus === 'warning').length;
    const errorFields = fieldReviews.filter(f => f.validationStatus === 'error').length;
    const avgConfidence = totalFields > 0 ? fieldReviews.reduce((sum, f) => sum + f.confidence, 0) / totalFields : 0;

    return {
      total: totalFields,
      valid: validFields,
      warnings: warningFields,
      errors: errorFields,
      avgConfidence: avgConfidence * 100,
      completionRate: totalFields > 0 ? (validFields / totalFields) * 100 : 0
    };
  }, [fieldReviews]);

  const renderFieldInput = (field: FieldReview) => {
    const config = getFieldConfig()[field.fieldName as keyof FieldConfig];

    switch (config.type) {
      case 'date':
        return (
          <DatePicker
            value={field.value && typeof field.value === 'string' ? dayjs(field.value) : null}
            onChange={(date) => handleFieldChange(field.fieldName, date ? date.format('YYYY-MM-DD') : null)}
            style={{ width: '100%' }}
            placeholder={`请选择${config.label}`}
          />
        );
      case 'number':
        return (
          <InputNumber
            value={typeof field.value === 'number' ? field.value : undefined}
            onChange={(value) => handleFieldChange(field.fieldName, value)}
            style={{ width: '100%' }}
            placeholder={`请输入${config.label}`}
            formatter={value => `${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
            parser={value => Number(value!.replace(/\$\s?|(,*)/g, '')) || 0}
            addonAfter={config.unit}
          />
        );
      case 'select':
        return (
          <Select
            value={field.value as string | undefined}
            onChange={(value) => handleFieldChange(field.fieldName, value)}
            style={{ width: '100%' }}
            placeholder={`请选择${config.label}`}
          >
            <Select.Option value="monthly">按月</Select.Option>
            <Select.Option value="quarterly">按季</Select.Option>
            <Select.Option value="yearly">按年</Select.Option>
          </Select>
        );
      default:
        return (
          <Input
            value={typeof field.value === 'string' ? field.value : String(field.value ?? '')}
            onChange={(e) => handleFieldChange(field.fieldName, e.target.value)}
            placeholder={`请输入${config.label}`}
            suffix={field.suggestedValue && field.suggestedValue !== field.value ? (
              <Tooltip title="建议使用匹配的值">
                <Button
                  type="link"
                  size="small"
                  icon={<CheckCircleOutlined />}
                  onClick={() => handleFieldChange(field.fieldName, field.suggestedValue)}
                />
              </Tooltip>
            ) : undefined}
          />
        );
    }
  };

  const matchingResultsColumns = [
    {
      title: '物业名称',
      dataIndex: 'property_name',
      key: 'property_name',
      width: 200
    },
    {
      title: '地址',
      dataIndex: 'address',
      key: 'address',
      width: 300
    },
    {
      title: '相似度',
      dataIndex: 'similarity',
      key: 'similarity',
      width: 100,
      render: (similarity: number) => (
        <Progress
          percent={similarity * 100}
          size="small"
          status={similarity > 0.8 ? 'success' : similarity > 0.6 ? 'normal' : 'exception'}
          format={() => `${(similarity * 100).toFixed(1)}%`}
        />
      )
    },
    {
      title: '匹配置由',
      dataIndex: 'match_reason',
      key: 'match_reason',
      width: 120
    },
    {
      title: '操作',
      key: 'action',
      width: 100,
      render: (_: any, record: AssetMatch) => (
        <Button
          type="primary"
          size="small"
          onClick={() => handleAssetSelection(record.id)}
        >
          选择
        </Button>
      )
    }
  ];

  return (
    <div className="enhanced-contract-review">
      {/* 统计信息 */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="字段完整性"
              value={statistics.completionRate}
              precision={1}
              suffix="%"
              valueStyle={{ color: statistics.completionRate > 80 ? '#3f8600' : '#cf1322' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="平均置信度"
              value={statistics.avgConfidence}
              precision={1}
              suffix="%"
              prefix={<StarFilled />}
              valueStyle={{ color: statistics.avgConfidence > 70 ? '#3f8600' : '#cf1322' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="验证通过"
              value={statistics.valid}
              suffix={`/ ${statistics.total}`}
              valueStyle={{ color: '#3f8600' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Space>
              <span>自动保存</span>
              <Switch
                checked={autoSaveEnabled}
                onChange={setAutoSaveEnabled}
                size="small"
              />
              <Button
                type="text"
                size="small"
                icon={<SyncOutlined />}
                onClick={() => initializeFieldReviews()}
              >
                重置
              </Button>
            </Space>
          </Card>
        </Col>
      </Row>

      {/* 匹配结果 */}
      {((sessionData as any).matching_results?.matched_assets?.length > 0 ||
        (sessionData as any).matching_results?.matched_ownerships?.landlords?.length > 0) && (
          <Card
            title={
              <Space>
                <SearchOutlined />
                <span>智能匹配结果</span>
                <Badge count={(sessionData as any).matching_results?.matched_assets?.length || 0} />
              </Space>
            }
            style={{ marginBottom: 24 }}
          >
            <Tabs defaultActiveKey="assets">
              <TabPane tab="资产匹配" key="assets">
                <Table
                  columns={matchingResultsColumns}
                  dataSource={(sessionData as any).matching_results?.matched_assets || []}
                  rowKey="id"
                  pagination={false}
                  size="small"
                />
              </TabPane>
              <TabPane tab="权属方匹配" key="ownerships">
                <Table
                  columns={[
                    ...matchingResultsColumns.slice(0, -1) as any,
                    {
                      title: '操作',
                      key: 'action',
                      render: (_: any, record: OwnershipMatch) => (
                        <Button
                          type="primary"
                          size="small"
                          onClick={() => handleOwnershipSelection(record.id, 'landlord')}
                        >
                          选择
                        </Button>
                      )
                    }
                  ] as any}
                  dataSource={(sessionData as any).matching_results?.matched_ownerships?.landlords || []}
                  rowKey="id"
                  pagination={false}
                  size="small"
                />
              </TabPane>
            </Tabs>
          </Card>
        )}

      {/* 字段编辑 */}
      <Card
        title={
          <Space>
            <EditOutlined />
            <span>字段审核与编辑</span>
            <Badge count={statistics.errors} status="error" />
          </Space>
        }
      >
        <Form form={form} layout="vertical">
          <Row gutter={16}>
            {fieldReviews.map((field) => (
              <Col span={12} key={field.fieldName} style={{ marginBottom: 16 }}>
                <Form.Item
                  label={
                    <Space>
                      <span>{field.label}</span>
                      <Tag color={field.validationStatus === 'valid' ? 'green' :
                        field.validationStatus === 'warning' ? 'orange' : 'red'}>
                        {field.validationStatus === 'valid' ? '有效' :
                          field.validationStatus === 'warning' ? '警告' : '错误'}
                      </Tag>
                      <Tooltip title={`置信度: ${(field.confidence * 100).toFixed(1)}%`}>
                        <Progress
                          percent={field.confidence * 100}
                          size="small"
                          strokeColor={field.confidence > 0.8 ? '#52c41a' : '#faad14'}
                          format={() => ''}
                          style={{ width: 60 }}
                        />
                      </Tooltip>
                    </Space>
                  }
                  validateStatus={field.validationStatus === 'error' ? 'error' :
                    field.validationStatus === 'warning' ? 'warning' : undefined}
                  help={field.validationMessage}
                  extra={
                    <Button
                      type="text"
                      size="small"
                      icon={field.editMode ? <SaveOutlined /> : <EditOutlined />}
                      onClick={() => handleFieldEdit(field.fieldName)}
                    >
                      {field.editMode ? '保存' : '编辑'}
                    </Button>
                  }
                >
                  {field.editMode ? (
                    renderFieldInput(field)
                  ) : (
                    <div onClick={() => handleFieldEdit(field.fieldName)}>
                      {(() => {
                        const val = field.value
                        if (!val) return <Text type="secondary" italic>未提取</Text>
                        if (typeof val === 'object' && Object.keys(val).length === 0) {
                          return <Text type="secondary" italic>未提取</Text>
                        }
                        return val as any
                      })()}
                    </div>
                  )}
                </Form.Item>
              </Col>
            ))}
          </Row>
        </Form>
      </Card>

      {/* 操作按钮 */}
      <Card style={{ textAlign: 'center', marginTop: 24 }}>
        <Space size="large">
          <Button size="large" onClick={onCancel}>
            取消导入
          </Button>
          <Button
            type="primary"
            size="large"
            icon={<CheckCircleOutlined />}
            onClick={handleConfirm}
            disabled={statistics.errors > 0}
          >
            确认导入
          </Button>
        </Space>
      </Card>
    </div>
  );
};

export default EnhancedContractReview;
