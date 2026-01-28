import React from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Card, Space, Button, Descriptions, Tag, Table, Typography, Row, Col, Spin, Alert } from 'antd';
import { ArrowLeftOutlined, FileTextOutlined, HomeOutlined, CheckCircleOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import { propertyCertificateService } from '@/services/propertyCertificateService';
import type { PropertyCertificate, PropertyOwner, CertificateType } from '@/types/propertyCertificate';
import { PROPERTY_CERTIFICATE_ROUTES } from '@/constants/routes';
import type { ColumnsType } from 'antd/es/table';

const { Title } = Typography;

const typeLabelMap: Record<CertificateType, string> = {
  real_estate: '不动产权证',
  house_ownership: '房屋所有权证',
  land_use: '土地使用证',
  other: '其他',
};

const PropertyCertificateDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const { data: certificate, isLoading, error } = useQuery({
    queryKey: ['property-certificate', id],
    queryFn: () => propertyCertificateService.getCertificate(id as string),
    enabled: !!id,
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
            <Tag color={certificate.extraction_confidence > 0.8 ? 'green' : certificate.extraction_confidence > 0.5 ? 'gold' : 'default'}>
              置信度 {(certificate.extraction_confidence * 100).toFixed(0)}%
            </Tag>
          )}
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
    </div>
  );
};

export default PropertyCertificateDetailPage;
