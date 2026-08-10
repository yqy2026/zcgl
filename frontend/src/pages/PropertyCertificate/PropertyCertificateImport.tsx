import { useState } from 'react';
import {
  Alert,
  Button,
  Card,
  Checkbox,
  Form,
  Input,
  Select,
  Space,
  Steps,
  Upload,
  message,
} from 'antd';
import { InboxOutlined } from '@ant-design/icons';
import { useNavigate, useSearchParams } from 'react-router-dom';

import PageContainer from '@/components/Common/PageContainer';
import { PROPERTY_CERTIFICATE_ROUTES } from '@/constants/routes';
import {
  propertyCertificateExtractionService,
  type ExtractionAction,
  type ExtractionField,
  type ExtractionSession,
} from '@/services/documentExtractionService';

import styles from './PropertyCertificateImport.module.css';

const FIELD_LABELS: Record<string, string> = {
  certificate_number: '证书编号',
  registration_date: '登记日期',
  property_address: '坐落地址',
  building_area: '建筑面积',
  land_area: '土地面积',
  remarks: '备注',
};
const OPTIONAL_FIELDS = new Set([
  'registration_date',
  'property_address',
  'building_area',
  'land_area',
  'remarks',
]);

const isApiConflict = (error: unknown): boolean => {
  if (typeof error !== 'object' || error == null || !('response' in error)) {
    return false;
  }
  const response = (error as { response?: { status?: unknown } }).response;
  return response?.status === 409;
};

