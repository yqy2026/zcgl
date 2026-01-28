/**
 * Property Certificate List Page
 * 产权证列表页面
 */

import { useState } from 'react';
import { Table, Button, Space, Tag, Input } from 'antd';
import { PlusOutlined, SearchOutlined, EyeOutlined } from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { propertyCertificateService } from '@/services/propertyCertificateService';
import type { PropertyCertificate, CertificateType } from '@/types/propertyCertificate';
import dayjs from 'dayjs';

export const PropertyCertificateList: React.FC = () => {
  const navigate = useNavigate();
  const [searchText, setSearchText] = useState('');

  const { data: certificates, isLoading } = useQuery({
    queryKey: ['property-certificates'],
    queryFn: () => propertyCertificateService.listCertificates(),
  });

  const columns = [
    {
      title: '证书编号',
      dataIndex: 'certificate_number',
      key: 'certificate_number',
      filteredValue: searchText ? [searchText] : null,
      onFilter: (value: unknown, record: PropertyCertificate) =>
        record.certificate_number.toLowerCase().includes((value as string).toLowerCase()),
    },
    {
      title: '类型',
      dataIndex: 'certificate_type',
      key: 'certificate_type',
      render: (type: CertificateType) => {
        const typeMap: Record<CertificateType, string> = {
          real_estate: '不动产权证',
          house_ownership: '房屋所有权证',
          land_use: '土地使用证',
          other: '其他',
        };
        return <Tag>{typeMap[type] ?? type}</Tag>;
      },
    },
    {
      title: '坐落地址',
      dataIndex: 'property_address',
      key: 'property_address',
      ellipsis: true,
    },
    {
      title: '建筑面积',
      dataIndex: 'building_area',
      key: 'building_area',
      render: (area: string | null) => (area != null ? `${area}㎡` : '-'),
    },
    {
      title: '置信度',
      dataIndex: 'extraction_confidence',
      key: 'extraction_confidence',
      render: (confidence: number | null) => {
        if (confidence == null) return '-';
        const level = confidence > 0.8 ? 'success' : confidence > 0.5 ? 'warning' : 'default';
        return <Tag color={level}>{(confidence * 100).toFixed(0)}%</Tag>;
      },
    },
    {
      title: '审核状态',
      dataIndex: 'verified',
      key: 'verified',
      render: (verified: boolean) => (
        <Tag color={verified ? 'success' : 'default'}>{verified ? '已审核' : '待审核'}</Tag>
      ),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date: string) => dayjs(date).format('YYYY-MM-DD'),
    },
    {
      title: '操作',
      key: 'actions',
      render: (_: unknown, record: PropertyCertificate) => (
        <Space>
          <Button
            type="link"
            icon={<EyeOutlined />}
            onClick={() => navigate(`/property-certificates/${record.id}`)}
          >
            查看
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <div style={{ padding: '24px' }}>
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        <Space>
          <Input
            placeholder="搜索证书编号"
            prefix={<SearchOutlined />}
            style={{ width: 300 }}
            onChange={e => setSearchText(e.target.value)}
            allowClear
          />
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => navigate('/property-certificates/import')}
          >
            新建产权证
          </Button>
        </Space>

        <Table
          columns={columns}
          dataSource={certificates ?? []}
          rowKey="id"
          loading={isLoading}
          pagination={{
            showSizeChanger: true,
            showTotal: total => `共 ${total} 条`,
          }}
        />
      </Space>
    </div>
  );
};

export default PropertyCertificateList;
