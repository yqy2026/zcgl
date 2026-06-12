/**
 * Property Certificate List Page
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import { Button, Space, Tag, Input, Card, Typography } from 'antd';
import { PlusOutlined, SearchOutlined, EyeOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { MessageManager } from '@/utils/messageManager';
import { propertyCertificateService } from '@/services/propertyCertificateService';
import type { PropertyCertificate, CertificateType } from '@/types/propertyCertificate';
import dayjs from 'dayjs';
import { useArrayListData } from '@/hooks/useArrayListData';
import { TableWithPagination } from '@/components/Common/TableWithPagination';
import PageContainer from '@/components/Common/PageContainer';
import styles from './PropertyCertificateList.module.css';

interface CertificateFilters {
  keyword: string;
}

type Tone = 'primary' | 'success' | 'warning' | 'error';

interface TypeMeta {
  label: string;
  tone: Tone;
}

const CERTIFICATE_TYPE_META: Record<CertificateType, TypeMeta> = {
  real_estate: { label: 'Real estate', tone: 'primary' },
  house_ownership: { label: 'House ownership', tone: 'success' },
  land_use: { label: 'Land use', tone: 'warning' },
  other: { label: 'Other', tone: 'error' },
};

const CONFIDENCE_THRESHOLD = {
  high: 0.8,
  medium: 0.5,
};

const getConfidenceMeta = (confidence: number): { tone: Tone; label: string } => {
  if (confidence > CONFIDENCE_THRESHOLD.high) {
    return { tone: 'success', label: 'High' };
  }
  if (confidence > CONFIDENCE_THRESHOLD.medium) {
    return { tone: 'warning', label: 'Medium' };
  }
  return { tone: 'error', label: 'Low' };
};

export const PropertyCertificateList: React.FC = () => {
  const navigate = useNavigate();
  const [certificateSource, setCertificateSource] = useState<PropertyCertificate[]>([]);
  const [isFetching, setIsFetching] = useState(false);

  const {
    data: certificates,
    loading: listLoading,
    pagination,
    filters,
    loadList,
    applyFilters,
    updatePagination,
  } = useArrayListData<PropertyCertificate, CertificateFilters>({
    items: certificateSource,
    initialFilters: {
      keyword: '',
    },
    initialPageSize: 10,
    filterFn: useCallback((items: PropertyCertificate[], nextFilters: CertificateFilters) => {
      const trimmedKeyword = nextFilters.keyword.trim().toLowerCase();
      if (trimmedKeyword === '') {
        return items;
      }
      return items.filter(cert => cert.certificate_number?.toLowerCase().includes(trimmedKeyword));
    }, []),
  });

  useEffect(() => {
    const loadCertificates = async () => {
      setIsFetching(true);
      try {
        const data = await propertyCertificateService.listCertificates();
        setCertificateSource(data);
      } catch (error) {
        const message = error instanceof Error ? error.message : 'Failed to load certificates';
        MessageManager.error(message);
      } finally {
        setIsFetching(false);
      }
    };
    void loadCertificates();
  }, []);

  useEffect(() => {
    void loadList({ page: 1 });
  }, [certificateSource, loadList]);

  const loading = useMemo(() => isFetching || listLoading, [isFetching, listLoading]);
  const { Text } = Typography;
  const toneClassMap: Record<Tone, string> = {
    primary: styles.tonePrimary,
    success: styles.toneSuccess,
    warning: styles.toneWarning,
    error: styles.toneError,
  };

  const columns = [
    {
      title: 'Certificate number',
      dataIndex: 'certificate_number',
      key: 'certificate_number',
    },
    {
      title: 'Type',
      dataIndex: 'certificate_type',
      key: 'certificate_type',
      render: (type: CertificateType) => {
        const typeMeta = CERTIFICATE_TYPE_META[type] ?? {
          label: type,
          tone: 'primary' as Tone,
        };
        return (
          <Tag className={[styles.statusTag, toneClassMap[typeMeta.tone]].join(' ')}>
            {typeMeta.label}
          </Tag>
        );
      },
    },
    {
      title: 'Address',
      dataIndex: 'property_address',
      key: 'property_address',
      ellipsis: true,
    },
    {
      title: 'Building area',
      dataIndex: 'building_area',
      key: 'building_area',
      render: (area: string | null) => (area != null ? `${area} sqm` : '-'),
    },
    {
      title: 'Confidence',
      dataIndex: 'extraction_confidence',
      key: 'extraction_confidence',
      render: (confidence: number | null) => {
        if (confidence == null) {
          return '-';
        }
        const confidenceMeta = getConfidenceMeta(confidence);
        return (
          <Space size={6} className={styles.inlineStatus} wrap>
            <Tag className={[styles.statusTag, toneClassMap[confidenceMeta.tone]].join(' ')}>
              {(confidence * 100).toFixed(0)}%
            </Tag>
            <Text type="secondary" className={styles.statusAssistText}>
              {confidenceMeta.label}
            </Text>
          </Space>
        );
      },
    },
    {
      title: 'Created at',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date: string) => dayjs(date).format('YYYY-MM-DD'),
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_: unknown, record: PropertyCertificate) => (
        <Space className={styles.actionGroup}>
          <Button
            type="text"
            icon={<EyeOutlined />}
            onClick={() => navigate(`/property-certificates/${record.id}`)}
            className={styles.actionButton}
            aria-label={`View certificate ${record.certificate_number ?? record.id}`}
          >
            View
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <PageContainer
      className={styles.pageShell}
      title="Property Certificates"
      subTitle="Manage property certificate records and asset links"
    >
      <div className={styles.pageContent}>
        <Card className={styles.filterCard}>
          <Space size={12} wrap className={styles.filterActions}>
            <Input
              placeholder="Search certificate number"
              prefix={<SearchOutlined />}
              className={styles.searchInput}
              value={filters.keyword}
              onChange={e => applyFilters({ keyword: e.target.value })}
              allowClear
            />
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => navigate('/property-certificates/import')}
              className={styles.createButton}
            >
              New Certificate
            </Button>
          </Space>
        </Card>

        <TableWithPagination
          columns={columns}
          dataSource={certificates}
          rowKey="id"
          loading={loading}
          paginationState={pagination}
          onPageChange={updatePagination}
          paginationProps={{
            showTotal: (total: number) => `Total ${total}`,
          }}
        />
      </div>
    </PageContainer>
  );
};

export default PropertyCertificateList;
