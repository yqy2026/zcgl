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
} from 'antd';
import { SaveOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import type {
  CertificateExtractionResult,
  AssetMatch,
  CertificateImportConfirm,
} from '@/types/propertyCertificate';

const { Text } = Typography;

interface PropertyCertificateReviewProps {
  extractionResult: CertificateExtractionResult;
  onConfirm: (data: CertificateImportConfirm) => void;
  loading?: boolean;
}

export const PropertyCertificateReview: React.FC<PropertyCertificateReviewProps> = ({
  extractionResult,
  onConfirm,
  loading = false,
}) => {
  const [form] = Form.useForm();
  const [selectedAssetId, setSelectedAssetId] = useState<string | null>(null);

  const { extracted_data, confidence_score, asset_matches, validation_errors, warnings } =
    extractionResult;

  const confidenceLevel =
    confidence_score > 0.8 ? 'success' : confidence_score > 0.5 ? 'warning' : 'error';

  const handleConfirm = async () => {
    try {
      const values = await form.validateFields();
      onConfirm({
        session_id: extractionResult.session_id,
        asset_ids: selectedAssetId != null ? [selectedAssetId] : [],
        extracted_data: values,
        asset_link_id: selectedAssetId,
        should_create_new_asset: selectedAssetId == null,
        owners: [],
      });
    } catch {
      console.error('Validation failed');
    }
  };

  return (
    <Space orientation="vertical" size="large" style={{ width: '100%' }}>
      {/* Confidence Score */}
      <Card
        title="提取结果"
        extra={<Tag color={confidenceLevel}>置信度: {(confidence_score * 100).toFixed(1)}%</Tag>}
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
                      <List.Item>
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
                      <List.Item>
                        <Text type="warning">{warning}</Text>
                      </List.Item>
                    )}
                  />
                ),
              },
            ]}
            style={{ marginTop: '16px' }}
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
                onClick={() => setSelectedAssetId(asset.asset_id)}
                style={{
                  cursor: 'pointer',
                  background: selectedAssetId === asset.asset_id ? '#e6f7ff' : 'transparent',
                }}
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
            registration_date: extracted_data.registration_date
              ? dayjs(extracted_data.registration_date as string)
              : null,
            land_use_term_start: extracted_data.land_use_term_start
              ? dayjs(extracted_data.land_use_term_start as string)
              : null,
            land_use_term_end: extracted_data.land_use_term_end
              ? dayjs(extracted_data.land_use_term_end as string)
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
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item>
            <Button type="primary" htmlType="submit" icon={<SaveOutlined />} loading={loading}>
              确认并创建产权证
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </Space>
  );
};
