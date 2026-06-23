import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  Card,
  Space,
  Button,
  Descriptions,
  Tag,
  Table,
  Row,
  Col,
  Alert,
  Form,
  Input,
  DatePicker,
  Modal,
  message,
  Popconfirm,
  Select,
} from 'antd';
import { FileTextOutlined, HomeOutlined, EditOutlined, EyeOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import { propertyCertificateService } from '@/services/propertyCertificateService';
import type { PropertyOwner, CertificateType } from '@/types/propertyCertificate';
import { PROPERTY_CERTIFICATE_ROUTES } from '@/constants/routes';
import type { ColumnsType } from 'antd/es/table';
import { assetService } from '@/services/assetService';
import type { Asset } from '@/types/asset';
import { PageContainer } from '@/components/Common';
import styles from './PropertyCertificateDetailPage.module.css';

const typeLabelMap: Record<CertificateType, string> = {
  real_estate: 'Real estate',
  house_ownership: 'House ownership',
  land_use: 'Land use',
  other: 'Other',
};

const normalizePreviewUrl = (source?: string | null) => {
  if (source == null) return null;
  const trimmed = source.trim();
  if (trimmed === '') return null;
  if (trimmed.startsWith('http://') || trimmed.startsWith('https://')) return trimmed;
  if (trimmed.startsWith('//')) return `${window.location.protocol}${trimmed}`;
  return trimmed;
};

const PropertyCertificateDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [editVisible, setEditVisible] = useState(false);
  const [assetVisible, setAssetVisible] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [form] = Form.useForm();
  const [assetForm] = Form.useForm();

  const {
    data: certificate,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ['property-certificate', id],
    queryFn: () => propertyCertificateService.getCertificate(id as string),
    enabled: !!id,
  });

  const { data: assetResponse, isLoading: loadingAssets } = useQuery({
    queryKey: ['assets-options'],
    queryFn: () => assetService.getAssets({ page: 1, page_size: 200 }),
  });

  if (error) {
    return (
      <PageContainer
        title="Property Certificate Detail"
        onBack={() => navigate(PROPERTY_CERTIFICATE_ROUTES.LIST)}
      >
        <Alert type="error" title="Failed to load" />
      </PageContainer>
    );
  }

  if (!isLoading && !certificate) {
    return (
      <PageContainer
        title="Property Certificate Detail"
        onBack={() => navigate(PROPERTY_CERTIFICATE_ROUTES.LIST)}
      >
        <Alert type="warning" title="Property certificate not found" />
      </PageContainer>
    );
  }

  const openEdit = () => {
    if (!certificate) return;
    form.setFieldsValue({
      certificate_number: certificate.certificate_number,
      property_address: certificate.property_address,
      building_area: certificate.building_area,
      land_area: certificate.land_area,
      floor_info: certificate.floor_info,
      land_use_type: certificate.land_use_type,
      land_use_term:
        certificate.land_use_term_start && certificate.land_use_term_end
          ? [dayjs(certificate.land_use_term_start), dayjs(certificate.land_use_term_end)]
          : null,
      registration_date: certificate.registration_date
        ? dayjs(certificate.registration_date)
        : null,
      co_ownership: certificate.co_ownership,
      restrictions: certificate.restrictions,
      remarks: certificate.remarks,
    });
    setEditVisible(true);
  };

  const handleSubmitEdit = async () => {
    if (!id) return;
    try {
      const values = await form.validateFields();
      setSubmitting(true);
      await propertyCertificateService.updateCertificate(id, {
        certificate_number: values.certificate_number,
        property_address: values.property_address ?? null,
        building_area: values.building_area ?? null,
        land_area: values.land_area ?? null,
        floor_info: values.floor_info ?? null,
        land_use_type: values.land_use_type ?? null,
        land_use_term_start: values.land_use_term?.[0]
          ? dayjs(values.land_use_term[0]).format('YYYY-MM-DD')
          : null,
        land_use_term_end: values.land_use_term?.[1]
          ? dayjs(values.land_use_term[1]).format('YYYY-MM-DD')
          : null,
        registration_date: values.registration_date
          ? dayjs(values.registration_date).format('YYYY-MM-DD')
          : null,
        co_ownership: values.co_ownership ?? null,
        restrictions: values.restrictions ?? null,
        remarks: values.remarks ?? null,
      });
      message.success('Updated successfully');
      setEditVisible(false);
      await refetch();
    } catch {
      message.error('Update failed');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async () => {
    if (!id) return;
    setSubmitting(true);
    try {
      await propertyCertificateService.deleteCertificate(id);
      message.success('Deleted successfully');
      navigate(PROPERTY_CERTIFICATE_ROUTES.LIST);
    } catch {
      message.error('Delete failed');
    } finally {
      setSubmitting(false);
    }
  };

  const openAssetModal = () => {
    if (!certificate) return;
    assetForm.setFieldsValue({
      asset_ids: certificate.asset_ids ?? [],
    });
    setAssetVisible(true);
  };

  const handleSubmitAssets = async () => {
    if (!id) return;
    try {
      const values = await assetForm.validateFields();
      setSubmitting(true);
      await propertyCertificateService.updateCertificate(id, {
        asset_ids: values.asset_ids ?? [],
      });
      message.success('Asset links updated');
      setAssetVisible(false);
      await refetch();
    } catch {
      message.error('Failed to update asset links');
    } finally {
      setSubmitting(false);
    }
  };

  const previewUrl = normalizePreviewUrl(certificate?.extraction_source);

  const ownerColumns: ColumnsType<PropertyOwner> = [
    { title: 'Name', dataIndex: 'name', key: 'name' },
    {
      title: 'Type',
      dataIndex: 'owner_type',
      key: 'owner_type',
      render: (val: string) => {
        const map: Record<string, string> = {
          individual: 'Individual',
          organization: 'Organization',
          joint: 'Joint',
        };
        return <Tag>{map[val] ?? val}</Tag>;
      },
    },
    { title: 'ID type', dataIndex: 'id_type', key: 'id_type' },
    { title: 'ID number', dataIndex: 'id_number', key: 'id_number' },
    { title: 'Phone', dataIndex: 'phone', key: 'phone' },
    { title: 'Address', dataIndex: 'address', key: 'address' },
  ];

  return (
    <PageContainer
      title={
        <Space>
          <span>Property Certificate Detail</span>
          {certificate && (
            <>
              <Tag icon={<FileTextOutlined />}>{certificate.certificate_number}</Tag>
              <Tag color="blue">{typeLabelMap[certificate.certificate_type]}</Tag>
              {certificate.extraction_confidence != null && (
                <Tag
                  color={
                    certificate.extraction_confidence > 0.8
                      ? 'green'
                      : certificate.extraction_confidence > 0.5
                        ? 'gold'
                        : 'default'
                  }
                >
                  Confidence {(certificate.extraction_confidence * 100).toFixed(0)}%
                </Tag>
              )}
            </>
          )}
        </Space>
      }
      loading={isLoading}
      onBack={() => navigate(PROPERTY_CERTIFICATE_ROUTES.LIST)}
      extra={
        certificate && (
          <Space>
            {previewUrl != null && (
              <Button
                icon={<EyeOutlined />}
                onClick={() => window.open(previewUrl, '_blank', 'noopener,noreferrer')}
              >
                View Scan
              </Button>
            )}
            <Button onClick={openAssetModal}>Link Assets</Button>
            <Button icon={<EditOutlined />} onClick={openEdit}>
              Edit
            </Button>
            <Popconfirm
              title="Delete this property certificate?"
              description="This action cannot be undone."
              okText="Delete"
              cancelText="Cancel"
              okButtonProps={{ danger: true }}
              onConfirm={handleDelete}
            >
              <Button danger loading={submitting}>
                Delete
              </Button>
            </Popconfirm>
          </Space>
        )
      }
    >
      {certificate && (
        <Space orientation="vertical" size="large" className={styles.fullWidthStack}>
          <Row gutter={[24, 24]}>
            <Col span={24}>
              <Card title="Basic Information">
                <Descriptions column={3} bordered>
                  <Descriptions.Item label="Registration date">
                    {certificate.registration_date
                      ? dayjs(certificate.registration_date).format('YYYY-MM-DD')
                      : '-'}
                  </Descriptions.Item>
                  <Descriptions.Item label="Address">
                    {certificate.property_address ?? '-'}
                  </Descriptions.Item>
                  <Descriptions.Item label="Property type">
                    {certificate.property_type ?? '-'}
                  </Descriptions.Item>
                  <Descriptions.Item label="Building area">
                    {certificate.building_area != null ? `${certificate.building_area} sqm` : '-'}
                  </Descriptions.Item>
                  <Descriptions.Item label="Land area">
                    {certificate.land_area != null ? `${certificate.land_area} sqm` : '-'}
                  </Descriptions.Item>
                  <Descriptions.Item label="Floor info">
                    {certificate.floor_info ?? '-'}
                  </Descriptions.Item>
                  <Descriptions.Item label="Land use type">
                    {certificate.land_use_type ?? '-'}
                  </Descriptions.Item>
                  <Descriptions.Item label="Land use term">
                    {certificate.land_use_term_start && certificate.land_use_term_end
                      ? `${certificate.land_use_term_start} ~ ${certificate.land_use_term_end}`
                      : '-'}
                  </Descriptions.Item>
                  <Descriptions.Item label="Co-ownership">
                    {certificate.co_ownership ?? '-'}
                  </Descriptions.Item>
                  <Descriptions.Item label="Restrictions">
                    {certificate.restrictions ?? '-'}
                  </Descriptions.Item>
                  <Descriptions.Item label="Remarks">
                    {certificate.remarks ?? '-'}
                  </Descriptions.Item>
                  <Descriptions.Item label="Source">
                    {certificate.extraction_source ?? '-'}
                  </Descriptions.Item>
                  <Descriptions.Item label="Created at">
                    {certificate.created_at
                      ? dayjs(certificate.created_at).format('YYYY-MM-DD')
                      : '-'}
                  </Descriptions.Item>
                  <Descriptions.Item label="Updated at">
                    {certificate.updated_at
                      ? dayjs(certificate.updated_at).format('YYYY-MM-DD')
                      : '-'}
                  </Descriptions.Item>
                </Descriptions>
              </Card>
            </Col>

            <Col span={24}>
              <Card title="Owners">
                <Table<PropertyOwner>
                  columns={ownerColumns}
                  dataSource={certificate.owners ?? []}
                  rowKey="id"
                  pagination={false}
                />
              </Card>
            </Col>

            <Col span={24}>
              <Card title="Linked Assets">
                {certificate.asset_ids && certificate.asset_ids.length > 0 ? (
                  <Space wrap>
                    {certificate.asset_ids.map(aid => (
                      <Button
                        key={aid}
                        icon={<HomeOutlined />}
                        onClick={() => navigate(`/assets/${aid}`)}
                      >
                        Asset {aid}
                      </Button>
                    ))}
                  </Space>
                ) : (
                  <Alert type="info" title="No linked assets" />
                )}
              </Card>
            </Col>
          </Row>
        </Space>
      )}

      <Modal
        title="Edit Property Certificate"
        open={editVisible}
        onCancel={() => setEditVisible(false)}
        onOk={handleSubmitEdit}
        confirmLoading={submitting}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            label="Certificate number"
            name="certificate_number"
            rules={[{ required: true, message: 'Please enter certificate number' }]}
          >
            <Input />
          </Form.Item>
          <Form.Item label="Registration date" name="registration_date">
            <DatePicker className={styles.fullWidthDatePicker} />
          </Form.Item>
          <Form.Item label="Address" name="property_address">
            <Input />
          </Form.Item>
          <Form.Item label="Building area" name="building_area">
            <Input />
          </Form.Item>
          <Form.Item label="Land area" name="land_area">
            <Input />
          </Form.Item>
          <Form.Item label="Floor info" name="floor_info">
            <Input />
          </Form.Item>
          <Form.Item label="Land use type" name="land_use_type">
            <Input />
          </Form.Item>
          <Form.Item label="Land use term" name="land_use_term">
            <DatePicker.RangePicker className={styles.fullWidthRangePicker} />
          </Form.Item>
          <Form.Item label="Co-ownership" name="co_ownership">
            <Input />
          </Form.Item>
          <Form.Item label="Restrictions" name="restrictions">
            <Input />
          </Form.Item>
          <Form.Item label="Remarks" name="remarks">
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="Link Assets"
        open={assetVisible}
        onCancel={() => setAssetVisible(false)}
        onOk={handleSubmitAssets}
        confirmLoading={submitting}
      >
        <Form form={assetForm} layout="vertical">
          <Form.Item label="Linked assets" name="asset_ids">
            <Select
              mode="multiple"
              showSearch
              placeholder="Select assets"
              optionFilterProp="children"
              loading={loadingAssets}
              filterOption={(input, option) =>
                String(option?.children || '')
                  .toLowerCase()
                  .includes(input.toLowerCase())
              }
            >
              {(assetResponse?.items ?? []).map((asset: Asset) => (
                <Select.Option key={asset.id} value={asset.id}>
                  {asset.asset_name} - {asset.address}
                </Select.Option>
              ))}
            </Select>
          </Form.Item>
        </Form>
      </Modal>
    </PageContainer>
  );
};

export default PropertyCertificateDetailPage;
