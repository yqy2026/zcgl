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
  Typography,
  Row,
  Col,
  Spin,
  Alert,
  Form,
  Input,
  DatePicker,
  Modal,
  message,
  Popconfirm,
  Select,
} from 'antd';
import {
  ArrowLeftOutlined,
  FileTextOutlined,
  HomeOutlined,
  CheckCircleOutlined,
  EditOutlined,
  EyeOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import { propertyCertificateService } from '@/services/propertyCertificateService';
import type { PropertyOwner, CertificateType } from '@/types/propertyCertificate';
import { PROPERTY_CERTIFICATE_ROUTES } from '@/constants/routes';
import type { ColumnsType } from 'antd/es/table';
import { assetService } from '@/services/assetService';
import type { Asset } from '@/types/asset';

const { Title } = Typography;

const typeLabelMap: Record<CertificateType, string> = {
  real_estate: '不动产权证',
  house_ownership: '房屋所有权证',
  land_use: '土地使用证',
  other: '其他',
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

  if (isLoading) {
    return (
      <div style={{ padding: 24 }}>
        <Spin />
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ padding: 24 }}>
        <Alert type="error" message="加载失败" />
      </div>
    );
  }

  if (!certificate) {
    return (
      <div style={{ padding: 24 }}>
        <Alert type="warning" message="未找到产权证信息" />
      </div>
    );
  }

  const handleToggleVerified = async () => {
    if (!id) return;
    setSubmitting(true);
    try {
      await propertyCertificateService.updateCertificate(id, { verified: !certificate.verified });
      message.success(certificate.verified ? '已取消审核' : '已标记为已审核');
      await refetch();
    } catch {
      message.error('更新审核状态失败');
    } finally {
      setSubmitting(false);
    }
  };

  const openEdit = () => {
    form.setFieldsValue({
      certificate_number: certificate.certificate_number,
      property_address: certificate.property_address,
      building_area: certificate.building_area,
      land_area: certificate.land_area,
      floor_info: certificate.floor_info,
      land_use_type: certificate.land_use_type,
      land_use_term: certificate.land_use_term_start && certificate.land_use_term_end
        ? [dayjs(certificate.land_use_term_start), dayjs(certificate.land_use_term_end)]
        : null,
      registration_date: certificate.registration_date ? dayjs(certificate.registration_date) : null,
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
      message.success('更新成功');
      setEditVisible(false);
      await refetch();
    } catch {
      message.error('更新失败');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async () => {
    if (!id) return;
    setSubmitting(true);
    try {
      await propertyCertificateService.deleteCertificate(id);
      message.success('删除成功');
      navigate(PROPERTY_CERTIFICATE_ROUTES.LIST);
    } catch {
      message.error('删除失败');
    } finally {
      setSubmitting(false);
    }
  };

  const openAssetModal = () => {
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
      message.success('关联资产已更新');
      setAssetVisible(false);
      await refetch();
    } catch {
      message.error('更新关联资产失败');
    } finally {
      setSubmitting(false);
    }
  };

  const previewUrl = normalizePreviewUrl(certificate.extraction_source);

  const ownerColumns: ColumnsType<PropertyOwner> = [
    { title: '姓名/名称', dataIndex: 'name', key: 'name' },
    {
      title: '类型',
      dataIndex: 'owner_type',
      key: 'owner_type',
      render: (val: string) => {
        const map: Record<string, string> = {
          individual: '个人',
          organization: '组织',
          joint: '共同',
        };
        return <Tag>{map[val] ?? val}</Tag>;
      },
    },
    { title: '证件类型', dataIndex: 'id_type', key: 'id_type' },
    { title: '证件号码', dataIndex: 'id_number', key: 'id_number' },
    { title: '联系电话', dataIndex: 'phone', key: 'phone' },
    { title: '地址', dataIndex: 'address', key: 'address' },
  ];

  return (
    <div style={{ padding: 24 }}>
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        <Space>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate(PROPERTY_CERTIFICATE_ROUTES.LIST)}>
            返回列表
          </Button>
          <Title level={4} style={{ margin: 0 }}>
            产权证详情
          </Title>
          <Tag icon={<FileTextOutlined />}>{certificate.certificate_number}</Tag>
          <Tag color="blue">{typeLabelMap[certificate.certificate_type]}</Tag>
          <Tag color={certificate.verified ? 'green' : 'default'} icon={<CheckCircleOutlined />}>
            {certificate.verified ? '已审核' : '待审核'}
          </Tag>
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
              置信度 {(certificate.extraction_confidence * 100).toFixed(0)}%
            </Tag>
          )}
          {previewUrl != null && (
            <Button
              icon={<EyeOutlined />}
              onClick={() => window.open(previewUrl, '_blank', 'noopener,noreferrer')}
            >
              查看扫描件
            </Button>
          )}
          <Button onClick={openAssetModal}>关联资产</Button>
          <Button icon={<EditOutlined />} onClick={openEdit}>
            编辑
          </Button>
          <Button
            type={certificate.verified ? 'default' : 'primary'}
            loading={submitting}
            onClick={handleToggleVerified}
          >
            {certificate.verified ? '取消审核' : '标记已审核'}
          </Button>
          <Popconfirm
            title="确认删除该产权证？"
            description="删除后不可恢复，请确认已备份相关信息。"
            okText="删除"
            cancelText="取消"
            okButtonProps={{ danger: true }}
            onConfirm={handleDelete}
          >
            <Button danger loading={submitting}>
              删除
            </Button>
          </Popconfirm>
        </Space>

        <Row gutter={[24, 24]}>
          <Col span={24}>
            <Card title="基础信息">
              <Descriptions column={3} bordered>
                <Descriptions.Item label="登记日期">
                  {certificate.registration_date ? dayjs(certificate.registration_date).format('YYYY-MM-DD') : '-'}
                </Descriptions.Item>
                <Descriptions.Item label="坐落地址">{certificate.property_address ?? '-'}</Descriptions.Item>
                <Descriptions.Item label="物业类型">{certificate.property_type ?? '-'}</Descriptions.Item>
                <Descriptions.Item label="建筑面积">
                  {certificate.building_area != null ? `${certificate.building_area}㎡` : '-'}
                </Descriptions.Item>
                <Descriptions.Item label="土地面积">
                  {certificate.land_area != null ? `${certificate.land_area}㎡` : '-'}
                </Descriptions.Item>
                <Descriptions.Item label="楼层信息">{certificate.floor_info ?? '-'}</Descriptions.Item>
                <Descriptions.Item label="土地用途">{certificate.land_use_type ?? '-'}</Descriptions.Item>
                <Descriptions.Item label="土地使用期限">
                  {certificate.land_use_term_start && certificate.land_use_term_end
                    ? `${certificate.land_use_term_start} ~ ${certificate.land_use_term_end}`
                    : '-'}
                </Descriptions.Item>
                <Descriptions.Item label="共有情况">{certificate.co_ownership ?? '-'}</Descriptions.Item>
                <Descriptions.Item label="权利限制">{certificate.restrictions ?? '-'}</Descriptions.Item>
                <Descriptions.Item label="备注">{certificate.remarks ?? '-'}</Descriptions.Item>
                <Descriptions.Item label="来源">{certificate.extraction_source ?? '-'}</Descriptions.Item>
                <Descriptions.Item label="创建时间">
                  {certificate.created_at ? dayjs(certificate.created_at).format('YYYY-MM-DD') : '-'}
                </Descriptions.Item>
                <Descriptions.Item label="更新时间">
                  {certificate.updated_at ? dayjs(certificate.updated_at).format('YYYY-MM-DD') : '-'}
                </Descriptions.Item>
              </Descriptions>
            </Card>
          </Col>

          <Col span={24}>
            <Card title="权利人">
              <Table<PropertyOwner>
                columns={ownerColumns}
                dataSource={certificate.owners ?? []}
                rowKey="id"
                pagination={false}
              />
            </Card>
          </Col>

          <Col span={24}>
            <Card title="关联资产">
              {certificate.asset_ids && certificate.asset_ids.length > 0 ? (
                <Space wrap>
                  {certificate.asset_ids.map(aid => (
                    <Button
                      key={aid}
                      icon={<HomeOutlined />}
                      onClick={() => navigate(`/assets/${aid}`)}
                    >
                      资产 {aid}
                    </Button>
                  ))}
                </Space>
              ) : (
                <Alert type="info" message="暂无关联资产" />
              )}
            </Card>
          </Col>
        </Row>
      </Space>

      <Modal
        title="编辑产权证信息"
        open={editVisible}
        onCancel={() => setEditVisible(false)}
        onOk={handleSubmitEdit}
        confirmLoading={submitting}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            label="证书编号"
            name="certificate_number"
            rules={[{ required: true, message: '请输入证书编号' }]}
          >
            <Input />
          </Form.Item>
          <Form.Item label="登记日期" name="registration_date">
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item label="坐落地址" name="property_address">
            <Input />
          </Form.Item>
          <Form.Item label="建筑面积(㎡)" name="building_area">
            <Input />
          </Form.Item>
          <Form.Item label="土地面积(㎡)" name="land_area">
            <Input />
          </Form.Item>
          <Form.Item label="楼层信息" name="floor_info">
            <Input />
          </Form.Item>
          <Form.Item label="土地用途" name="land_use_type">
            <Input />
          </Form.Item>
          <Form.Item label="土地使用期限" name="land_use_term">
            <DatePicker.RangePicker style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item label="共有情况" name="co_ownership">
            <Input />
          </Form.Item>
          <Form.Item label="权利限制" name="restrictions">
            <Input />
          </Form.Item>
          <Form.Item label="备注" name="remarks">
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="关联资产"
        open={assetVisible}
        onCancel={() => setAssetVisible(false)}
        onOk={handleSubmitAssets}
        confirmLoading={submitting}
      >
        <Form form={assetForm} layout="vertical">
          <Form.Item label="关联资产" name="asset_ids">
            <Select
              mode="multiple"
              showSearch
              placeholder="选择资产（可多选）"
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
                  {asset.property_name} - {asset.address}
                </Select.Option>
              ))}
            </Select>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default PropertyCertificateDetailPage;
