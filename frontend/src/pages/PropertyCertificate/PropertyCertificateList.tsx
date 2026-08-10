/**
 * Property Certificate List Page
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import { Button, Space, Tag, Input, Card } from 'antd';
import { PlusOutlined, SearchOutlined, EyeOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { MessageManager } from '@/utils/messageManager';
import { propertyCertificateService } from '@/services/propertyCertificateService';
import type { PropertyCertificate, CertificateType } from '@/types/propertyCertificate';
import { CERTIFICATE_TYPE_LABELS } from '@/types/propertyCertificate';
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
  real_estate: { label: CERTIFICATE_TYPE_LABELS.real_estate, tone: 'primary' },
  house_ownership: { label: CERTIFICATE_TYPE_LABELS.house_ownership, tone: 'success' },
  land_use: { label: CERTIFICATE_TYPE_LABELS.land_use, tone: 'warning' },
  other: { label: CERTIFICATE_TYPE_LABELS.other, tone: 'error' },
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
        const message = error instanceof Error ? error.message : '加载产权证列表失败';
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
  const toneClassMap: Record<Tone, string> = {
    primary: styles.tonePrimary,
    success: styles.toneSuccess,
    warning: styles.toneWarning,
    error: styles.toneError,
  };

  const columns = [
    {
      title: '证书编号',
      dataIndex: 'certificate_number',
      key: 'certificate_number',
    },
    {
      title: '类型',
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
      title: '坐落地址',
      dataIndex: 'property_address',
      key: 'property_address',
      ellipsis: true,
    },
    {
      title: '建筑面积',
      dataIndex: 'building_area',
      key: 'building_area',
      render: (area: string | null) => (area != null ? `${area} ㎡` : '-'),
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
        <Space className={styles.actionGroup}>
          <Button
            type="text"
            icon={<EyeOutlined />}
            onClick={() => navigate(`/property-certificates/${record.id}`)}
            className={styles.actionButton}
            aria-label={`查看产权证 ${record.certificate_number ?? record.id}`}
          >
            查看
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <PageContainer
      className={styles.pageShell}
      title="产权证管理"
      subTitle="管理产权证记录与资产关联"
    >
      <div className={styles.pageContent}>
        <Card className={styles.filterCard}>
          <Space size={12} wrap className={styles.filterActions}>
            <Input
              placeholder="搜索证书编号"
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
              新建产权证
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
            showTotal: (total: number) => `共 ${total} 条`,
          }}
        />
      </div>
    </PageContainer>
  );
};

export default PropertyCertificateList;
