import React, { useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Button,
  Card,
  Col,
  Form,
  Input,
  Row,
  Select,
  Space,
  Tag,
  Typography,
  Upload,
  message,
} from 'antd';
import { UploadOutlined } from '@ant-design/icons';
import { useSearchParams } from 'react-router-dom';
import type { UploadFile } from 'antd/es/upload/interface';

import {
  documentExtractionService,
  type ContractPartyIds,
  type ExtractionAction,
  type ExtractionSession,
  type ExtractionUploadContext,
} from '@/services/documentExtractionService';
import { partyService } from '@/services/partyService';
import type { Party } from '@/types/party';
import ProjectSelect from '@/components/Project/ProjectSelect';
import PartySelector, { type PartySelectorFilterMode } from '@/components/Common/PartySelector';
import AssetMultiSelect from '@/components/Common/AssetMultiSelect';

const { Title, Text } = Typography;

const fieldLabels: Record<string, string> = {
  contract_number: '合同编号',
  sign_date: '签订日期',
  effective_from: '生效日期',
  effective_to: '到期日期',
  monthly_rent: '月租金',
  contract_notes: '合同备注',
  payment_cycle: '付款周期',
};

const requiredFields = ['contract_number', 'sign_date', 'effective_from'];
const optionalFields = ['effective_to', 'monthly_rent', 'contract_notes', 'payment_cycle'];

const PARTY_FIELD_LABELS: Record<keyof ContractPartyIds, string> = {
  operator_party_id: '运营方主体',
  owner_party_id: '产权方主体',
  lessor_party_id: '出租方主体',
  lessee_party_id: '承租方主体',
};

const CONFIDENCE_LABELS: Record<string, string> = {
  high: '高',
  medium: '中',
  low: '低',
};

interface FieldDecision {
  action?: ExtractionAction;
  candidate_value?: string;
  value?: string;
}

interface RelationTypeOption {
  value: ExtractionUploadContext['group_relation_type'];
  label: string;
}

const relationTypeOptionsByRevenueMode: Record<
  ExtractionUploadContext['revenue_mode'],
  RelationTypeOption[]
> = {
  lease: [
    { value: '\u4e0a\u6e38', label: '上游' },
    { value: '\u4e0b\u6e38', label: '下游' },
  ],
  agency: [
    { value: '\u59d4\u6258', label: '委托' },
    { value: '\u76f4\u79df', label: '直租' },
  ],
};

export const relationTypeOptionsForRevenueMode = (
  revenueMode: ExtractionUploadContext['revenue_mode']
): RelationTypeOption[] => relationTypeOptionsByRevenueMode[revenueMode];

export const errorText = (error: unknown): string => {
  if (error instanceof Error) {
    return error.message;
  }
  if (typeof error === 'object' && error !== null && 'message' in error) {
    const message = (error as { message?: unknown }).message;
    if (typeof message === 'string' && message.trim() !== '') {
      return message;
    }
  }
  return '请求失败';
};

export const isPdfFile = (file: Pick<File, 'name' | 'type'>): boolean =>
  file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf');

const APPROVED_PARTY_SEARCH_LIMIT = 20;

/**
 * 已审核主体选择器：只允许选择 review_status=approved 且 status=active 的主体。
 * 过滤由服务端完成（GET /api/v1/parties?review_status=approved&status=active，#81/#82 契约对齐），
 * 客户端不再二次过滤。
 */
export const approvedPartyFetcher = async (
  query: string,
  _filterMode: PartySelectorFilterMode
): Promise<Party[]> => {
  const result = await partyService.searchParties(query, {
    limit: APPROVED_PARTY_SEARCH_LIMIT,
    status: 'active',
    review_status: 'approved',
  });
  return result.items;
};

const PDFImportPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const projectIdFromUrl = searchParams.get('project_id');
  const [form] = Form.useForm<ExtractionUploadContext>();
  const [file, setFile] = useState<File | null>(null);
  const [session, setSession] = useState<ExtractionSession | null>(null);
  const [decisions, setDecisions] = useState<Record<string, FieldDecision>>({});
  const [partyIds, setPartyIds] = useState<ContractPartyIds>({
    operator_party_id: '',
    owner_party_id: '',
    lessor_party_id: '',
    lessee_party_id: '',
  });
  const [assetIds, setAssetIds] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const revenueMode =
    Form.useWatch('revenue_mode', { form, preserve: true }) ?? 'lease';
  const selectedProjectId = Form.useWatch('project_id', { form, preserve: true });
  const relationTypeOptions = relationTypeOptionsForRevenueMode(revenueMode);
  const projectLocked = projectIdFromUrl != null && projectIdFromUrl !== '';

  // 同路由不同 query 重放（import?project_id=A → B）时重放预填值，避免会话建在旧项目上
  useEffect(() => {
    if (projectLocked) {
      form.setFieldValue('project_id', projectIdFromUrl);
    }
  }, [projectIdFromUrl, projectLocked, form]);

  useEffect(() => {
    setAssetIds([]);
  }, [selectedProjectId]);

  const fields = useMemo(() => {
    const extracted = session?.candidates.fields ?? {};
    return Array.from(new Set([...requiredFields, ...optionalFields, ...Object.keys(extracted)]));
  }, [session]);

  const updateDecision = (fieldKey: string, patch: Partial<FieldDecision>): void => {
    setDecisions(current => ({
      ...current,
      [fieldKey]: { ...current[fieldKey], ...patch },
    }));
  };

  const handleRevenueModeChange = (
    nextRevenueMode: ExtractionUploadContext['revenue_mode']
  ): void => {
    const currentRelationType = form.getFieldValue('group_relation_type');
    const remainsCompatible = relationTypeOptionsForRevenueMode(nextRevenueMode).some(
      option => option.value === currentRelationType
    );
    if (!remainsCompatible) {
      form.setFieldValue('group_relation_type', undefined);
    }
  };

  const start = async (): Promise<void> => {
    const context = await form.validateFields();
    if (file == null) {
      message.error('请选择一个 PDF 文件。');
      return;
    }
    setBusy(true);
    try {
      const created = await documentExtractionService.createContractSession(file, context);
      setSession(created);
      setDecisions({});
    } catch (error) {
      message.error(errorText(error));
    } finally {
      setBusy(false);
    }
  };

  const cancel = async (): Promise<void> => {
    if (session == null) {
      return;
    }
    setBusy(true);
    try {
      await documentExtractionService.cancel(session.session_id);
      setSession(null);
      setFile(null);
      setDecisions({});
      message.success('已取消解析会话。');
    } catch (error) {
      message.error(errorText(error));
    } finally {
      setBusy(false);
    }
  };

  const confirm = async (): Promise<void> => {
    if (session == null) {
      return;
    }
    const missingDecision = fields.find(fieldKey => decisions[fieldKey]?.action == null);
    if (missingDecision != null) {
      message.error(
        `请为字段「${fieldLabels[missingDecision] ?? missingDecision}」选择处理方式。`
      );
      return;
    }
    if (Object.values(partyIds).some(value => value.trim() === '')) {
      message.error('请完整选择运营方、产权方、出租方、承租方四个主体。');
      return;
    }
    const actions = fields.map(field_key => {
      const decision = decisions[field_key];
      return {
        field_key,
        action: decision.action as ExtractionAction,
        candidate_value: decision.candidate_value,
        value: decision.value,
      };
    });
    setBusy(true);
    try {
      const result = await documentExtractionService.confirm(session.session_id, {
        actions,
        party_ids: partyIds,
        asset_ids: assetIds,
      });
      message.success(`合同创建成功：${result.contract_id}`);
      setSession(null);
      setFile(null);
      setDecisions({});
    } catch (error) {
      message.error(errorText(error));
    } finally {
      setBusy(false);
    }
  };

  if (session == null) {
    return (
      <div>
        <Title level={3}>合同文件解析</Title>
        <Card>
          <Form
            form={form}
            layout="vertical"
            initialValues={{ revenue_mode: 'lease', project_id: projectIdFromUrl ?? undefined }}
          >
            <Row gutter={16}>
              <Col xs={24} md={12}>
                <Form.Item
                  name="project_id"
                  label="所属项目"
                  rules={[{ required: true, message: '请选择所属项目' }]}
                  extra={projectLocked ? '来自项目详情，已锁定' : undefined}
                >
                  <ProjectSelect disabled={projectLocked} />
                </Form.Item>
              </Col>
              <Col xs={24} md={12}>
                <Form.Item
                  name="revenue_mode"
                  label="经营模式"
                  rules={[{ required: true, message: '请选择经营模式' }]}
                >
                  <Select
                    onChange={handleRevenueModeChange}
                    options={[
                      { value: 'lease', label: '承租转租' },
                      { value: 'agency', label: '代理运营' },
                    ]}
                  />
                </Form.Item>
              </Col>
              <Col xs={24} md={12}>
                <Form.Item
                  name="contract_direction"
                  label="合同方向"
                  rules={[{ required: true, message: '请选择合同方向' }]}
                >
                  <Select
                    options={[
                      { value: '\u51fa\u79df', label: '出租' },
                      { value: '\u627f\u79df', label: '承租' },
                    ]}
                  />
                </Form.Item>
              </Col>
              <Col xs={24} md={12}>
                <Form.Item
                  name="group_relation_type"
                  label="合同角色"
                  rules={[{ required: true, message: '请选择合同角色' }]}
                >
                  <Select options={relationTypeOptions} />
                </Form.Item>
              </Col>
            </Row>
            <Upload
              accept=".pdf,application/pdf"
              beforeUpload={upload => {
                if (!isPdfFile(upload)) {
                  message.error('仅支持 PDF 文件。');
                  return Upload.LIST_IGNORE;
                }
                setFile(upload);
                return false;
              }}
              maxCount={1}
              fileList={
                file == null
                  ? []
                  : ([{ uid: 'contract-pdf', name: file.name, status: 'done' }] as UploadFile[])
              }
              onRemove={() => {
                setFile(null);
                return true;
              }}
            >
              <Button icon={<UploadOutlined />}>选择 PDF 文件</Button>
            </Upload>
            <Space style={{ marginTop: 16 }}>
              <Button type="primary" onClick={() => void start()} loading={busy}>
                开始解析
              </Button>
            </Space>
          </Form>
        </Card>
      </div>
    );
  }

  return (
    <div>
      <Title level={3}>逐项确认提取的合同字段</Title>
      {session.errors.map(error => (
        <Alert key={error} type="warning" showIcon message={error} style={{ marginBottom: 12 }} />
      ))}
      <Card>
        <Space direction="vertical" size="large" style={{ display: 'flex' }}>
          {fields.map(fieldKey => {
            const field = session.candidates.fields[fieldKey];
            const decision = decisions[fieldKey] ?? {};
            const isOptional = optionalFields.includes(fieldKey);
            return (
              <Card key={fieldKey} size="small" title={fieldLabels[fieldKey] ?? fieldKey}>
                {field?.conflict === true && (
                  <Alert
                    type="warning"
                    showIcon
                    message="候选存在冲突，请显式选择处理方式。"
                  />
                )}
                <Form layout="vertical">
                  <Form.Item label="处理方式" required>
                    <Select
                      value={decision.action}
                      onChange={(action: ExtractionAction) => updateDecision(fieldKey, { action })}
                      options={[
                        { value: 'accept_candidate', label: '采用候选' },
                        { value: 'correct_candidate', label: '修正候选' },
                        { value: 'manual', label: '手工录入' },
                        ...(isOptional
                          ? [{ value: 'clear_optional', label: '清空可选字段' }]
                          : []),
                      ]}
                    />
                  </Form.Item>
                  {(decision.action === 'accept_candidate' ||
                    decision.action === 'correct_candidate') && (
                    <Form.Item label="候选值" required>
                      <Select
                        value={decision.candidate_value}
                        onChange={(candidate_value: string) =>
                          updateDecision(fieldKey, { candidate_value })
                        }
                        options={(field?.candidates ?? []).map(candidate => ({
                          value: candidate.value,
                          label: candidate.value,
                        }))}
                      />
                    </Form.Item>
                  )}
                  {(decision.action === 'correct_candidate' || decision.action === 'manual') && (
                    <Form.Item label="修正值" required>
                      <Input
                        value={decision.value}
                        onChange={event => updateDecision(fieldKey, { value: event.target.value })}
                      />
                    </Form.Item>
                  )}
                  {(field?.candidates ?? []).map(candidate => (
                    <div key={candidate.value}>
                      <Tag
                        color={
                          candidate.confidence === 'high'
                            ? 'green'
                            : candidate.confidence === 'medium'
                              ? 'gold'
                              : 'red'
                        }
                      >
                        {CONFIDENCE_LABELS[candidate.confidence] ?? candidate.confidence}
                      </Tag>
                      <Text>{candidate.value}</Text>
                      {candidate.evidence.map(evidence => (
                        <div key={`${candidate.value}-${evidence.page_number}`}>
                          <Text type="secondary">
                            第 {evidence.page_number} 页: {evidence.text}
                          </Text>
                        </div>
                      ))}
                    </div>
                  ))}
                </Form>
              </Card>
            );
          })}
        </Space>
      </Card>
      <Card title="明确选择既有主体与资产" style={{ marginTop: 16 }}>
        <Row gutter={16}>
          {(
            ['operator_party_id', 'owner_party_id', 'lessor_party_id', 'lessee_party_id'] as const
          ).map(key => (
            <Col xs={24} md={12} key={key}>
              <Form.Item label={PARTY_FIELD_LABELS[key]}>
                <PartySelector
                  value={partyIds[key] !== '' ? partyIds[key] : undefined}
                  onChange={value =>
                    setPartyIds(current => ({ ...current, [key]: value ?? '' }))
                  }
                  fetcher={approvedPartyFetcher}
                />
              </Form.Item>
            </Col>
          ))}
          <Col xs={24}>
            <Form.Item label="覆盖资产">
              <AssetMultiSelect
                value={assetIds}
                onChange={setAssetIds}
                projectId={selectedProjectId}
              />
            </Form.Item>
          </Col>
        </Row>
      </Card>
      <Space style={{ marginTop: 16 }}>
        <Button onClick={() => void cancel()} disabled={busy}>
          取消
        </Button>
        <Button type="primary" onClick={() => void confirm()} loading={busy}>
          创建合同
        </Button>
      </Space>
    </div>
  );
};

export default PDFImportPage;
