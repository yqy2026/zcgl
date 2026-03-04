/**
 * Property Certificate Review Component
 * 产权证审核组件
 */

import { useState } from 'react';
import {
  Card,
  Form,
  Input,
  Select,
  DatePicker,
  Button,
  Space,
  Tag,
  Collapse,
  List,
  Typography,
  message,
} from 'antd';
import { SaveOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import type {
  CertificateExtractionResult,
  AssetMatch,
  CertificateImportConfirm,
} from '@/types/propertyCertificate';
import styles from './PropertyCertificateReview.module.css';

const { Text } = Typography;

interface PropertyCertificateReviewProps {
  extractionResult: CertificateExtractionResult;
  onConfirm: (data: CertificateImportConfirm) => void;
  loading?: boolean;
}

type Tone = 'primary' | 'success' | 'warning' | 'error';

const ANT_TAG_COLOR_MAP: Record<Tone, string> = {
  primary: 'blue',
  success: 'success',
  warning: 'warning',
  error: 'error',
};

const getConfidenceMeta = (confidence: number): { tone: Tone; label: string } => {
  if (confidence > 0.8) {
    return { tone: 'success', label: '高' };
  }
  if (confidence > 0.5) {
    return { tone: 'warning', label: '中' };
  }
  return { tone: 'error', label: '低' };
};

const DATE_FIELD_KEYS = ['registration_date', 'land_use_term_start', 'land_use_term_end'] as const;

const normalizeIsoDate = (year: number, month: number, day: number): string | null => {
  if (
    !Number.isInteger(year) ||
    !Number.isInteger(month) ||
    !Number.isInteger(day) ||
    month < 1 ||
    month > 12 ||
    day < 1 ||
    day > 31
  ) {
    return null;
  }

  const candidate = new Date(Date.UTC(year, month - 1, day));
  if (
    candidate.getUTCFullYear() !== year ||
    candidate.getUTCMonth() + 1 !== month ||
    candidate.getUTCDate() !== day
  ) {
    return null;
  }

  return `${String(year).padStart(4, '0')}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
};

const normalizeDateFieldValue = (value: unknown): string | null => {
  if (value == null) {
    return null;
  }

  if (dayjs.isDayjs(value)) {
    return value.isValid() ? value.format('YYYY-MM-DD') : null;
  }

  const rawValue = String(value).trim();
  if (rawValue === '') {
    return null;
  }

  const isoMatch = rawValue.match(/^(\d{4})-(\d{1,2})-(\d{1,2})$/);
  if (isoMatch != null) {
    const [, year, month, day] = isoMatch;
    return normalizeIsoDate(Number(year), Number(month), Number(day));
  }

  const slashMatch = rawValue.match(/^(\d{4})\/(\d{1,2})\/(\d{1,2})$/);
  if (slashMatch != null) {
    const [, year, month, day] = slashMatch;
    return normalizeIsoDate(Number(year), Number(month), Number(day));
  }

  const chineseMatch = rawValue.match(/^(\d{4})年(\d{1,2})月(\d{1,2})日$/);
  if (chineseMatch != null) {
    const [, year, month, day] = chineseMatch;
    return normalizeIsoDate(Number(year), Number(month), Number(day));
  }

  return null;
};

const normalizeCertificateDateFields = (
  values: Record<string, unknown>
): Record<string, unknown> => {
  const normalizedValues: Record<string, unknown> = { ...values };
  for (const fieldKey of DATE_FIELD_KEYS) {
    if (fieldKey in normalizedValues) {
      normalizedValues[fieldKey] = normalizeDateFieldValue(normalizedValues[fieldKey]);
    }
  }
  return normalizedValues;
};

export const PropertyCertificateReview: React.FC<PropertyCertificateReviewProps> = ({
  extractionResult,
  onConfirm,
  loading = false,
}) => {
  const [form] = Form.useForm();
  const [selectedAssetId, setSelectedAssetId] = useState<string | null>(null);

  const { extracted_data, confidence_score, asset_matches, validation_errors, warnings } =
    extractionResult;
  const normalizedInitialRegistrationDate = normalizeDateFieldValue(
    extracted_data.registration_date
  );
  const normalizedInitialLandUseTermStart = normalizeDateFieldValue(
    extracted_data.land_use_term_start
  );
  const normalizedInitialLandUseTermEnd = normalizeDateFieldValue(
    extracted_data.land_use_term_end
  );
  const confidenceMeta = getConfidenceMeta(confidence_score);
  const toneClassMap: Record<Tone, string> = {
    primary: styles.tonePrimary,
    success: styles.toneSuccess,
    warning: styles.toneWarning,
    error: styles.toneError,
  };

  const handleConfirm = async () => {
    try {
      const values = await form.validateFields();
      const mergedValues: Record<string, unknown> = {
        ...extracted_data,
        ...values,
      };
      const normalizedValues = normalizeCertificateDateFields(mergedValues);
      onConfirm({
        session_id: extractionResult.session_id,
        asset_ids: selectedAssetId != null ? [selectedAssetId] : [],
        extracted_data: normalizedValues,
        asset_link_id: selectedAssetId,
        should_create_new_asset: selectedAssetId == null,
        owners: [],
      });
    } catch {
      console.error('Validation failed');
      message.error('表单验证失败，请检查输入');
    }
  };

  const handleAssetSelect = (assetId: string) => {
    setSelectedAssetId(assetId);
  };

  return (
    <Space orientation="vertical" size="large" className={styles.reviewStack}>
      {/* Confidence Score */}
      <Card
        title="提取结果"
        extra={
          <Space size={6} className={styles.inlineStatus} wrap>
            <Tag
              color={ANT_TAG_COLOR_MAP[confidenceMeta.tone]}
              className={[styles.statusTag, toneClassMap[confidenceMeta.tone]].join(' ')}
            >
              置信度: {(confidence_score * 100).toFixed(1)}%
            </Tag>
            <Text type="secondary" className={styles.statusAssistText}>
              {confidenceMeta.label}
            </Text>
          </Space>
        }
      >
        <Collapse
          items={[
            {
              key: 'errors',
              label: `验证错误 (${validation_errors.length})`,
              children:
                validation_errors.length > 0 ? (
                  <List
                    dataSource={validation_errors}
                    renderItem={error => (
                      <List.Item className={styles.listItem}>
                        <Text type="danger">{error}</Text>
                      </List.Item>
                    )}
                  />
                ) : (
                  <Text>无错误</Text>
                ),
            },
          ]}
        />

        {warnings.length > 0 && (
          <Collapse
            items={[
              {
                key: 'warnings',
                label: `警告 (${warnings.length})`,
                children: (
                  <List
                    dataSource={warnings}
                    renderItem={warning => (
                      <List.Item className={styles.listItem}>
                        <Text type="warning">{warning}</Text>
                      </List.Item>
                    )}
                  />
                ),
              },
            ]}
            className={styles.warningCollapse}
          />
        )}
      </Card>

      {/* Asset Matching */}
      {asset_matches != null && asset_matches.length > 0 && (
        <Card title="匹配的资产">
          <List
            dataSource={asset_matches}
            renderItem={(asset: AssetMatch) => (
              <List.Item
                key={asset.asset_id}
                onClick={() => handleAssetSelect(asset.asset_id)}
                onKeyDown={event => {
                  if (event.key === 'Enter' || event.key === ' ') {
                    event.preventDefault();
                    handleAssetSelect(asset.asset_id);
                  }
                }}
                role="button"
                tabIndex={0}
                className={[
                  styles.assetListItem,
                  selectedAssetId === asset.asset_id ? styles.assetListItemActive : '',
                ].join(' ')}
              >
                <List.Item.Meta
                  title={asset.name}
                  description={`${asset.address} - 置信度: ${(asset.confidence * 100).toFixed(1)}%`}
                />
              </List.Item>
            )}
          />
        </Card>
      )}

      {/* Edit Form */}
      <Card title="确认并编辑信息">
        <Form
          form={form}
          layout="vertical"
          initialValues={{
            ...extracted_data,
            registration_date: normalizedInitialRegistrationDate
              ? dayjs(normalizedInitialRegistrationDate)
              : null,
            land_use_term_start: normalizedInitialLandUseTermStart
              ? dayjs(normalizedInitialLandUseTermStart)
              : null,
            land_use_term_end: normalizedInitialLandUseTermEnd
              ? dayjs(normalizedInitialLandUseTermEnd)
              : null,
          }}
          onFinish={handleConfirm}
        >
          <Form.Item
            label="证书编号"
            name="certificate_number"
            rules={[{ required: true, message: '请输入证书编号' }]}
          >
            <Input />
          </Form.Item>

          <Form.Item
            label="坐落地址"
            name="property_address"
            rules={[{ required: true, message: '请输入坐落地址' }]}
          >
            <Input />
          </Form.Item>

          <Form.Item label="用途" name="property_type">
            <Select placeholder="请选择用途">
              <Select.Option value="住宅">住宅</Select.Option>
              <Select.Option value="商业">商业</Select.Option>
              <Select.Option value="工业">工业</Select.Option>
              <Select.Option value="办公">办公</Select.Option>
            </Select>
          </Form.Item>

          <Form.Item label="建筑面积" name="building_area">
            <Input suffix="㎡" />
          </Form.Item>

          <Form.Item label="登记日期" name="registration_date">
            <DatePicker className={styles.fullWidthInput} />
          </Form.Item>

          <Form.Item>
            <Button
              type="primary"
              htmlType="submit"
              icon={<SaveOutlined />}
              loading={loading}
              className={styles.submitButton}
            >
              确认并创建产权证
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </Space>
  );
};
