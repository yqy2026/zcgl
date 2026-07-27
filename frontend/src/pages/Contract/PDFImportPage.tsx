import React, { useMemo, useState } from 'react';
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
import type { UploadFile } from 'antd/es/upload/interface';

import {
  documentExtractionService,
  type ContractPartyIds,
  type ExtractionAction,
  type ExtractionSession,
  type ExtractionUploadContext,
} from '@/services/documentExtractionService';

const { Title, Text } = Typography;

const fieldLabels: Record<string, string> = {
  contract_number: 'Contract number',
  sign_date: 'Sign date',
  effective_from: 'Effective from',
  effective_to: 'Effective to',
  monthly_rent: 'Monthly rent',
  contract_notes: 'Contract notes',
};

const requiredFields = ['contract_number', 'sign_date', 'effective_from'];
const optionalFields = ['effective_to', 'monthly_rent', 'contract_notes'];

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
    { value: '\u4e0a\u6e38', label: 'Upstream' },
    { value: '\u4e0b\u6e38', label: 'Downstream' },
  ],
  agency: [
    { value: '\u59d4\u6258', label: 'Entrusted' },
    { value: '\u76f4\u79df', label: 'Direct lease' },
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
  return 'Request failed';
};

const PDFImportPage: React.FC = () => {
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
  const [assetIds, setAssetIds] = useState('');
  const [busy, setBusy] = useState(false);
  const revenueMode = Form.useWatch('revenue_mode', form) ?? 'lease';
  const relationTypeOptions = relationTypeOptionsForRevenueMode(revenueMode);

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
      message.error('Select one PDF file.');
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
      message.success('Session cancelled.');
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
      message.error(`Choose an action for ${fieldLabels[missingDecision] ?? missingDecision}.`);
      return;
    }
    if (Object.values(partyIds).some(value => value.trim() === '')) {
      message.error('Enter all four Party IDs explicitly.');
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
        asset_ids: assetIds
          .split(',')
          .map(value => value.trim())
          .filter(value => value !== ''),
      });
      message.success(`Contract created: ${result.contract_id}`);
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
        <Title level={3}>Contract document review</Title>
        <Card>
          <Form form={form} layout="vertical" initialValues={{ revenue_mode: 'lease' }}>
            <Row gutter={16}>
              <Col xs={24} md={12}>
                <Form.Item name="project_id" label="Project ID" rules={[{ required: true }]}>
                  <Input />
                </Form.Item>
              </Col>
              <Col xs={24} md={12}>
                <Form.Item name="revenue_mode" label="Revenue mode" rules={[{ required: true }]}>
                  <Select
                    onChange={handleRevenueModeChange}
                    options={[
                      { value: 'lease', label: 'Lease' },
                      { value: 'agency', label: 'Agency' },
                    ]}
                  />
                </Form.Item>
              </Col>
              <Col xs={24} md={12}>
                <Form.Item
                  name="contract_direction"
                  label="Contract direction"
                  rules={[{ required: true }]}
                >
                  <Select
                    options={[
                      { value: '\u51fa\u79df', label: 'Lessor' },
                      { value: '\u627f\u79df', label: 'Lessee' },
                    ]}
                  />
                </Form.Item>
              </Col>
              <Col xs={24} md={12}>
                <Form.Item
                  name="group_relation_type"
                  label="Contract role"
                  rules={[{ required: true }]}
                >
                  <Select options={relationTypeOptions} />
                </Form.Item>
              </Col>
            </Row>
            <Upload
              accept=".pdf,application/pdf"
              beforeUpload={upload => {
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
              <Button icon={<UploadOutlined />}>Select PDF</Button>
            </Upload>
            <Space style={{ marginTop: 16 }}>
              <Button type="primary" onClick={() => void start()} loading={busy}>
                Extract for review
              </Button>
            </Space>
          </Form>
        </Card>
      </div>
    );
  }

  return (
    <div>
      <Title level={3}>Review extracted contract fields</Title>
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
                    message="Conflicting candidates require an explicit choice."
                  />
                )}
                <Form layout="vertical">
                  <Form.Item label="Action" required>
                    <Select
                      value={decision.action}
                      onChange={(action: ExtractionAction) => updateDecision(fieldKey, { action })}
                      options={[
                        { value: 'accept_candidate', label: 'Accept candidate' },
                        { value: 'correct_candidate', label: 'Correct candidate' },
                        { value: 'manual', label: 'Enter manually' },
                        ...(isOptional
                          ? [{ value: 'clear_optional', label: 'Clear optional field' }]
                          : []),
                      ]}
                    />
                  </Form.Item>
                  {(decision.action === 'accept_candidate' ||
                    decision.action === 'correct_candidate') && (
                    <Form.Item label="Candidate" required>
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
                    <Form.Item label="Reviewed value" required>
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
                        {candidate.confidence}
                      </Tag>
                      <Text>{candidate.value}</Text>
                      {candidate.evidence.map(evidence => (
                        <div key={`${candidate.value}-${evidence.page_number}`}>
                          <Text type="secondary">
                            Page {evidence.page_number}: {evidence.text}
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
      <Card title="Explicit existing references" style={{ marginTop: 16 }}>
        <Row gutter={16}>
          {(
            ['operator_party_id', 'owner_party_id', 'lessor_party_id', 'lessee_party_id'] as const
          ).map(key => (
            <Col xs={24} md={12} key={key}>
              <Form.Item label={key.replaceAll('_', ' ')}>
                <Input
                  value={partyIds[key]}
                  onChange={event =>
                    setPartyIds(current => ({ ...current, [key]: event.target.value }))
                  }
                />
              </Form.Item>
            </Col>
          ))}
          <Col xs={24}>
            <Form.Item label="Asset IDs (comma separated)">
              <Input value={assetIds} onChange={event => setAssetIds(event.target.value)} />
            </Form.Item>
          </Col>
        </Row>
      </Card>
      <Space style={{ marginTop: 16 }}>
        <Button onClick={() => void cancel()} disabled={busy}>
          Cancel
        </Button>
        <Button type="primary" onClick={() => void confirm()} loading={busy}>
          Create contract
        </Button>
      </Space>
    </div>
  );
};

export default PDFImportPage;