export const PropertyCertificateImport: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const existingCertificateId = searchParams.get('certificate_id');
  const existingAttachmentId = searchParams.get('attachment_id');
  const isExistingReference = existingCertificateId != null && existingAttachmentId != null;
  const [form] = Form.useForm<{
    assetId: string;
    holderPartyIds: string;
    certificateType: string;
  }>();
  const [file, setFile] = useState<File | null>(null);
  const [session, setSession] = useState<ExtractionSession | null>(null);
  const [fieldValues, setFieldValues] = useState<Record<string, string>>({});
  const [linkExistingCertificateId, setLinkExistingCertificateId] = useState('');
  const [attachStaged, setAttachStaged] = useState(true);
  const [loading, setLoading] = useState(false);
  const [conflict, setConflict] = useState(false);

  const startExtraction = async () => {
    try {
      const values = await form.validateFields(['assetId']);
      setLoading(true);
      const nextSession = isExistingReference
        ? await propertyCertificateExtractionService.createExistingSession(
            existingCertificateId,
            values.assetId,
            existingAttachmentId
          )
        : await (() => {
            if (file == null) {
              throw new Error('请选择一份产权证文件');
            }
            return propertyCertificateExtractionService.createSession(file, values.assetId);
          })();
      setSession(nextSession);
      setFieldValues({});
      setConflict(false);
    } catch (error) {
      if (typeof error === 'object' && error !== null && 'errorFields' in error) {
        // antd validateFields 拒绝：行内校验消息已展示，不弹全局错误
        return;
      }
      if (error instanceof Error) {
        message.error(error.message);
      } else {
        message.error('文件解析失败，请检查资产 ID 和文件后重试');
      }
    } finally {
      setLoading(false);
    }
  };

  const resolveActions = (): Array<{
    field_key: string;
    action: ExtractionAction;
    candidate_value?: string;
    value?: string;
  }> => {
    if (session == null) {
      return [];
    }
    const fields = session.candidates.fields;
    const actions: Array<{
      field_key: string;
      action: ExtractionAction;
      candidate_value?: string;
      value?: string;
    }> = [];
    const keys = new Set([...Object.keys(FIELD_LABELS), ...Object.keys(fields)]);
    for (const key of keys) {
      const value = fieldValues[key]?.trim() ?? '';
      const field: ExtractionField | undefined = fields[key];
      if (field != null) {
        if (value === '' && OPTIONAL_FIELDS.has(key)) {
          actions.push({ field_key: key, action: 'clear_optional' });
          continue;
        }
        if (value === '') {
          throw new Error(`${FIELD_LABELS[key] ?? key}需要人工确认`);
        }
        const matchedCandidate = field.candidates.find(candidate => candidate.value === value);
        if (matchedCandidate != null) {
          actions.push({
            field_key: key,
            action: 'accept_candidate',
            candidate_value: matchedCandidate.value,
          });
        } else {
          actions.push({
            field_key: key,
            action: 'correct_candidate',
            candidate_value: field.candidates[0]?.value,
            value,
          });
        }
        continue;
      }
      if (value !== '') {
        actions.push({ field_key: key, action: 'manual', value });
      }
    }
    return actions;
  };

  const confirm = async () => {
    if (session == null) {
      return;
    }
    try {
      const values = isExistingReference
        ? undefined
        : await form.validateFields(['holderPartyIds', 'certificateType']);
      const actions = resolveActions();
      if (!actions.some(action => action.field_key === 'certificate_number')) {
        throw new Error('请填写证书编号');
      }
      const holderPartyIds = (values?.holderPartyIds ?? '')
        .split(',')
        .map(value => value.trim())
        .filter(value => value !== '');
      if (
        !isExistingReference &&
        holderPartyIds.length === 0 &&
        linkExistingCertificateId.trim() === ''
      ) {
        throw new Error('请填写至少一个权利人 ID');
      }
      setLoading(true);
      const result = isExistingReference
        ? await propertyCertificateExtractionService.confirmExisting(session.session_id, {
            actions,
          })
        : await propertyCertificateExtractionService.confirm(session.session_id, {
            actions,
            certificate_type: values?.certificateType as
              | 'real_estate'
              | 'house_ownership'
              | 'land_use'
              | 'other',
            holder_party_ids: holderPartyIds,
            link_existing_certificate_id:
              linkExistingCertificateId.trim() === ''
                ? undefined
                : linkExistingCertificateId.trim(),
            attach_staged: attachStaged,
          });
      message.success(`产权证已保存：${result.certificate_id}`);
      navigate(PROPERTY_CERTIFICATE_ROUTES.LIST);
    } catch (error) {
      if (isApiConflict(error)) {
        setConflict(true);
        message.error('证书编号已存在，请明确选择已有产权证');
      } else if (error instanceof Error) {
        message.error(error.message);
      } else {
        message.error('产权证保存失败，请重试');
      }
    } finally {
      setLoading(false);
    }
  };

  const cancel = async () => {
    if (session != null) {
      await propertyCertificateExtractionService.cancel(session.session_id);
    }
    setSession(null);
    setFile(null);
    setFieldValues({});
    setConflict(false);
  };

  return (
    <PageContainer
      title="产权证导入"
      subTitle="上传后逐字段复核，再创建产权证"
      className={styles.importPage}
    >
      <Space orientation="vertical" size="large" className={styles.importPage}>
        <Steps
          current={session == null ? 0 : 1}
          items={[{ title: '上传文件' }, { title: '人工复核' }, { title: '完成' }]}
        />

        <Card title={isExistingReference ? '复核已有附件' : '新建产权证'}>
          <Form form={form} layout="vertical" initialValues={{ certificateType: 'other' }}>
            <Form.Item
              label="资产 ID"
              name="assetId"
              rules={[{ required: true, message: '请输入资产 ID' }]}
            >
              <Input disabled={session != null} />
            </Form.Item>
            <Form.Item
              label="权利人 ID"
              name="holderPartyIds"
              rules={[{ required: session == null, message: '请输入权利人 ID' }]}
            >
              <Input
                disabled={session == null || isExistingReference}
                placeholder="多个 ID 用英文逗号分隔"
              />
            </Form.Item>
            <Form.Item label="证书类型" name="certificateType">
              <Select
                disabled={session == null}
                options={[
                  { value: 'real_estate', label: '不动产权证' },
                  { value: 'house_ownership', label: '房屋所有权证' },
                  { value: 'land_use', label: '土地使用证' },
                  { value: 'other', label: '其他' },
                ]}
              />
            </Form.Item>
          </Form>

          {session == null && (
            <>
              {!isExistingReference && (
                <Upload.Dragger
                  accept=".pdf,.jpg,.jpeg,.png"
                  maxCount={1}
                  beforeUpload={nextFile => {
                    if (nextFile.size > 20 * 1024 * 1024) {
                      message.error('文件不能超过 20 MiB');
                      return Upload.LIST_IGNORE;
                    }
                    setFile(nextFile as File);
                    return false;
                  }}
                  onRemove={() => setFile(null)}
                >
                  <p className="ant-upload-drag-icon">
                    <InboxOutlined />
                  </p>
                  <p className="ant-upload-text">选择产权证 PDF、JPEG 或 PNG</p>
                </Upload.Dragger>
              )}
              <Button type="primary" loading={loading} onClick={() => void startExtraction()}>
                {isExistingReference ? '开始复核' : '开始解析'}
              </Button>
            </>
          )}
        </Card>

        {session != null && (
          <Card title="人工复核">
            {session.errors.length > 0 && (
              <Alert type="warning" showIcon message={session.errors.join('、')} />
            )}
            <Space orientation="vertical" size="middle" className={styles.importPage}>
              {Object.entries(FIELD_LABELS).map(([key, label]) => {
                const candidates = session.candidates.fields[key]?.candidates ?? [];
                return (
                  <div key={key}>
                    <label htmlFor={`certificate-${key}`}>{label}</label>
                    <Input
                      id={`certificate-${key}`}
                      value={fieldValues[key] ?? ''}
                      onChange={event =>
                        setFieldValues(current => ({ ...current, [key]: event.target.value }))
                      }
                    />
                    {candidates.length > 0 && (
                      <Space wrap>
                        {candidates.map(candidate => (
                          <Button
                            key={`${key}-${candidate.value}`}
                            size="small"
                            onClick={() =>
                              setFieldValues(current => ({ ...current, [key]: candidate.value }))
                            }
                          >
                            使用候选：{candidate.value}
                          </Button>
                        ))}
                      </Space>
                    )}
                  </div>
                );
              })}
              {conflict && (
                <Alert
                  type="warning"
                  showIcon
                  message="证书编号已存在"
                  description={
                    <Space orientation="vertical">
                      <Input
                        aria-label="已有产权证 ID"
                        value={linkExistingCertificateId}
                        onChange={event => setLinkExistingCertificateId(event.target.value)}
                      />
                      <Checkbox
                        checked={attachStaged}
                        onChange={event => setAttachStaged(event.target.checked)}
                      >
                        追加本次扫描件
                      </Checkbox>
                    </Space>
                  }
                />
              )}
              <Space>
                <Button type="primary" loading={loading} onClick={() => void confirm()}>
                  保存产权证
                </Button>
                <Button onClick={() => void cancel()}>取消</Button>
              </Space>
            </Space>
          </Card>
        )}
      </Space>
    </PageContainer>
  );
};

export default PropertyCertificateImport;
