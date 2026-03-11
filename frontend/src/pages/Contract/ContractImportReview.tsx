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
import { useNavigate } from 'react-router-dom';
import { MessageManager } from '@/utils/messageManager';
import { createLogger } from '@/utils/logger';

import {
  type CompleteResult,
  type ConfirmedContractData,
  type ConfirmImportResponse,
  type AssetMatch,
  type OwnershipMatch,
} from '@/services/pdfImportService';
import { CONTRACT_GROUP_ROUTES } from '@/constants/routes';
import { ContractStatus, ContractStatusLabels } from '@/types/rentContract';
import styles from './ContractImportReview.module.css';

const { Title, Text } = Typography;
const { TextArea } = Input;
const pageLogger = createLogger('ContractImportReview');

type ConfidenceTone = 'success' | 'warning' | 'error';
type AgencyFeeCalculationBase = NonNullable<
  ConfirmedContractData['agency_detail']
>['fee_calculation_base'];

interface ContractImportReviewProps {
  sessionId: string;
  result: CompleteResult;
  onConfirm: (data: ConfirmedContractData) => Promise<ConfirmImportResponse>;
  onCancel: () => void;
  onBack: () => void;
}

interface FormValues {
  revenue_mode?: ConfirmedContractData['revenue_mode'];
  contract_direction?: ConfirmedContractData['contract_direction'];
  group_relation_type?: ConfirmedContractData['group_relation_type'];
  operator_party_id?: string;
  contract_number: string;
  asset_id?: string;
  owner_party_id?: string;
  lessor_party_id?: string;
  lessee_party_id?: string;
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
  settlement_rule_json?: string;
  service_fee_ratio?: string;
  fee_calculation_base?: string;
  agency_scope?: string;
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

type OwnerReferenceFields = Pick<FormValues, 'owner_party_id'>;

export const parseJsonObjectField = (value: string): ConfirmedContractData['settlement_rule'] => {
  const normalized = value.trim();
  if (normalized === '') {
    throw new Error('结算规则 JSON 不能为空');
  }
  const parsed: unknown = JSON.parse(normalized);
  if (parsed == null || typeof parsed !== 'object' || Array.isArray(parsed)) {
    throw new Error('结算规则必须是合法 JSON 对象');
  }
  return parsed as ConfirmedContractData['settlement_rule'];
};

export const normalizeOptionalId = (value: string | undefined): string | undefined => {
  if (value == null) {
    return undefined;
  }
  const normalized = value.trim();
  return normalized === '' ? undefined : normalized;
};

export const resolveOwnerReferences = (
  validatedValues: OwnerReferenceFields,
  storedValues: OwnerReferenceFields
): { ownerPartyId: string | undefined } => {
  const ownerPartyId = normalizeOptionalId(
    validatedValues.owner_party_id ?? storedValues.owner_party_id
  );
  return { ownerPartyId };
};

const VALID_AGENCY_FEE_BASES = new Set<AgencyFeeCalculationBase>(['actual_received', 'due_amount']);

const normalizeAgencyFeeCalculationBase = (
  value: string | undefined
): AgencyFeeCalculationBase | undefined => {
  if (value == null) {
    return undefined;
  }
  const normalized = value.trim();
  if (VALID_AGENCY_FEE_BASES.has(normalized as AgencyFeeCalculationBase)) {
    return normalized as AgencyFeeCalculationBase;
  }
  return undefined;
};

const ContractImportReview: React.FC<ContractImportReviewProps> = ({
  result,
  onConfirm,
  onBack,
}) => {
  const navigate = useNavigate();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [modifiedFields, setModifiedFields] = useState<Set<string>>(new Set());
  const [activeTab, setActiveTab] = useState('basic');
  const [showAdvancedFields, setShowAdvancedFields] = useState(false);
  const [currentRevenueMode, setCurrentRevenueMode] = useState<
    ConfirmedContractData['revenue_mode'] | undefined
  >(undefined);

  const fieldEvidence = result.extraction_result.field_evidence ?? undefined;
  const fieldSources = result.extraction_result.field_sources ?? undefined;

  const hasExtractedValue = (fieldKey: string): boolean => {
    const value = result.extraction_result.data[fieldKey];
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
    const rawEvidence = fieldEvidence[fieldKey];
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
    const mappedSource = fieldSources != null ? fieldSources[fieldKey] : undefined;
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
      <div className={styles.evidencePopover}>
        <Text type="secondary" className={styles.evidenceMetaText}>
          来源: {resolveSourceLabel(sourceKey)}
        </Text>
        {hasSnippet ? (
          <Text className={styles.evidenceSnippetText}>{snippet}</Text>
        ) : (
          <Text type="secondary">未提供原文片段</Text>
        )}
        {hasMatch && (
          <Text type="secondary" className={styles.evidenceMetaWithGap}>
            匹配: {String(matchValue)}
          </Text>
        )}
        {evidence?.match_type != null && String(evidence.match_type).trim() !== '' && (
          <Text type="secondary" className={styles.evidenceMetaText}>
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
    const agencyDetail =
      validatedData.agency_detail != null && typeof validatedData.agency_detail === 'object'
        ? (validatedData.agency_detail as Record<string, unknown>)
        : undefined;

    // 设置表单初始值 - 确保数字字段正确转换
    form.setFieldsValue({
      revenue_mode: validatedData.revenue_mode,
      contract_direction: validatedData.contract_direction,
      group_relation_type: validatedData.group_relation_type,
      operator_party_id: validatedData.operator_party_id ?? '',
      contract_number: validatedData.contract_number ?? '',
      asset_id: recommendations.asset_id ?? '',
      owner_party_id: recommendations.owner_party_id ?? '',
      lessor_party_id: validatedData.lessor_party_id ?? '',
      lessee_party_id: validatedData.lessee_party_id ?? '',
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
      settlement_rule_json:
        validatedData.settlement_rule != null
          ? JSON.stringify(validatedData.settlement_rule, null, 2)
          : '',
      service_fee_ratio:
        agencyDetail?.service_fee_ratio != null ? String(agencyDetail.service_fee_ratio) : '',
      fee_calculation_base:
        agencyDetail?.fee_calculation_base != null
          ? String(agencyDetail.fee_calculation_base)
          : undefined,
      agency_scope: agencyDetail?.agency_scope != null ? String(agencyDetail.agency_scope) : '',
      rent_terms: validatedData.rent_terms ?? [],
    });
    if (validatedData.revenue_mode === 'LEASE' || validatedData.revenue_mode === 'AGENCY') {
      setCurrentRevenueMode(validatedData.revenue_mode);
    }
  }, [result, form]);

  // 表单字段变更处理
  const handleFieldChange = (changedValues: Record<string, unknown>) => {
    // 标记已修改的字段
    const newModifiedFields = new Set(modifiedFields);
    Object.keys(changedValues).forEach((fieldName: string) => {
      newModifiedFields.add(fieldName);
    });
    setModifiedFields(newModifiedFields);
    if (changedValues.revenue_mode === 'LEASE' || changedValues.revenue_mode === 'AGENCY') {
      setCurrentRevenueMode(changedValues.revenue_mode);
    }
  };

  // 确认导入
  const handleConfirm = async () => {
    try {
      const validatedValues = (await form.validateFields()) as FormValues;
      const storedValues = form.getFieldsValue(true) as FormValues;
      const values: FormValues = {
        ...storedValues,
        ...validatedValues,
      };

      // 转换日期格式
      const { ownerPartyId } = resolveOwnerReferences(validatedValues, storedValues);
      const settlementRule = parseJsonObjectField(values.settlement_rule_json ?? '');
      const operatorPartyId = normalizeOptionalId(values.operator_party_id);
      const lessorPartyId = normalizeOptionalId(values.lessor_party_id);
      const lesseePartyId = normalizeOptionalId(values.lessee_party_id);
      if (
        values.revenue_mode == null ||
        values.contract_direction == null ||
        values.group_relation_type == null ||
        operatorPartyId == null ||
        ownerPartyId == null ||
        lessorPartyId == null ||
        lesseePartyId == null
      ) {
        MessageManager.error('请补全新合同上下文');
        return;
      }

      const serviceFeeRatio = values.service_fee_ratio?.trim() ?? '';
      const feeCalculationBase = normalizeAgencyFeeCalculationBase(values.fee_calculation_base);
      if (values.revenue_mode === 'AGENCY' && feeCalculationBase == null) {
        form.setFields([
          {
            name: 'fee_calculation_base',
            errors: ['计费基数必须是 actual_received 或 due_amount'],
          },
        ]);
        MessageManager.error('请检查表单填写是否正确');
        return;
      }
      const confirmedData: ConfirmedContractData = {
        revenue_mode: values.revenue_mode,
        contract_direction: values.contract_direction,
        group_relation_type: values.group_relation_type,
        operator_party_id: operatorPartyId,
        contract_number: values.contract_number,
        asset_id: normalizeOptionalId(values.asset_id),
        owner_party_id: ownerPartyId,
        lessor_party_id: lessorPartyId,
        lessee_party_id: lesseePartyId,
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
        settlement_rule: settlementRule,
        ...(values.revenue_mode === 'AGENCY'
          ? {
              agency_detail: {
                service_fee_ratio: serviceFeeRatio,
                fee_calculation_base: feeCalculationBase!,
                agency_scope: values.agency_scope?.trim() ?? '',
              },
            }
          : {}),
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
        if (response.contract_group_id != null && response.contract_group_id.trim() !== '') {
          navigate(CONTRACT_GROUP_ROUTES.DETAIL(response.contract_group_id));
        }
      } else {
        MessageManager.error(response.error ?? '导入失败');
      }
    } catch (error: unknown) {
      pageLogger.error('表单验证失败', error);
      const _errorMessage = error instanceof Error ? error.message : '表单验证失败';
      MessageManager.error('请检查表单填写是否正确');
    } finally {
      setLoading(false);
    }
  };

  // 获取置信度色阶
  const getConfidenceTone = (score: number): ConfidenceTone => {
    if (score >= 90) {
      return 'success';
    }
    if (score >= 70) {
      return 'warning';
    }
    return 'error';
  };

  const getConfidenceToneClassName = (score: number): string => {
    const tone = getConfidenceTone(score);
    if (tone === 'success') {
      return styles.toneSuccess;
    }
    if (tone === 'warning') {
      return styles.toneWarning;
    }
    return styles.toneError;
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
          <Form.Item label={renderFieldLabel('合同状态', 'contract_status')} name="contract_status">
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
          <Form.Item label={renderFieldLabel('签订日期', 'sign_date')} name="sign_date">
            <DatePicker className={styles.fullWidthControl} placeholder="请选择签订日期" />
          </Form.Item>
        </Col>
        <Col span={8}>
          <Form.Item
            label={renderFieldLabel('开始日期', 'start_date')}
            name="start_date"
            rules={[{ required: true, message: '请选择开始日期' }]}
          >
            <DatePicker className={styles.fullWidthControl} placeholder="请选择开始日期" />
          </Form.Item>
        </Col>
        <Col span={8}>
          <Form.Item
            label={renderFieldLabel('结束日期', 'end_date')}
            name="end_date"
            rules={[{ required: true, message: '请选择结束日期' }]}
          >
            <DatePicker className={styles.fullWidthControl} placeholder="请选择结束日期" />
          </Form.Item>
        </Col>
      </Row>

      <Row gutter={16}>
        <Col span={8}>
          <Form.Item label={renderFieldLabel('租赁面积(㎡)', 'rentable_area')} name="rentable_area">
            <InputNumber
              className={styles.fullWidthControl}
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
              className={styles.fullWidthControl}
              placeholder="请输入月租金"
              min={0}
              precision={2}
              formatter={value => `${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
            />
          </Form.Item>
        </Col>
        <Col span={8}>
          <Form.Item label={renderFieldLabel('押金(元)', 'total_deposit')} name="total_deposit">
            <InputNumber
              className={styles.fullWidthControl}
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
      <div className={styles.matchingSection}>
        <Title level={5}>
          资产匹配
          {result.matching_result.matched_assets.length > 0 && (
            <Tag color="green" className={styles.matchCountTag}>
              找到 {result.matching_result.matched_assets.length} 个匹配项
            </Tag>
          )}
        </Title>

        {result.matching_result.matched_assets.length > 0 ? (
          <Form.Item label="选择资产" name="asset_id">
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
                      <span>{asset.asset_name}</span>
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
                    <div className={styles.matchAddressText}>{asset.address}</div>
                  </div>
                </Select.Option>
              ))}
            </Select>
          </Form.Item>
        ) : (
          <>
            <Alert
              title="未找到匹配的资产"
              description="资产关联保持可选；如需要，请手动填写资产 ID。"
              type="warning"
              showIcon
            />
            <Form.Item label="资产 ID（可选）" name="asset_id">
              <Input placeholder="请输入资产 ID" />
            </Form.Item>
          </>
        )}
      </div>

      {/* 产权方主体匹配 */}
      <div>
        <Title level={5}>
          产权方主体匹配
          {result.matching_result.matched_ownerships.length > 0 && (
            <Tag color="green" className={styles.matchCountTag}>
              找到 {result.matching_result.matched_ownerships.length} 个匹配项
            </Tag>
          )}
        </Title>

        {result.matching_result.matched_ownerships.length > 0 ? (
          <Form.Item
            label="选择产权方主体"
            name="owner_party_id"
            rules={[{ required: true, message: '请选择关联的产权方主体' }]}
          >
            <Select
              placeholder="请选择匹配的产权方主体"
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
          <>
            <Alert
              title="未找到匹配的产权方主体"
              description="新合同导入仍要求显式 owner_party_id，请手动填写。"
              type="warning"
              showIcon
            />
            <Form.Item
              label="产权方主体 ID"
              name="owner_party_id"
              rules={[{ required: true, message: '请输入产权方主体 ID' }]}
            >
              <Input placeholder="请输入产权方主体 ID" />
            </Form.Item>
          </>
        )}
      </div>
    </div>
  );

  // 高级字段表单
  const AdvancedForm = () => (
    <Form form={form} layout="vertical" onValuesChange={handleFieldChange}>
      <Form.Item label={renderFieldLabel('支付条款', 'payment_terms')} name="payment_terms">
        <TextArea rows={3} placeholder="请输入支付条款" />
      </Form.Item>

      <Form.Item label={renderFieldLabel('合同备注', 'contract_notes')} name="contract_notes">
        <TextArea rows={3} placeholder="请输入合同备注" />
      </Form.Item>
    </Form>
  );

  const ContractContextForm = () => (
    <Form form={form} layout="vertical" onValuesChange={handleFieldChange}>
      <Alert
        type="info"
        showIcon
        className={styles.messageAlert}
        title="新合同导入采用 fail-closed 模式，必须显式提供合同组与主体上下文。"
      />

      <Row gutter={16}>
        <Col span={8}>
          <Form.Item
            label="经营模式"
            name="revenue_mode"
            rules={[{ required: true, message: '请选择经营模式' }]}
            extra="请输入 LEASE 或 AGENCY"
          >
            <Input placeholder="LEASE / AGENCY" />
          </Form.Item>
        </Col>
        <Col span={8}>
          <Form.Item
            label="合同方向"
            name="contract_direction"
            rules={[{ required: true, message: '请选择合同方向' }]}
            extra="请输入 LESSOR 或 LESSEE"
          >
            <Input placeholder="LESSOR / LESSEE" />
          </Form.Item>
        </Col>
        <Col span={8}>
          <Form.Item
            label="合同角色"
            name="group_relation_type"
            rules={[{ required: true, message: '请选择合同角色' }]}
            extra="请输入 UPSTREAM / DOWNSTREAM / ENTRUSTED / DIRECT_LEASE"
          >
            <Input placeholder="UPSTREAM / DOWNSTREAM / ENTRUSTED / DIRECT_LEASE" />
          </Form.Item>
        </Col>
      </Row>

      <Row gutter={16}>
        <Col span={8}>
          <Form.Item
            label="运营方主体 ID"
            name="operator_party_id"
            rules={[{ required: true, message: '请输入运营方主体 ID' }]}
          >
            <Input placeholder="请输入运营方主体 ID" />
          </Form.Item>
        </Col>
        <Col span={8}>
          <Form.Item
            label="出租方/委托方主体 ID"
            name="lessor_party_id"
            rules={[{ required: true, message: '请输入出租方/委托方主体 ID' }]}
          >
            <Input placeholder="请输入出租方/委托方主体 ID" />
          </Form.Item>
        </Col>
        <Col span={8}>
          <Form.Item
            label="承租方/受托方主体 ID"
            name="lessee_party_id"
            rules={[{ required: true, message: '请输入承租方/受托方主体 ID' }]}
          >
            <Input placeholder="请输入承租方/受托方主体 ID" />
          </Form.Item>
        </Col>
      </Row>

      <Form.Item
        label="结算规则 JSON"
        name="settlement_rule_json"
        rules={[
          { required: true, message: '请输入结算规则 JSON' },
          {
            validator: async (_, value: string | undefined) => {
              try {
                parseJsonObjectField(value ?? '');
              } catch (error) {
                throw new Error(error instanceof Error ? error.message : '结算规则必须是合法 JSON');
              }
            },
          },
        ]}
      >
        <TextArea
          rows={6}
          placeholder='{"version":"v1","cycle":"月付","settlement_mode":"manual","amount_rule":{},"payment_rule":{}}'
        />
      </Form.Item>

      {currentRevenueMode === 'AGENCY' && (
        <Row gutter={16}>
          <Col span={8}>
            <Form.Item
              label="服务费比例"
              name="service_fee_ratio"
              rules={[
                { required: true, message: '请输入服务费比例' },
                {
                  validator: async (_, value: string | undefined) => {
                    const normalized = value?.trim() ?? '';
                    const numericValue = Number(normalized);
                    if (
                      normalized === '' ||
                      Number.isNaN(numericValue) ||
                      numericValue < 0 ||
                      numericValue > 1
                    ) {
                      throw new Error('服务费比例必须是 0 到 1 之间的小数');
                    }
                  },
                },
              ]}
            >
              <Input placeholder="例如 0.08" />
            </Form.Item>
          </Col>
          <Col span={8}>
            <Form.Item
              label="计费基数"
              name="fee_calculation_base"
              rules={[
                { required: true, message: '请输入计费基数' },
                {
                  validator: async (_, value: string | undefined) => {
                    if (normalizeAgencyFeeCalculationBase(value) == null) {
                      throw new Error('计费基数必须是 actual_received 或 due_amount');
                    }
                  },
                },
              ]}
              extra="请输入 actual_received 或 due_amount"
            >
              <Input placeholder="actual_received / due_amount" />
            </Form.Item>
          </Col>
          <Col span={8}>
            <Form.Item label="代理范围说明" name="agency_scope">
              <Input placeholder="请输入代理范围说明" />
            </Form.Item>
          </Col>
        </Row>
      )}
    </Form>
  );

  const tabItems = [
    {
      key: 'basic',
      label: '基本信息',
      children: <BasicInfoForm />,
    },
    {
      key: 'dates',
      label: '日期和金额',
      children: <DateAmountForm />,
    },
    {
      key: 'matching',
      label: '数据匹配',
      children: <MatchingForm />,
    },
    {
      key: 'contract-context',
      label: '新体系上下文',
      children: <ContractContextForm />,
    },
    {
      key: 'advanced',
      label: `高级字段${showAdvancedFields ? '' : ' (展开)'}`,
      children: (
        <>
          <div className={styles.advancedSwitchRow}>
            <Switch
              checked={showAdvancedFields}
              onChange={setShowAdvancedFields}
              checkedChildren="显示高级字段"
              unCheckedChildren="隐藏高级字段"
            />
          </div>
          {showAdvancedFields && <AdvancedForm />}
        </>
      ),
    },
  ];

  return (
    <div className={styles.reviewContainer}>
      {/* 头部统计 */}
      <Card className={styles.sectionCard}>
        <Row gutter={[16, 16]} className={styles.statsRow}>
          <Col xs={24} sm={12} xl={6}>
            <Card
              className={`${styles.statsCard} ${getConfidenceToneClassName(result.summary.extraction_confidence)}`}
            >
              <Statistic
                title="提取可信度"
                value={result.summary.extraction_confidence}
                precision={2}
                suffix="%"
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} xl={6}>
            <Card
              className={`${styles.statsCard} ${getConfidenceToneClassName(result.summary.validation_score)}`}
            >
              <Statistic
                title="验证评分"
                value={result.summary.validation_score}
                precision={2}
                suffix="%"
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} xl={6}>
            <Card
              className={`${styles.statsCard} ${getConfidenceToneClassName(result.summary.match_confidence)}`}
            >
              <Statistic
                title="匹配置信度"
                value={result.summary.match_confidence}
                precision={2}
                suffix="%"
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} xl={6}>
            <Card
              className={`${styles.statsCard} ${getConfidenceToneClassName(result.summary.total_confidence)}`}
            >
              <Statistic
                title="总体评分"
                value={result.summary.total_confidence}
                precision={2}
                suffix="%"
              />
            </Card>
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
          className={styles.messageAlert}
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
            className={styles.messageAlert}
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
          className={styles.messageAlert}
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
          className={styles.messageAlert}
        />
      )}

      {/* 主表单 */}
      <Card title="合同信息确认">
        <Tabs activeKey={activeTab} onChange={setActiveTab} items={tabItems} />
      </Card>

      {/* 操作按钮 */}
      <div className={styles.actionFooter}>
        <Space size="large" className={styles.actionSpace}>
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
            aria-label="确认导入"
          >
            确认导入
          </Button>
        </Space>
      </div>
    </div>
  );
};

export default ContractImportReview;
